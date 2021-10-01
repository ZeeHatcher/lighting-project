import boto3
from boto3.dynamodb.conditions import Key
from contextlib import closing
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, g, url_for, redirect, request, session
import json
import os
import sys
import threading
import traceback
from werkzeug import secure_filename, abort
import base64
import io
import requests
from uuid import uuid4

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 1 * 1024 * 1024 # 1MB maximum file size
app.secret_key=uuid4().hex

@app.route("/")
@app.route("/index")
def index():
    if "access-token" in session and session["access-token"]:
        print("access token found")
        print("Logged in as", session['username'])
    else:
        return redirect('/login')
    
    # Clients to access AWS services
    dynamodb = boto3.resource("dynamodb")
    iot = boto3.client("iot")
    iot_data = boto3.client("iot-data")
    
    lightsticks = []
    modes = {}
    patterns = {}
    
    # Get modes from DynamoDB and format into dict
    table_modes = dynamodb.Table("modes")
    items = table_modes.scan()["Items"]
    items = sorted(items, key=lambda k: k["id"])
    for item in items:
        modes[int(item["id"])] = item

    # Get patterns from DynamoDB and format into dict
    table_patterns = dynamodb.Table("patterns")
    items = table_patterns.scan()["Items"]
    items = sorted(items, key=lambda k: k["id"])
    for item in items:
        patterns[int(item["id"])] = item

    # Get list of lightsticks and get reported shadow state
    res_things = iot.list_things_in_thing_group(thingGroupName='lightsticks')
    for thing in res_things["things"]:
#         print(thing)
        res_shadow = iot_data.get_thing_shadow(thingName=thing)
        byte_str = res_shadow["payload"].read()
        payload = json.loads(byte_str.decode("utf-8"))

        if payload["state"] and payload["state"]["reported"]:
            state = payload["state"]["reported"]
            state["name"] = thing
            
            s3 = boto3.resource("s3")
            bucket = s3.Bucket(S3_BUCKET)
            #s3://lighting-bucket/lightstick_cherry/image
            object = bucket.Object(thing+'/image')
            file_stream = io.BytesIO()
            img_data = object.get().get('Body').read()
#             object.download_fileobj(file_stream)
            #"https://lighting-bucket.s3.ap-southeast-1.amazonaws.com/lightstick_cherry/image"
            state["image"] = base64.encodebytes(img_data).decode('utf-8')

            lightsticks.insert(0, state)
#     print(lightsticks)
    
    return render_template("index.html", username=session['username'],lightsticks=lightsticks, modes=modes, patterns=patterns)

@app.route("/lightstick/<name>/data")
def get_sensors_data(name):
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table("sensors_data")

    response = table.query(
        KeyConditionExpression=Key("thing_name").eq(name))

    x = []
    y = []

    items = response["Items"]
    for item in items:
        x.append({
            "value": item["data"]["x"],
            "timestamp": item["timestamp"]
        })
        y.append({
            "value": item["data"]["y"],
            "timestamp": item["timestamp"]
        })

    res = {
        "x": x,
        "y": y
    }

    return jsonify(res)

@app.route("/lightstick/<name>", methods=["POST"])
def update(name):
    iot_data = boto3.client("iot-data")

    field = request.form["field"]
    value = None

    if field == "mode" or field == "pattern":
        value = request.form.get("value", type=int)
    elif field == "is_on":
        value = request.form.get("value") == "true"
    elif field == "colors":
        value = request.form.getlist("value[]")
    else:
        abort(400)

    if (value == None):
        abort(400)

    desired = {}
    desired[field] = value

    payload = { "state": { "desired": desired } }
    byte_str = json.dumps(payload)

    response = iot_data.update_thing_shadow(thingName=name, payload=byte_str)
    print(response)

    res = { "status": 200, "message": "Successfully updated lightstick shadow." }

    return jsonify(res)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        if "access-token" in session and session["access-token"]:
            return redirect('/')

        return render_template("login.html")

    elif request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        
#     username = "admin"
#     password = "lighting-project"
        
        client = boto3.client("cognito-idp")
        try:
            response = client.initiate_auth(
                ClientId = CLIENT_ID,
                AuthFlow="USER_PASSWORD_AUTH",
                AuthParameters={
                    "USERNAME": username,
                    "PASSWORD": password,
                }
            )
##### Run this if "NEW_PASSWORD_REQUIRED" Challenge Posed #####    
#             chg = client.respond_to_auth_challenge(
#                 ClientId = CLIENT_ID,
#                 ChallengeName="NEW_PASSWORD_REQUIRED",
#                 ChallengeResponses={
#                     "USERNAME":username,
#                     "NEW_PASSWORD": "testing1"
#                 },
#                 Session=response["Session"]            
#             )
            
        except client.exceptions.NotAuthorizedException as e:
            abort(422)
                
        except Exception as e:
            print(e)
            abort(400)

        access_token = response["AuthenticationResult"]["AccessToken"]
        session['access-token'] = access_token
        session['username'] = username    
        
        res = { "status": 200, "message": "Successfully logged in", "redirect": url_for("index") }
            
        return jsonify(res)
    
    
@app.route("/sendcode", methods=["POST"])
def sendCode():
    client = boto3.client("cognito-idp")
#     print(request.form["username"])
    try:
        response = client.forgot_password(
            ClientId = CLIENT_ID,
            Username = request.form["username"]
        )
        print(response)
        
    except client.exceptions.LimitExceededException as e:
        print("Confirmation Code request limit reached")
        res = { "status": 422, "message": "Confirmation code limit reached"}
        return jsonify(res)
#         abort(422)
        
    except Exception as e:
        print(e)
        
    res = { "status": 200, "message": "Confirmation code sent"}
    return jsonify(res)

@app.route("/reset", methods=["POST"])
def reset():
    input_username = request.form["username"]
    code = request.form["code"]
    password = request.form["new-password"]
        
#     username = "admin"
#     password = "lighting-project"
    
    client = boto3.client("cognito-idp")
    try:
        response = client.confirm_forgot_password(
            ClientId = CLIENT_ID,
            Username = input_username,
            ConfirmationCode = code,
            Password = password
        )
        print(response)
        
    except client.exceptions.ExpiredCodeException as e:
        print("Code Expired")
        res = { "status": 422, "message": "Confirmation code expired"}
        return jsonify(res)
            
    except Exception as e:
        print(e)
        abort(400) 
    
    res = { "status": 200, "message": "Successfully logged in"}
        
    return jsonify(res)

@app.route("/logout", methods=["POST"])
def logout():
    session['access-token'] = None
    session['username'] = None    

    res = { "status": 200, "message": "Successfully logged out", "redirect": url_for("login") }

    return jsonify(res)
            
@app.route("/lightstick/<name>/upload", methods=["POST"])
def upload(name):
    s3 = boto3.resource("s3")
    bucket = s3.Bucket(S3_BUCKET)

    f = request.files["file"]

    if (f.content_type not in MIME_TYPES):
        abort(400)

    file_type = f.content_type.split("/")[0]
    f.filename = name + "/" + file_type

    try:
        bucket.upload_fileobj(f, f.filename)
    except Exception as e:
        print("Something happened: ", e)

        res = { "status": 400, "message": "Something went wrong on the server." }
        return jsonify(res)

    res = { "status": 200, "message": "Successfully uploaded file." }

    return jsonify(res)

if __name__ == "__main__":
    # Load .env file for development
    load_dotenv()

    # Constants
    MIME_TYPES = ["image/jpeg", "image/png", "audio/mpeg", "audio/wav"]
    S3_BUCKET = os.environ.get("S3_BUCKET")
    CLIENT_ID = os.environ.get("COGNITO_USER_CLIENT_ID")

    app.run(host="0.0.0.0", port=5000, debug=True)

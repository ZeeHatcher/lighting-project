import boto3
from boto3.dynamodb.conditions import Key
from contextlib import closing
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, g
import json
import os
import sys
import threading
import traceback
from werkzeug import secure_filename, abort

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 1 * 1024 * 1024 # 1MB maximum file size

@app.route("/")
def index():
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
        res_shadow = iot_data.get_thing_shadow(thingName=thing)
        byte_str = res_shadow["payload"].read()
        payload = json.loads(byte_str.decode("utf-8"))

        if payload["state"] and payload["state"]["reported"]:
            state = payload["state"]["reported"]
            state["name"] = thing

            lightsticks.insert(0, state)

    return render_template("index.html", lightsticks=lightsticks, modes=modes, patterns=patterns)

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

    app.run(host="0.0.0.0", port=5000, debug=True)

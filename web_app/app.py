import boto3
from contextlib import closing
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, g
import json
import MySQLdb
import os
import sys
import traceback

load_dotenv()

DB_HOST = os.environ.get("DB_HOST")
DB_USERNAME = os.environ.get("DB_USERNAME")
DB_PASSWORD = os.environ.get("DB_PASSWORD")
DB_DATABASE = os.environ.get("DB_DATABASE")

app = Flask(__name__)
iot = boto3.client("iot")
iot_data = boto3.client("iot-data")

def request_has_connection():
    return hasattr(g, "db")

def get_request_connection():
    if not request_has_connection():
        db = MySQLdb.connect(DB_HOST, DB_USERNAME, DB_PASSWORD, DB_DATABASE)
        db.autocommit(True)

        g.db = db

    return g.db

@app.route("/")
def index():
    db = get_request_connection()

    rows_modes = []
    rows_patterns = []

    with closing(db.cursor()) as cur:
        sql = "SELECT * FROM modes"
        cur.execute(sql)

        rows_modes = cur.fetchall()

    with closing(db.cursor()) as cur:
        sql = "SELECT * FROM patterns"
        cur.execute(sql)

        rows_patterns = cur.fetchall()

    lightsticks = []
    modes = {}
    patterns = {}

    res_things = iot.list_things_in_thing_group(thingGroupName='lightsticks')
    for thing in res_things["things"]:
        res_shadow = iot_data.get_thing_shadow(thingName=thing)
        byte_str = res_shadow["payload"].read()
        payload = json.loads(byte_str.decode("utf-8"))

        if payload["state"] and payload["state"]["reported"]:
            state = payload["state"]["reported"]
            state["name"] = thing

            lightsticks.append(state)

    print(lightsticks)
    for row in rows_modes:
        mode, name = row
        modes[mode] = {
            "name": name
        }

    for row in rows_patterns:
        pattern, name, num_colors = row
        patterns[pattern] = {
            "name": name,
            "num_colors": num_colors
        }

    return render_template("index.html", lightsticks=lightsticks, modes=modes, patterns=patterns)

@app.route("/lightstick/<name>", methods=["POST"])
def update(name):
    field = request.form["field"]
    value = None

    if field == "mode" or field == "pattern":
        value = request.form.get("value", type=int)
    elif field == "is_on":
        value = request.form.get("value") == "true"
    elif field == "colors":
        value = request.form.getlist("value[]")
    else:
        res = jsonify({ "status": 400, "message": "Could not get appropriate form value" })
        return res

    desired = {}
    desired[field] = value

    payload = { "state": { "desired": desired } }
    byte_str = json.dumps(payload)

    response = iot_data.update_thing_shadow(thingName=name, payload=byte_str)
    print(response)

    res = { "status": 200, "message": "Successfully updated lightstick shadow." }

    return jsonify(res)

@app.teardown_request
def exit(ex):
    if request_has_connection():
        print("Terminating database connection...")
        db = get_request_connection()
        db.close()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

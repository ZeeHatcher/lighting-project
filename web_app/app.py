import json
import os
import MySQLdb

from contextlib import closing
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify

load_dotenv()

DB_HOST = os.environ.get("DB_HOST")
DB_USERNAME = os.environ.get("DB_USERNAME")
DB_PASSWORD = os.environ.get("DB_PASSWORD")
DB_DATABASE = os.environ.get("DB_DATABASE")

app = Flask(__name__)
db = MySQLdb.connect(DB_HOST, DB_USERNAME, DB_PASSWORD, DB_DATABASE) or die("Could not connect to database")
db.autocommit(True)

@app.route("/")
def index():
    rows_lightsticks = []
    rows_modes = []
    rows_patterns = []

    with closing(db.cursor()) as cur:
        sql = "SELECT * FROM lightsticks"
        cur.execute(sql)

        rows_lightsticks = cur.fetchall()

    with closing(db.cursor()) as cur:
        sql = "SELECT * FROM modes"
        cur.execute(sql)

        rows_modes = cur.fetchall()

    with closing(db.cursor()) as cur:
        sql = "SELECT * FROM patterns"
        cur.execute(sql)

        rows_patterns = cur.fetchall()

    lightsticks = {}
    modes = {}
    patterns = {}

    for row in rows_lightsticks:
        lightstick, is_on, mode, pattern, colors = row
        lightsticks[lightstick] = {
            "is_on": is_on,
            "mode": mode,
            "pattern": pattern,
            "colors": colors
        }

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

@app.route("/lightstick/<lightstick>", methods=["POST"])
def update(lightstick):
    field = request.form["field"]
    value = request.form["value"]

    with closing(db.cursor()) as cur:
        cur.execute("UPDATE lightsticks SET %s = '%s' WHERE id = '%s'" % (field, value, lightstick))

    res = { "status": 200, "message": "Successfully updated lightstick." }

    return jsonify(res)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, debug=True)

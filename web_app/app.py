import json
import os
import MySQLdb

from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify

load_dotenv()

DB_HOST = os.environ.get("DB_HOST")
DB_USERNAME = os.environ.get("DB_USERNAME")
DB_PASSWORD = os.environ.get("DB_PASSWORD")
DB_DATABASE = os.environ.get("DB_DATABASE")

app = Flask(__name__)
db = MySQLdb.connect(DB_HOST, DB_USERNAME, DB_PASSWORD, DB_DATABASE) or die("Could not connect to database")

@app.route("/")
def index():
    rows_lightsticks = []
    rows_modes = []
    rows_patterns = []

    with db.cursor() as cur:
        sql = "SELECT * FROM lightsticks"
        cur.execute(sql)

        rows_lightsticks = cur.fetchall()

        cur.close()

    with db.cursor() as cur:
        sql = "SELECT * FROM modes"
        cur.execute(sql)

        rows_modes = cur.fetchall()

        cur.close()

    with db.cursor() as cur:
        sql = "SELECT * FROM patterns"
        cur.execute(sql)

        rows_patterns = cur.fetchall()

        cur.close()

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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, debug=True)

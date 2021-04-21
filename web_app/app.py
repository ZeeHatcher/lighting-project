import json
import MySQLdb
import os

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
    return render_template("index.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, debug=True)

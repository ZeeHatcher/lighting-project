import json
import MySQLdb
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)
#db = MySQLdb.connect("localhost", "pi", "", "DB_HERE") or die("Could not connect to database")
#db.autocommit(True)

@app.route("/")
def index():
    return render_template("index.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, debug=True)

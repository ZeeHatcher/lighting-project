import boto3
import json
import time
import urllib.parse

iot_data = boto3.client("iot-data")

def lambda_handler(event, context):
    # Get object key
    key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')
    
    # Extract required data
    tokens = key.split("/")
    name = tokens[0]
    file_type = tokens[1]

    # Initialize data to update shadow with
    desired = { "upload_" + file_type: round(time.time()) }
    payload = { "state": { "desired": desired } }
    
    iot_data.update_thing_shadow(thingName=name, payload=json.dumps(payload))

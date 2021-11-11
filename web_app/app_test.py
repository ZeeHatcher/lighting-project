import boto3
import os
from dotenv import load_dotenv

def s3_bucket():
    try:
        s3 = boto3.resource("s3")
        bucket = s3.Bucket(S3_BUCKET)
        print("S3 test complete")
    except:
        print("S3 test incomplete")

def incognito_correct():
    username = "admin"
    password = "lighting-project"
    try:
        client = boto3.client("cognito-idp")
        response = client.initiate_auth(
            ClientId = CLIENT_ID,
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={
                "USERNAME": username,
                "PASSWORD": password,
            }
        )
        print("Incognito testing with correct credentials complete")
        
    except client.exceptions.NotAuthorizedException as e:
        print("Incognito testing with correct credentials not authorized")
                
    except Exception as e:
        print("Incognito testing with correct credentials incomplete")

def incognito_incorrect():
    username = "admin"
    password = "incorrect_password"
    try:
        client = boto3.client("cognito-idp")
        response = client.initiate_auth(
            ClientId = CLIENT_ID,
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={
                "USERNAME": username,
                "PASSWORD": password,
            }
        )
        print("Incognito testing with incorrect credentials authorized")
    except client.exceptions.NotAuthorizedException as e:
        print("Incognito testing with incorrect credentials complete")
                
    except Exception as e:
        print("Incognito testing with incorrect credentials incomplete")
    
def dynamodb():
    try:
        client = boto3.client("dynamodb")
        tables = client.list_tables()
#         print(tables['TableNames'])
        print("Dynamodb test complete")
    except:
        print("Dynamodb test incomplete")
        
def iotcore():
    try:
        iot = boto3.client("iot")
        iot_data = boto3.client("iot-data")
        res_things = iot.list_things_in_thing_group(thingGroupName='lightsticks')
        for thing in res_things["things"]:
            res_shadow = iot_data.get_thing_shadow(thingName=thing)
        print("IoT Core test complete")
    except:
        print("IoT Core test incomplete")

if __name__ == "__main__":
    # Load .env file for development
    load_dotenv()

    # Constants
    MIME_TYPES = ["image/jpeg", "image/png", "audio/mpeg", "audio/wav"]
    S3_BUCKET = os.environ.get("S3_BUCKET")
    CLIENT_ID = os.environ.get("COGNITO_USER_CLIENT_ID")
    
    s3_bucket()
    iotcore()
    incognito_correct()
    incognito_incorrect()
    dynamodb()
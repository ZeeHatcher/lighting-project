#!/bin/bash

# JSON parser
sudo apt-get install jq

cd $(dirname $0)
ROOT_DIR=$(pwd)

# Retrieve Account ID
ACCOUNT_ID=$(aws sts get-caller-identity | jq -r ".Account")

# ---=== IAM ===---
# Create roles with required policies
aws iam create-role \
  --role-name LPRoleForIoT \
  --assume-role-policy-document file://trusts/iot.json
aws iam put-role-policy \
  --role-name LPRoleForIoT \
  --policy-name LPPolicyForDynamoDBPutAccess \
  --policy-document "$(sed "s/<ACCOUNT_ID>/$ACCOUNT_ID/g" policies/iot.json)"

aws iam create-role \
  --role-name LPRoleForLambda \
  --assume-role-policy-document file://trusts/lambda.json
aws iam put-role-policy \
  --role-name LPRoleForLambda \
  --policy-name LPPolicyForIoTUpdateThingShadowAccess \
  --policy-document "$(sed "s/<ACCOUNT_ID>/$ACCOUNT_ID/g" policies/lambda.json)"

aws iam create-role \
  --role-name LPRoleForEC2 \
  --assume-role-policy-document file://trusts/ec2.json
aws iam put-role-policy \
  --role-name LPRoleForEC2 \
  --policy-name LPPolicyForLightstickDataReadWriteAccess \
  --policy-document "$(sed "s/<ACCOUNT_ID>/$ACCOUNT_ID/g" policies/ec2.json)"
aws iam create-instance-profile --instance-profile-name LPRoleForEC2
aws iam add-role-to-instance-profile \
  --instance-profile-name LPRoleForEC2 \
  --role-name LPRoleForEC2
# ---===========---

# ---=== DynamoDB ===---
# Setup tables
aws dynamodb create-table \
  --table-name modes \
  --attribute-definitions \
    AttributeName=id,AttributeType=N \
  --key-schema \
    AttributeName=id,KeyType=HASH \
  --provisioned-throughput \
    ReadCapacityUnits=5,WriteCapacityUnits=5
aws dynamodb create-table \
  --table-name patterns \
  --attribute-definitions \
    AttributeName=id,AttributeType=N \
  --key-schema \
    AttributeName=id,KeyType=HASH \
  --provisioned-throughput \
    ReadCapacityUnits=5,WriteCapacityUnits=5
aws dynamodb create-table \
  --table-name sensors_data \
  --attribute-definitions \
    AttributeName=thing_name,AttributeType=S \
    AttributeName=timestamp,AttributeType=N \
  --key-schema \
    AttributeName=thing_name,KeyType=HASH \
    AttributeName=timestamp,KeyType=RANGE \
  --provisioned-throughput \
    ReadCapacityUnits=5,WriteCapacityUnits=5
# ---================---

# ---=== S3 ===---
# Create bucket
aws s3api create-bucket \
  --bucket lighting-project \
  --create-bucket-configuration LocationConstraint=ap-southeast-1
# ---==========---

# ---=== IoT Core ===---
# Create thing policy
aws iot create-policy \
  --policy-name LPPolicyForIoTShadowReadWriteAccess \
  --policy-document "$(sed "s/<ACCOUNT_ID>/$ACCOUNT_ID/g" policies/thing.json)"

# Create thing group
aws iot create-thing-group --thing-group-name lightsticks

# Setup rules engine
aws iot create-topic-rule \
  --rule-name LPRuleForSensorsData \
  --topic-rule-payload "$(sed "s/<ACCOUNT_ID>/$ACCOUNT_ID/g" iot/rule.json)"
# ---================---

# ---=== Lambda ===---
# Setup function
zip -j lambda/deployment.zip lambda/lambda_function.py
aws lambda create-function \
  --function-name LPFunctionForUploadNotification \
  --runtime python3.8 \
  --zip-file fileb://lambda/deployment.zip \
  --handler lambda_function.lambda_handler \
  --role arn:aws:iam::$ACCOUNT_ID:role/LPRoleForLambda
rm lambda/deployment.zip

# Add policies for S3
aws lambda add-permission \
  --function-name LPFunctionForUploadNotification \
  --statement-id LPPolicyForLambdaInvokeFunctionAccess \
  --action lambda:InvokeFunction \
  --principal s3.amazonaws.com \
  --source-arn arn:aws:s3:::lighting-project \
  --source-account $ACCOUNT_ID

# Setup S3 trigger
aws s3api put-bucket-notification-configuration \
  --bucket lighting-project \
  --notification-configuration "$(sed "s/<ACCOUNT_ID>/$ACCOUNT_ID/g" lambda/notification.json)"
# ---==============---

# ---=== Cognito ===---
USER_POOL_ID=$(aws cognito-idp create-user-pool \
  --pool-name LPUserPool \
  --policies "PasswordPolicy={MinimumLength=8,RequireUppercase=false,RequireLowercase=false,RequireNumbers=false,RequireSymbols=false,TemporaryPasswordValidityDays=365}" \
  | jq -r ".UserPool.Id")

CLIENT_ID=$(aws cognito-idp create-user-pool-client \
  --user-pool-id $USER_POOL_ID \
  --client-name LPWebServer \
  --explicit-auth-flows "ALLOW_ADMIN_USER_PASSWORD_AUTH" "ALLOW_USER_PASSWORD_AUTH" \
  | jq -r ".UserPoolClient.ClientId")

aws cognito-idp create-group \
  --user-pool-id $USER_POOL_ID \
  --group-name admin

aws cognito-idp admin-create-user \
    --user-pool-id $USER_POOL_ID \
    --username admin \
    --message-action SUPPRESS

aws cognito-idp admin-set-user-password \
  --user-pool-id $USER_POOL_ID \
  --username admin \
  --password lighting-project \
  --permanent

aws cognito-idp admin-add-user-to-group \
  --user-pool-id $USER_POOL_ID \
  --username admin \
  --group-name admin
# ---===============---

# ---=== EC2 ===---
# Setup security groups and rules
SECURITY_GROUP_ID=$(aws ec2 create-security-group \
  --group-name LPSecurityGroupForWebServer \
  --description "Security group for the lighting-project web server, exposes the TCP port 5000" \
  | jq -r ".GroupId")

aws ec2 authorize-security-group-ingress \
  --group-id $SECURITY_GROUP_ID \
  --protocol tcp \
  --port 5000 \
  --cidr 0.0.0.0/0

# Launch EC2 instance and attach role
INSTANCE_ID=$(aws ec2 run-instances \
  --image-id ami-073998ba87e205747 \
  --instance-type t2.micro \
  --security-group-ids $SECURITY_GROUP_ID \
  --user-data "$(sed "s/<CLIENT_ID>/$CLIENT_ID/g" ec2/userdata.sh)" \
  --iam-instance-profile Name=LPRoleForEC2 \
  --count 1 \
  | jq -r ".Instances[0].InstanceId")
# ---===========---

# Insert preset data into DynamoDB when initialization is complete
aws dynamodb batch-write-item --request-items file://dynamodb/modes.json
aws dynamodb batch-write-item --request-items file://dynamodb/patterns.json

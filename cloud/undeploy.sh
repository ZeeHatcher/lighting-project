#!/bin/bash

CONFIG=$(cat undeploy.json)

INSTANCE_ID=$(echo $CONFIG | jq -r ".INSTANCE_ID")
USERPOOL_ID=$(echo $CONFIG | jq -r ".USERPOOL_ID")
S3_BUCKET=$(echo $CONFIG | jq -r ".S3_BUCKET")

echo $INSTANCE_ID
echo $USERPOOL_ID
echo $S3_BUCKET

aws ec2 terminate-instances --instance-ids $INSTANCE_ID

aws ec2 delete-security-group --group-name LPSecurityGroupForWebServer

aws cognito-idp delete-user-pool --user-pool-id $USERPOOL_ID

aws lambda delete-function --function-name LPFunctionForUploadNotification

aws iot delete-topic-rule --rule-name LPRuleForSensorsData
aws iot delete-thing-group --thing-group-name lightsticks
aws iot delete-policy --policy-name LPPolicyForIoTShadowReadWriteAccess

aws s3 rb s3://$S3_BUCKET --force

aws dynamodb delete-table --table-name modes
aws dynamodb delete-table --table-name patterns
aws dynamodb delete-table --table-name sensors_data

aws iam delete-role-policy --role-name LPRoleForIoT --policy-name LPPolicyForDynamoDBPutAccess
aws iam delete-role --role-name LPRoleForIoT

aws iam delete-role-policy --role-name LPRoleForLambda --policy-name LPPolicyForIoTUpdateThingShadowAccess
aws iam delete-role --role-name LPRoleForLambda

aws iam remove-role-from-instance-profile --instance-profile-name LPRoleForEC2 --role-name LPRoleForEC2
aws iam delete-instance-profile --instance-profile-name LPRoleForEC2
aws iam delete-role-policy --role-name LPRoleForEC2 --policy-name LPPolicyForLightstickDataReadWriteAccess
aws iam delete-role --role-name LPRoleForEC2

rm undeploy.json

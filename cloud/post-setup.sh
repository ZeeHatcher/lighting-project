USERPOOL_ID=$1

if [ -z "$USERPOOL_ID" ]
then
  echo "Please input a value for the userpool ID."
  echo ""
  echo 'Usage: post-setup.sh "USERPOOL_ID"'
  exit
fi

aws cognito-idp admin-set-user-password \
  --user-pool-id $USERPOOL_ID \
  --username admin \
  --password lighting-project \
  --permanent

aws cognito-idp admin-set-user-password \
  --user-pool-id $USERPOOL_ID \
  --username user \
  --password lighting-project \
  --permanent

aws dynamodb batch-write-item --request-items file://modes.json
aws dynamodb batch-write-item --request-items file://patterns.json

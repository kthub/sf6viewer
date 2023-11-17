import boto3
import json
import logging
import time
import os

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# User Limit
USER_LIMIT = int(os.environ['USER_LIMIT'])

# Initialize a DynamoDB resources
dynamodb = boto3.resource('dynamodb')
table_user = dynamodb.Table('User')
table_battlelog = dynamodb.Table('BattleLog')

# Initialize Lambda
lambda_client = boto3.client('lambda')

def lambda_handler(event, context):
  
  # Get User List
  response = table_user.scan(
    ProjectionExpression='UserCode',
    Limit=USER_LIMIT
  )
  items = response['Items']

  # Invoke updateBattleLog asynchronously
  for item in items:
    user_code = item['UserCode']
    logger.info(f"invoke update for UserCode={user_code}")
    response = lambda_client.invoke(
      FunctionName='updateBattleLog',
      InvocationType='Event',
      Payload=json.dumps({'USER_CODE': user_code})
    )
    time.sleep(1)
  logger.info(f"{len(items)} items are successfully invoked. USER_LIMIT={USER_LIMIT}")

  # Return JSON
  return {
    'statusCode': 200,
    'body': json.dumps("Success")
  }
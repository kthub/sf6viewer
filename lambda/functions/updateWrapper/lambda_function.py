import boto3
import json
import logging
import time
import os
import requests
from bs4 import BeautifulSoup

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

# update environment variable for lambda
def update_lambda_environment(fname, new_environment_variables):
  response = lambda_client.get_function_configuration(FunctionName=fname)
  current_env_vars = response['Environment']['Variables']

  current_env_vars.update(new_environment_variables)
  lambda_client.update_function_configuration(
    FunctionName=fname,
    Environment={'Variables': current_env_vars}
  )

# main
def lambda_handler(event, context):
  ##
  ## Update Build ID for updateBattleLog lambda function
  ##
  headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36'}
  resp = requests.get('https://www.streetfighter.com/6/buckler/ja-jp', headers=headers)
  soup = BeautifulSoup(resp.text, 'html.parser')
  script_tag = soup.find('script', {'id': '__NEXT_DATA__'})
  json_data = json.loads(script_tag.string)
  build_id = json_data.get('buildId', None)
  logger.info(f"update build id with : {build_id}")
  update_lambda_environment('updateBattleLog', {'BUILD_ID': build_id})

  ##
  ## Check User Limit
  ##
  # Get User List
  response = table_user.scan(
    ProjectionExpression='UserCode',
    Limit=USER_LIMIT
  )
  items = response['Items']

  ##
  ## Invoke Lambda
  ##
  # Invoke updateBattleLog with asynch mode
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
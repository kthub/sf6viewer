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

def update_lambda_environment(function_name, new_environment_variables):
  # 現在のLambda関数の設定を取得
  response = lambda_client.get_function_configuration(FunctionName=function_name)
  current_env_vars = response['Environment']['Variables']

  # 新しい環境変数を追加または更新
  current_env_vars.update(new_environment_variables)

  # 更新された環境変数でLambda関数を更新
  lambda_client.update_function_configuration(
    FunctionName=function_name,
    Environment={'Variables': current_env_vars}
  )

def lambda_handler(event, context):
  
  ##
  ## Update Build ID for updateBattleLog lambda function
  ##
  # Get Build ID
  headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36'}
  resp = requests.get('https://www.streetfighter.com/6/buckler/ja-jp', headers=headers)
  soup = BeautifulSoup(resp.text, 'html.parser')
  script_tag = soup.find('script', {'id': '__NEXT_DATA__'})
  json_data = json.loads(script_tag.string)
  build_id = json_data.get('buildId', None)
  logger.info(f"update build id with : {build_id}")

  # Update environment variable for updateBattleLog
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
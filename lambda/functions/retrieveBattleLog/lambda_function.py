import boto3
from boto3.dynamodb.conditions import Key
import json
import logging
import time

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
  
  # Get arguments
  user_code = event['queryStringParameters'].get('USER_CODE', None)
  if user_code is None:
    raise ValueError("USER_CODE is not specified")
  elif not (user_code.isdigit() and len(user_code) == 10):
    raise ValueError("USER_CODE must be a 10-digit number")
  
  retrieve_option = int(event['queryStringParameters'].get('RETRIEVE_OPTION', 9))
  fetch_now = event['queryStringParameters'].get('FETCH_NOW', 'False')
  fetch_now = fetch_now.lower() == 'true'

  logger.info(f'user_code : {user_code}')
  logger.info(f'retrieve_option: {retrieve_option}')
  logger.info(f'fetch_now: {fetch_now}')

  # Initialize a DynamoDB resources
  dynamodb = boto3.resource('dynamodb')
  table_user = dynamodb.Table('User')
  table_battlelog = dynamodb.Table('BattleLog')
  
  # Query table_user
  if not fetch_now:
    response = table_user.query(
      KeyConditionExpression=Key('UserCode').eq(user_code),
      ProjectionExpression='UserCode, CurrentLP, CharacterName'
    )
    items = response.get('Items', [])

  if fetch_now or not items:
    # Invoke updateBattleLog synchronously
    logger.info(f"invoke updateBattleLog for user code : {user_code}")
    lambda_client = boto3.client('lambda')
    response = lambda_client.invoke(
      FunctionName='updateBattleLog',
      InvocationType='RequestResponse',
      Payload=json.dumps({'USER_CODE': user_code})
    )
    # Check status code
    status_code = response['ResponseMetadata']['HTTPStatusCode']
    if status_code == 200:
      logger.info(f"updateBattleLog is successfully invoked.")
    else:
      logger.info(f"updateBattleLog invocation failed.")
      response_payload = json.loads(response['Payload'].read())
      raise Exception(f"updateBattleLog invocation failed. response payload=({response_payload})")

    time.sleep(1) # sleep for dynamodb to be consistent

    # Query table_user again
    response = table_user.query(
      KeyConditionExpression=Key('UserCode').eq(user_code),
      ProjectionExpression='UserCode, CurrentLP, CharacterName',
      ConsistentRead=True
    )
    items = response.get('Items', [])
    if items:
      characterName = items[0]['CharacterName']
      currentLP = items[0]['CurrentLP']
    else:
      characterName = "__NO_DATA__"
      currentLP = 0

  else:
    characterName = items[0]['CharacterName']
    currentLP = items[0]['CurrentLP']
  
  logger.info(f"User info queried. (CharacterName={characterName}, CurrentLP={currentLP})")

  # Get the epoch timestamp for the start date
  start_epoch = int((time.time() - (retrieve_option * 24 * 60 * 60)))
  logger.info(f'start_epoch: {start_epoch}')

  # Query table_battlelog
  response = table_battlelog.query(
    KeyConditionExpression=Key('UserCode').eq(user_code) & Key('UploadedAt').gte(start_epoch),
    ProjectionExpression='UserCode, UploadedAt, ReplayReduced'
  )
  items = response.get('Items', [])

  while 'LastEvaluatedKey' in response:
    response = table_battlelog.query(
      KeyConditionExpression=Key('UserCode').eq(user_code) & Key('UploadedAt').gte(start_epoch),
      ProjectionExpression='UserCode, UploadedAt, ReplayReduced',
      ExclusiveStartKey=response['LastEvaluatedKey']
    )
    items.extend(response.get('Items', []))
  
  logger.info(f'{len(items)} items retrieved.')
  
  # Expand resultant JSON string
  expanded_items = []
  for item in items:
    item_copy = item.copy()  # Create a copy to avoid modifying the original item
    # ---------------------------------------------------------------- #
    # can add filter condition here (for transfered data optimization)
    # ex.)
    #  Battle Type (only Ranked Match)
    #  Character Name (only current character)
    #  etc..
    # ---------------------------------------------------------------- #
    item_copy['ReplayReduced'] = json.loads(item['ReplayReduced'])  # Expand JSON string to JSON object
    item_copy['UploadedAt'] = int(item['UploadedAt'])
    item_copy['CharacterName'] = characterName
    item_copy['CurrentLP'] = int(currentLP)
    expanded_items.append(item_copy)

  # For invalid(unused) UserCode
  if len(expanded_items) == 0:
    item = {}
    item['CharacterName'] = characterName
    item['CurrentLP'] = int(currentLP)
    expanded_items.append(item)

  # Return JSON
  return {
    'statusCode': 200,
    'body': json.dumps(expanded_items)
  }
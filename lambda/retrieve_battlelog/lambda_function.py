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
    
    retrieve_option = int(event['queryStringParameters'].get('RETRIEVE_OPTION', 8))

    logger.info(f'user_code : {user_code}')
    logger.info(f'retrieve_option: {retrieve_option}')
    
    # Initialize a DynamoDB resources
    dynamodb = boto3.resource('dynamodb')
    table_user = dynamodb.Table('User')
    table_battlelog = dynamodb.Table('BattleLog')
    
    # Query table_user to get current LP
    response = table_user.query(
        KeyConditionExpression=Key('UserCode').eq(user_code),
        ProjectionExpression='UserCode, CurrentLP'
    )
    items = response.get('Items', [])
    currentLP = items[0]['CurrentLP']
    
    # Get the epoch timestamp for the start date (default to 8 d ago if not provided)
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
    
    hits = len(items)
    logger.info(f'{hits} items retrieved.')
    
    # Expand resultant JSON string
    expanded_items = []
    for item in items:
        item_copy = item.copy()  # Create a copy to avoid modifying the original item
        item_copy['ReplayReduced'] = json.loads(item['ReplayReduced'])  # Expand JSON string to JSON object
        item_copy['UploadedAt'] = int(item['UploadedAt'])
        item_copy['CurrentLP'] = int(currentLP)
        expanded_items.append(item_copy)

    # Return JSON
    return {
        'statusCode': 200,
        'body': json.dumps(expanded_items,)
    }
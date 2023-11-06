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
    table = dynamodb.Table('BattleLog')

    # Get the epoch timestamp for the start date (default to 8 weeks ago if not provided)
    start_epoch = int((time.time() - (retrieve_option * 7 * 24 * 60 * 60)))
    logger.info(f'start_epoch: {start_epoch}')

    # Query table
    response = table.query(
        KeyConditionExpression=Key('UserCode').eq(user_code) & Key('UploadedAt').gte(start_epoch),
        ProjectionExpression='UserCode, UploadedAt, ReplayReduced'
    )
    hits = len(response.get('Items', []))
    logger.info(f'{hits} items retrieved.')

    # Expand resultant JSON string
    expanded_items = []
    for item in response.get('Items', []):
        item_copy = item.copy()  # Create a copy to avoid modifying the original item
        item_copy['ReplayReduced'] = json.loads(item['ReplayReduced'])  # Expand JSON string to JSON object
        item_copy['UploadedAt'] = int(item['UploadedAt'])
        expanded_items.append(item_copy)

    # Return JSON
    return {
        'statusCode': 200,
        'body': json.dumps(expanded_items,)
    }
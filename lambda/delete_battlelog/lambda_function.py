import json
import logging
import boto3
from boto3.dynamodb.conditions import Key
import re

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize a session using Amazon DynamoDB
session = boto3.session.Session(region_name='ap-northeast-1')
dynamodb = session.resource('dynamodb')
table_user = dynamodb.Table('User')
table_battlelog = dynamodb.Table('BattleLog')

def lambda_handler(event, context):
    
    # get arguments
    user_code = event.get('USER_CODE')
    if not re.match(r'^\d{10}$', user_code):
        raise ValueError('user_code must be a 10-digit number')
    logger.info(f'delete all records for UserCode={user_code}')
    
    # delete BattleLog
    response = None
    items_to_delete = []
    while True:
        if response and 'LastEvaluatedKey' in response:
            response = table_battlelog.query(
                KeyConditionExpression=Key('UserCode').eq(user_code),
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
        else:
            response = table_battlelog.query(
                KeyConditionExpression=Key('UserCode').eq(user_code)
            )
        items = response.get('Items', [])
        items_to_delete.extend(items)
        
        if 'LastEvaluatedKey' not in response:
            break

    for item in items_to_delete:
        delete_key = {
            'UserCode': item['UserCode'],
            'UploadedAt': item['UploadedAt']
        }
        table_battlelog.delete_item(Key=delete_key)
        logger.info(f'item deleted : {delete_key}')

    logger.info(f'{len(items_to_delete)} records are deleted from BattleLog')

    # delete User
    table_user.delete_item(Key={'UserCode': user_code})

    logger.info(f'1 record is deleted from User')

    return {
        'statusCode': 200,
        'body': json.dumps('Successfully deleted.')
    }

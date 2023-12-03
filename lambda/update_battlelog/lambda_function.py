import json
import logging
import boto3
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError
import os
import time
import requests
import re
import replay_utils as ru

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize DynamoDB
session = boto3.session.Session(region_name='ap-northeast-1')
dynamodb = session.resource('dynamodb')
table_user = dynamodb.Table('User')
table_battlelog = dynamodb.Table('BattleLog')

# Initialize SNS
sns = boto3.client('sns')
SNS_TOPIC_ARN = "arn:aws:sns:ap-northeast-1:572065744477:email-notification"

# Main
def lambda_handler(event, context):
  try:
    # Configuration
    user_code = event.get('USER_CODE')
    if not re.match(r'^\d{10}$', user_code):
      raise ValueError('user_code must be a 10-digit number')
    build_id = os.environ['BUILD_ID']
    buckler_id = os.environ['BUCKLER_ID']
    gid = os.environ['GID']

    # Headers
    headers = {
      'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
      'Cookie': f"CookieConsent={{'stamp':'6oNLBjPlhgvQsfXTcT3nYo80bz5NQ0zBXB/8f2bTC8qu7EGMr60Y/w==','necessary':True,'preferences':True,'statistics':True,'marketing':True,'method':'explicit','ver':2,'utc':1691968880965,'region':'jp'}}; buckler_id={buckler_id}; _gid={gid}"
    }
    
    ##
    ## Update BattleLog
    ##
    # Target URL
    base_url = f'https://www.streetfighter.com/6/buckler/_next/data/{build_id}/ja-jp/profile/{user_code}/battlelog.json?sid={user_code}'
    urls = [base_url + (f"&page={i}" if i > 1 else "") for i in range(1, 11)]

    # Get latest UploadedAt
    response = table_battlelog.query(
      KeyConditionExpression=Key('UserCode').eq(user_code),
      ProjectionExpression='UploadedAt',
      ScanIndexForward=False,
      Limit=1
    )
    items = response.get('Items', [])
    if items:
      latestUploadedAt = items[0]['UploadedAt']
    else:
      latestUploadedAt = 1698796800 # 2023/11/11 00:00:00 as default
    logger.info(f'get last UploadedAt (lastUploadedAt={latestUploadedAt})')

    # Create items to write
    batch_items = []
    uploaded_at_set = set() # for duplicate prevention
    request_skip_flag = False
    for url in urls:
      if (request_skip_flag):
        break

      request_start_time = time.perf_counter()
      response = requests.get(url, headers=headers)
      request_end_time = time.perf_counter()
      logger.info(f'request completed with {(request_end_time - request_start_time) * 1000.0}[ms]. URL={url}')

      try:
        data = response.json()
      except:
        raise Exception("JSON Parse Error. Check if BUILD_ID is valid.")
      
      # if replay_list doesn't exist, break the loop
      if 'replay_list' not in data['pageProps'] or len(data['pageProps']['replay_list']) == 0:
        break

      for replay in data['pageProps']['replay_list']:
        uploaded_at = replay['uploaded_at']
        if (uploaded_at > latestUploadedAt):
          item = {
            'UserCode': user_code,
            'UploadedAt': uploaded_at,
            'Replay': json.dumps(replay),
            'ReplayReduced': json.dumps(ru.transform_to_replay_reduced(replay, int(user_code))),
          }
          if uploaded_at not in uploaded_at_set:
            batch_items.append({
              'PutRequest': {
                'Item': item
              }
            })
            uploaded_at_set.add(uploaded_at)
        else:
          request_skip_flag = True
    
    if len(batch_items) > 0:
      logger.info(f'new record detected. ({len(batch_items)} items)')

    # Batch Write (max items per one batch operation is 25)
    for i in range(0, len(batch_items), 25):
      batch_to_write = batch_items[i:i+25]
      logger.info("start batch write[" + str(i+1) + "-" + str(i+25) + "]")
      try:
        response = dynamodb.batch_write_item(RequestItems={table_battlelog.name: batch_to_write})
        if 'UnprocessedItems' in response and response['UnprocessedItems']:
          logger.info("UnprocessedItems detected :", response['UnprocessedItems'])
        else:
          logger.info("all items are successfully processed.")
      except Exception as e:
        raise Exception("batch write error: " + str(e))

    # debug
    #for item in batch_items:
    #  logger.info(f'put item to BattleLog table (UserCode={user_code}, UploadedAt={str(item["PutRequest"]["Item"]["UploadedAt"])})')

    if len(batch_items) > 0:
      logger.info(f'batch write to the BattleLog table completed. ({len(batch_items)} items)')
    else:
      logger.info(f'no item to update.')

    ##
    ## Update User
    ##
    if len(batch_items) > 0:
      # Target URL
      play_url = f'https://www.streetfighter.com/6/buckler/_next/data/{build_id}/ja-jp/profile/{user_code}/play.json?sid={user_code}'

      # Query play.json and update User table
      request_start_time = time.perf_counter()
      response = requests.get(play_url, headers=headers)
      request_end_time = time.perf_counter()
      logger.info(f'request completed with {(request_end_time - request_start_time) * 1000.0}[ms]. URL={play_url}')

      data = response.json()

      # Get favorite character name
      favorite_character_id = data['pageProps']['fighter_banner_info']['favorite_character_id']
      character_league_infos = data['pageProps']['play']['character_league_infos']
      favorite_character_name = None
      for character_info in character_league_infos:
        if character_info['character_id'] == favorite_character_id:
          favorite_character_name = character_info['character_name']
          break

      # Create item to put
      item = {
        'UserCode': user_code,
        'FighterId': data['pageProps']['fighter_banner_info']['personal_info']['fighter_id'],
        'CharacterName': favorite_character_name,
        'CurrentLP': data['pageProps']['fighter_banner_info']['favorite_character_league_info']['league_point']
      }

      # Put item
      response = table_user.put_item(
        Item=item
      )
      logger.info(f'put item to User table (UserCode={user_code})')

  except Exception as e:
    logger.error(f'Error occurred: {e}')
    sns.publish(
      TopicArn=SNS_TOPIC_ARN,
      Message=f"An error occurred in the Lambda function: {e}",
      Subject=f"Lambda Function Error (updateBattleLog, UserCode={user_code})"
    )
    raise

  return {
    'statusCode': 200,
    'body': json.dumps('Successfully Completed.')
  }
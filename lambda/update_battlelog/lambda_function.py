import json
import logging
import boto3
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError
import os
import time
import requests
import re

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Battle input type transformation
def transform_battle_input_type(bitype):
  if bitype == "[t]モダン":
    return "M"
  elif bitype == "[t]クラシック":
    return "C"
  else:
    return "?"

# Result calculation
def calculate_result(rounds):
  if len(rounds) <= 1:
    return "Unknown"
  elif rounds.count(0) >= 2:
    return "lose"
  else:
    return "win"

# ReplayReduced creation
def transform_to_replay_reduced(replay, short_id):
  transformed = {}
  
  player1_info = replay.get('player1_info', {})
  player2_info = replay.get('player2_info', {})
  
  player1 = player1_info.get('player', {})
  player2 = player2_info.get('player', {})

  # determine which player is myself
  my_player_info, opponent_player_info = (player1_info, player2_info) if player1.get('short_id') == short_id else (player2_info, player1_info)
  my_player, opponent_player = (player1, player2) if player1.get('short_id') == short_id else (player2, player1)

  # Populate the transformed data
  transformed.update({
    'fighter_id': my_player.get('fighter_id', ''),
    'short_id': my_player.get('short_id', ''),
    'platform_name': my_player.get('platform_name', ''),
    'character_name': my_player_info.get('character_name', ''),
    'league_point': my_player_info.get('league_point', ''),
    'battle_input_type_name': transform_battle_input_type(my_player_info.get('battle_input_type_name', '')),
    'round_results': my_player_info.get('round_results', []),
    'opponent': {
        'fighter_id': opponent_player.get('fighter_id', ''),
        'short_id': opponent_player.get('short_id', ''),
        'platform_name': opponent_player.get('platform_name', ''),
        'character_name': opponent_player_info.get('character_name', ''),
        'league_point': opponent_player_info.get('league_point', ''),
        'battle_input_type_name': transform_battle_input_type(opponent_player_info.get('battle_input_type_name', '')),
        'round_results': opponent_player_info.get('round_results', [])
    },
    'result': calculate_result(my_player_info.get('round_results', [])),
    'side': 'player1' if player1.get('short_id') == short_id else 'player2',
    'replay_id': replay.get('replay_id', ''),
    'uploaded_at': replay.get('uploaded_at', ''),
    'views': replay.get('views', 0),
    'replay_battle_type_name': replay.get('replay_battle_type_name', '')
  })

  return transformed

# Initialize a session using Amazon DynamoDB
session = boto3.session.Session(region_name='ap-northeast-1')
dynamodb = session.resource('dynamodb')
table_user = dynamodb.Table('User')
table_battlelog = dynamodb.Table('BattleLog')

# Initialize SNS
sns = boto3.client('sns')
SNS_TOPIC_ARN = "arn:aws:sns:ap-northeast-1:572065744477:email-notification"

def lambda_handler(event, context):
  try:
    # Configuration
    user_code = event.get('USER_CODE')
    if not re.match(r'^\d{10}$', user_code):
      raise ValueError('user_code must be a 10-digit number')
    server_id = os.environ['SERVER_ID']
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
    base_url = f'https://www.streetfighter.com/6/buckler/_next/data/{server_id}/ja-jp/profile/{user_code}/battlelog.json?sid={user_code}'
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
        raise Exception("JSON Parse Error. Check if SERVER_ID is valid.")
      
      for replay in data['pageProps']['replay_list']:
        uploaded_at = replay['uploaded_at']
        if (uploaded_at > latestUploadedAt):
          item = {
            'UserCode': user_code,
            'UploadedAt': uploaded_at,
            'Replay': json.dumps(replay),
            'ReplayReduced': json.dumps(transform_to_replay_reduced(replay, int(user_code))),
          }
          batch_items.append({
              'PutRequest': {
                  'Item': item
              }
          })
        else:
          request_skip_flag = True
    
    if len(batch_items) > 0:
      logger.info(f'new record detected ({len(batch_items)} items)')

    # Batch Write (max items per one batch operation is 25)
    for i in range(0, len(batch_items), 25):
      batch_to_write = batch_items[i:i+25]
      response = dynamodb.batch_write_item(RequestItems={table_battlelog.name: batch_to_write})

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
      play_url = f'https://www.streetfighter.com/6/buckler/_next/data/{server_id}/ja-jp/profile/{user_code}/play.json?sid={user_code}'

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
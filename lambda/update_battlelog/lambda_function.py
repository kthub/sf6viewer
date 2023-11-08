import json
import logging
import boto3
from botocore.exceptions import ClientError
import os
import time
import requests

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
table = dynamodb.Table('BattleLog')

def lambda_handler(event, context):

  # Configuration
  user_code = event.get('USER_CODE')
  #TBD : Check USER_CODE value
  server_id = os.environ['SERVER_ID']
  buckler_id = os.environ['BUCKLER_ID']
  gid = os.environ['GID']

  # Headers
  headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
    'Cookie': f"CookieConsent={{'stamp':'6oNLBjPlhgvQsfXTcT3nYo80bz5NQ0zBXB/8f2bTC8qu7EGMr60Y/w==','necessary':True,'preferences':True,'statistics':True,'marketing':True,'method':'explicit','ver':2,'utc':1691968880965,'region':'jp'}}; buckler_id={buckler_id}; _gid={gid}"
  }

  # SNS
  SNS = boto3.client('sns')
  SNS_TOPIC_ARN = "arn:aws:sns:ap-northeast-1:572065744477:email-notification"

  ##
  ## Update User
  ##
  # Target URL
  play_url = f'https://www.streetfighter.com/6/buckler/_next/data/{server_id}/ja-jp/profile/{user_code}/play.json?sid={user_code}'

  # Query play.json and update User table
  try:
    request_start_time = time.perf_counter()
    response = requests.get(play_url, headers=headers)
    request_end_time = time.perf_counter()
    logger.info(f'request completed with {(request_end_time - request_start_time) * 1000.0}[ms]. URL={play_url}')

    data = response.json()
    item = {
      'UserCode': user_code,
      'CurrentLP': data['pageProps']['fighter_banner_info']['favorite_character_league_info']['league_point']
    }
    response = dynamodb.Table('User').put_item(
      Item=item
    )
    logger.info(f'put item to User table (UserCode={user_code})')
  except Exception as e:
    logger.error(f'Error occurred: {e}')
    SNS.publish(
      TopicArn=SNS_TOPIC_ARN,
      Message=f"An error occurred in the Lambda function: {e}",
      Subject="Lambda Function Error (updateBattleLog::User)"
    )
    raise
  
  ##
  ## Update BattleLog
  ##
  # Target URL
  base_url = f'https://www.streetfighter.com/6/buckler/_next/data/{server_id}/ja-jp/profile/{user_code}/battlelog.json?sid={user_code}'
  urls = [base_url + (f"&page={i}" if i > 1 else "") for i in range(1, 11)]

  # Query battlelog.json and update BattleLog table
  try:
    for url in urls:
      request_start_time = time.perf_counter()
      response = requests.get(url, headers=headers)
      request_end_time = time.perf_counter()
      logger.info(f'request completed with {(request_end_time - request_start_time) * 1000.0}[ms]. URL={url}')

      data = response.json()
      for replay in data['pageProps']['replay_list']:
        item = {
          'UserCode': user_code,
          'UploadedAt': replay['uploaded_at'],
          'Replay': json.dumps(replay),
          'ReplayReduced': json.dumps(transform_to_replay_reduced(replay, int(user_code))),
        }
        try:
          response = table.put_item(
            Item=item,
            ConditionExpression='attribute_not_exists(UserCode) AND attribute_not_exists(UploadedAt)'
          )
          logger.info(f'put item to BattleLog table (UserCode={user_code}, UploadedAt={str(replay["uploaded_at"])})')
        except ClientError as ex:
          if ex.response['Error']['Code'] == 'ConditionalCheckFailedException':
            print(f'item already exist. skip put item. (UserCode={user_code}, UploadedAt={str(replay["uploaded_at"])})')
          else:
            raise
  except Exception as e:
    logger.error(f'Error occurred: {e}')
    SNS.publish(
      TopicArn=SNS_TOPIC_ARN,
      Message=f"An error occurred in the Lambda function: {e}",
      Subject="Lambda Function Error (updateBattleLog::BattleLog)"
    )
    raise

  return {
    'statusCode': 200,
    'body': json.dumps('Successfully Completed.')
  }
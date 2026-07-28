import json
import logging
import boto3
from boto3.dynamodb.conditions import Key
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

# Error classification for notifications:
#  - TransientError: self-heals (Lambda async retry now, next batch at the latest).
#    Log only, no SNS. If retries are exhausted and the update is dropped, the
#    CloudWatch alarm on AsyncEventsDropped notifies instead.
#  - ActionRequiredError: needs human action (e.g. buckler_id renewal). SNS right away.
#  - any other exception: unexpected (bug etc.). SNS right away.
class TransientError(Exception):
  pass

class ActionRequiredError(Exception):
  pass

# Interval between page requests to avoid bursting the server (seconds)
REQUEST_INTERVAL = float(os.environ.get('REQUEST_INTERVAL', '1'))

# Reuse HTTP connection (keep-alive) across requests within a warm container
http_session = requests.Session()

# Fetch JSON with retry for transient errors (rate limit, maintenance, WAF challenge, etc.)
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

def fetch_json(url, headers, max_retries=3):
  last_detail = None
  wait_hint = None
  for attempt in range(max_retries + 1):
    if attempt > 0:
      wait = wait_hint if wait_hint else 2 ** (attempt - 1) # 1, 2, 4 sec
      logger.warning(f'retrying in {wait}s (attempt {attempt}/{max_retries}): {last_detail}')
      # discard pooled keep-alive connections so the retry opens a fresh connection
      # (a broken edge/proxy can keep returning errors on the same connection)
      http_session.close()
      time.sleep(wait)
      wait_hint = None

    request_start_time = time.perf_counter()
    try:
      response = http_session.get(url, headers=headers, timeout=(10, 30))
    except requests.RequestException as e:
      last_detail = f'request failed ({e.__class__.__name__}: {e}). URL={url}'
      continue
    request_end_time = time.perf_counter()
    logger.info(f'request completed with {(request_end_time - request_start_time) * 1000.0}[ms]. URL={url}')

    if response.status_code in RETRYABLE_STATUS_CODES:
      last_detail = f'HTTP {response.status_code}. URL={url}'
      # honor Retry-After if the server tells us how long to wait (capped at 30s)
      retry_after = response.headers.get('Retry-After')
      if retry_after and retry_after.isdigit():
        wait_hint = min(int(retry_after), 30)
      continue

    # Buckler returns HTTP 403 with a JSON payload (pageProps.common.statusCode=403)
    # when buckler_id is expired/invalid -> no point in retrying
    if response.status_code == 403:
      try:
        payload_status = ((response.json().get('pageProps') or {}).get('common') or {}).get('statusCode')
      except (ValueError, AttributeError):
        payload_status = None
      if payload_status == 403:
        raise ActionRequiredError(f'HTTP 403 with auth-denied payload -- buckler_id is likely expired or invalid. URL={url}')
      last_detail = f'HTTP 403 without auth payload (possibly WAF/blocked). URL={url}'
      continue

    # redirected to the login page -> buckler_id is expired (no point in retrying)
    if response.history and ('auth' in response.url or 'login' in response.url):
      raise ActionRequiredError(f'redirected to login page ({response.url}) -- buckler_id is likely expired. requested URL={url}')

    try:
      data = response.json()
    except ValueError:
      body_head = response.text[:300].replace('\n', ' ')
      last_detail = (f'JSON Parse Error. HTTP {response.status_code}, '
                     f'Content-Type={response.headers.get("Content-Type")}, '
                     f'URL={url}, body[:300]={body_head}')
      if response.status_code == 404:
        # heals at the next batch (updateWrapper refreshes BUILD_ID every batch)
        raise TransientError(f'{last_detail} -- BUILD_ID is likely stale.')
      # non-JSON body with other status (e.g. 200 HTML) may be transient -> retry
      continue

    # Next.js returns a redirect payload instead of page data when auth fails
    if isinstance(data, dict):
      redirect_to = (data.get('pageProps') or {}).get('__N_REDIRECT', '')
      if redirect_to:
        if 'auth' in redirect_to or 'login' in redirect_to:
          raise ActionRequiredError(f'got redirect payload to {redirect_to} -- buckler_id is likely expired. URL={url}')
        raise ActionRequiredError(f'got unexpected redirect payload to {redirect_to}. URL={url}')

    return data

  raise TransientError(f'giving up after {max_retries} retries: {last_detail}')

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
    for page, url in enumerate(urls):
      if (request_skip_flag):
        break

      # pace page requests to be gentle on the server
      if page > 0:
        time.sleep(REQUEST_INTERVAL)

      data = fetch_json(url, headers)

      # if replay_list doesn't exist, break the loop
      page_props = data.get('pageProps') or {}
      if 'replay_list' not in page_props or len(page_props['replay_list']) == 0:
        break

      for replay in page_props['replay_list']:
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
      time.sleep(REQUEST_INTERVAL)
      data = fetch_json(play_url, headers)

      # Get favorite character name
      favorite_character_id = data['pageProps']['fighter_banner_info']['favorite_character_id']
      character_league_infos = data['pageProps']['play']['character_league_infos']
      favorite_character_name = None
      for character_info in character_league_infos:
        if character_info['character_id'] == favorite_character_id:
          favorite_character_name = character_info['character_name']
          break

      # Update item (creates the item if it doesn't exist; update_item instead of
      # put_item so that manually managed attributes like Disabled are preserved)
      response = table_user.update_item(
        Key={'UserCode': user_code},
        UpdateExpression='SET FighterId = :fighter_id, CharacterName = :character_name, CurrentLP = :current_lp',
        ExpressionAttributeValues={
          ':fighter_id': data['pageProps']['fighter_banner_info']['personal_info']['fighter_id'],
          ':character_name': favorite_character_name,
          ':current_lp': data['pageProps']['fighter_banner_info']['favorite_character_league_info']['league_point']
        }
      )
      logger.info(f'update item in User table (UserCode={user_code})')

    # Record fetch time for the fetchNow cooldown in retrieveBattleLog.
    # Runs on every successful fetch (with or without new records), but only for
    # registered users: attribute_exists prevents creating a partial User item
    # (e.g. CharacterName missing) for codes that are not registered yet.
    try:
      table_user.update_item(
        Key={'UserCode': user_code},
        UpdateExpression='SET LastFetchedAt = :now',
        ConditionExpression='attribute_exists(UserCode)',
        ExpressionAttributeValues={':now': int(time.time())}
      )
    except dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
      pass

  except TransientError as e:
    # no SNS: async retry re-runs this function in a few minutes, and the next
    # batch fills any remaining gap. if all retries fail and the update is
    # dropped, the AsyncEventsDropped CloudWatch alarm notifies instead.
    logger.error(f'Error occurred (transient, not notified): {e}')
    raise
  except ActionRequiredError as e:
    # no SNS from here: this fires identically for every user, so notifying per
    # invocation produced one mail per user per async retry. updateWrapper
    # checks buckler_id once at the start of each batch and sends a single
    # mail instead (see check_buckler_id there).
    logger.error(f'Error occurred (action required, notified by updateWrapper): {e}')
    raise
  except Exception as e:
    logger.error(f'Error occurred: {e}')
    sns.publish(
      TopicArn=SNS_TOPIC_ARN,
      Message=f"An error occurred in the Lambda function: {e}",
      Subject=f"[ACTION REQUIRED] updateBattleLog error (UserCode={user_code})"
    )
    raise

  return {
    'statusCode': 200,
    'body': json.dumps('Successfully Completed.')
  }
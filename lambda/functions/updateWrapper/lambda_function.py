import boto3
from boto3.dynamodb.conditions import Attr
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

# Interval between updateBattleLog invocations to spread out requests to the server (seconds)
INVOKE_INTERVAL = float(os.environ.get('INVOKE_INTERVAL', '3'))

# Initialize a DynamoDB resources
dynamodb = boto3.resource('dynamodb')
table_user = dynamodb.Table('User')
table_battlelog = dynamodb.Table('BattleLog')

# Initialize Lambda
lambda_client = boto3.client('lambda')

# Initialize SNS
sns = boto3.client('sns')
SNS_TOPIC_ARN = "arn:aws:sns:ap-northeast-1:572065744477:email-notification"

# update environment variable for lambda
def update_lambda_environment(fname, new_environment_variables):
  response = lambda_client.get_function_configuration(FunctionName=fname)
  current_env_vars = response['Environment']['Variables']

  # skip if nothing changes (update_function_configuration recycles warm
  # containers, so needless updates just cause cold starts)
  if all(current_env_vars.get(k) == v for k, v in new_environment_variables.items()):
    logger.info(f"environment variables of {fname} are unchanged. skip updating.")
    return

  current_env_vars.update(new_environment_variables)
  lambda_client.update_function_configuration(
    FunctionName=fname,
    Environment={'Variables': current_env_vars}
  )

  # update_function_configuration is async: without waiting, the first
  # invocations of this batch can run on warm containers that still hold
  # the old BUILD_ID and fail with 404
  lambda_client.get_waiter('function_updated_v2').wait(
    FunctionName=fname,
    WaiterConfig={'Delay': 2, 'MaxAttempts': 30}
  )
  logger.info(f"configuration update of {fname} has been applied.")

# Check buckler_id once per batch, before fanning out.
#
# When buckler_id dies every user fails identically, and notifying from
# updateBattleLog meant one mail per invocation -- users x async retries
# (13 users -> 39 mails on 2026-07-28). Checking once here means one mail per
# batch, and it also keeps the doomed requests (users x up to 10 pages) off
# Buckler entirely.
#
# Returns True when the batch should proceed. Costs one extra request per
# batch, which is the price of not sending ~130 pointless ones when it fails.
def check_buckler_id(build_id, user_code):
  env_vars = lambda_client.get_function_configuration(
    FunctionName='updateBattleLog'
  )['Environment']['Variables']
  buckler_id = env_vars['BUCKLER_ID']
  gid = env_vars['GID']

  # same header construction as updateBattleLog, so the check is representative
  headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
    'Cookie': f"CookieConsent={{'stamp':'6oNLBjPlhgvQsfXTcT3nYo80bz5NQ0zBXB/8f2bTC8qu7EGMr60Y/w==','necessary':True,'preferences':True,'statistics':True,'marketing':True,'method':'explicit','ver':2,'utc':1691968880965,'region':'jp'}}; buckler_id={buckler_id}; _gid={gid}"
  }
  url = f'https://www.streetfighter.com/6/buckler/_next/data/{build_id}/ja-jp/profile/{user_code}/battlelog.json?sid={user_code}'

  try:
    response = requests.get(url, headers=headers, timeout=(10, 30))
  except requests.RequestException as e:
    # a blip here must not block the batch: updateBattleLog has its own retries
    logger.warning(f'buckler_id check skipped (request failed: {e.__class__.__name__}: {e})')
    return True

  # HTTP 403 with pageProps.common.statusCode=403 is how Buckler reports an
  # expired/invalid buckler_id (a plain 403 is more likely WAF -> let the batch
  # run and leave the retry handling to updateBattleLog)
  if response.status_code == 403:
    try:
      payload_status = ((response.json().get('pageProps') or {}).get('common') or {}).get('statusCode')
    except (ValueError, AttributeError):
      payload_status = None
    if payload_status == 403:
      return False

  logger.info(f'buckler_id check passed (HTTP {response.status_code})')
  return True

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
  # Get User List (skip manually disabled users; see lambda/scripts/set-user-disabled.sh)
  response = table_user.scan(
    ProjectionExpression='UserCode',
    FilterExpression=Attr('Disabled').not_exists(),
    Limit=USER_LIMIT
  )
  items = response['Items']

  ##
  ## Check buckler_id
  ##
  # Skip the whole batch if the cookie is dead: every invocation would fail the
  # same way, so this is one mail instead of one per user per retry.
  if items and not check_buckler_id(build_id, items[0]['UserCode']):
    logger.error('buckler_id is likely expired or invalid. skipping this batch.')
    sns.publish(
      TopicArn=SNS_TOPIC_ARN,
      Subject="[ACTION REQUIRED] buckler_id is likely expired",
      Message=(
        "The buckler_id cookie was rejected by Buckler (HTTP 403 with auth-denied payload), "
        "so this batch was skipped without invoking updateBattleLog.\n\n"
        "Fix: log in to Buckler in a browser, copy the full buckler_id cookie value "
        "(64 chars) and update the BUCKLER_ID environment variable of updateBattleLog. "
        "See the 'buckler_id の更新' section of CLAUDE.md.\n\n"
        "Updates resume automatically at the next batch."
      )
    )
    return {
      'statusCode': 200,
      'body': json.dumps("Skipped: buckler_id is likely expired")
    }

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
    time.sleep(INVOKE_INTERVAL)
  logger.info(f"{len(items)} items are successfully invoked. USER_LIMIT={USER_LIMIT}")

  # Return JSON
  return {
    'statusCode': 200,
    'body': json.dumps("Success")
  }
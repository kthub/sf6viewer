import boto3
import json
import logging
import time
from datetime import datetime, timedelta, timezone

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

JST = timezone(timedelta(hours=9))

# Initialize clients
logs = boto3.client('logs')
cloudwatch = boto3.client('cloudwatch')
sns = boto3.client('sns')
dynamodb = boto3.resource('dynamodb')
table_user = dynamodb.Table('User')

SNS_TOPIC_ARN = "arn:aws:sns:ap-northeast-1:572065744477:email-notification"

LOG_GROUPS = {
  'retrieveBattleLog': '/aws/lambda/retrieveBattleLog',
  'updateBattleLog': '/aws/lambda/updateBattleLog',
  'updateWrapper': '/aws/lambda/updateWrapper',
}

LOG_STORAGE_FREE_TIER_BYTES = 5 * 1024 ** 3  # 5GB

# Report period: previous calendar month in JST
# (can be overridden for testing with event["REPORT_MONTH"] = "YYYY-MM")
def report_period(event):
  report_month = event.get('REPORT_MONTH') if isinstance(event, dict) else None
  if report_month:
    start = datetime.strptime(report_month, '%Y-%m').replace(tzinfo=JST)
  else:
    this_month = datetime.now(JST).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    start = (this_month - timedelta(days=1)).replace(day=1)
  if start.month == 12:
    end = start.replace(year=start.year + 1, month=1)
  else:
    end = start.replace(month=start.month + 1)
  return start, end

# Run a CloudWatch Logs Insights query and wait for the result.
# Scan cost is bounded by [start, end), so it stays flat no matter
# how long the logs are retained.
def run_query(log_group, query, start, end):
  query_id = logs.start_query(
    logGroupName=log_group,
    startTime=int(start.timestamp()),
    endTime=int(end.timestamp()),
    queryString=query
  )['queryId']
  while True:
    response = logs.get_query_results(queryId=query_id)
    if response['status'] not in ('Scheduled', 'Running'):
      break
    time.sleep(1)
  if response['status'] != 'Complete':
    raise Exception(f"Logs Insights query {response['status']} (log_group={log_group})")
  # strip() because values parsed from the end of a log line keep its trailing newline
  return [{col['field']: col['value'].strip() for col in row} for row in response['results']]

# Monthly sum of a Lambda metric (0 if no datapoints)
def lambda_metric_sum(function_name, metric_name, start, end):
  response = cloudwatch.get_metric_statistics(
    Namespace='AWS/Lambda',
    MetricName=metric_name,
    Dimensions=[{'Name': 'FunctionName', 'Value': function_name}],
    StartTime=start, EndTime=end, Period=86400, Statistics=['Sum']
  )
  return int(sum(dp['Sum'] for dp in response['Datapoints']))

# Monthly ingested bytes of a log group
def log_incoming_bytes(log_group, start, end):
  response = cloudwatch.get_metric_statistics(
    Namespace='AWS/Logs',
    MetricName='IncomingBytes',
    Dimensions=[{'Name': 'LogGroupName', 'Value': log_group}],
    StartTime=start, EndTime=end, Period=86400, Statistics=['Sum']
  )
  return int(sum(dp['Sum'] for dp in response['Datapoints']))

def format_bytes(n):
  for unit in ('B', 'KB', 'MB', 'GB'):
    if n < 1024 or unit == 'GB':
      return f'{n:.1f} {unit}' if unit != 'B' else f'{int(n)} {unit}'
    n /= 1024

# Classify an "Error occurred" log line (same buckets as the notification design)
def classify_error(detail):
  if 'buckler_id' in detail:
    return 'buckler_id (ACTION REQUIRED)'
  if 'BUILD_ID' in detail:
    return 'stale BUILD_ID'
  for code in ('502', '503', '500', '504', '429'):
    if f'HTTP {code}' in detail:
      return f'HTTP {code}'
  if 'request failed' in detail:
    return 'connection error'
  return 'other: ' + detail[:60]

def build_report(start, end):
  ##
  ## Usage (page views)
  ##
  views = run_query(
    LOG_GROUPS['retrieveBattleLog'],
    'parse @message "user_code : *" as uc | filter ispresent(uc)'
    ' | stats count(*) as cnt by uc | sort cnt desc',
    start, end
  )
  total_views = sum(int(v['cnt']) for v in views)
  fetch_now = run_query(
    LOG_GROUPS['retrieveBattleLog'],
    'filter @message like /fetch_now: True/ | stats count(*) as cnt',
    start, end
  )
  fetch_now_count = int(fetch_now[0]['cnt']) if fetch_now and 'cnt' in fetch_now[0] else 0

  # UserCode -> FighterId, and enabled/disabled counts
  users = table_user.scan(ProjectionExpression='UserCode, FighterId, Disabled')['Items']
  fighter_ids = {u['UserCode']: u.get('FighterId', '?') for u in users}
  disabled_count = sum(1 for u in users if u.get('Disabled'))

  ##
  ## Batch updates
  ##
  new_records = run_query(
    LOG_GROUPS['updateBattleLog'],
    'parse @message "new record detected. (* items)" as n | filter ispresent(n)'
    ' | stats sum(n) as total',
    start, end
  )
  new_record_count = int(float(new_records[0]['total'])) if new_records and new_records[0].get('total') else 0

  build_ids = run_query(
    LOG_GROUPS['updateWrapper'],
    'fields @timestamp | parse @message "update build id with : *" as bid'
    ' | filter ispresent(bid) | sort @timestamp asc | limit 10000',
    start, end
  )
  build_id_changes = sum(1 for prev, cur in zip(build_ids, build_ids[1:]) if prev['bid'] != cur['bid'])

  ##
  ## Errors
  ##
  errors = run_query(
    LOG_GROUPS['updateBattleLog'],
    'fields @message | filter @message like /Error occurred/ | limit 10000',
    start, end
  )
  error_kinds = {}
  for e in errors:
    detail = e['@message'].split('Error occurred', 1)[1]
    kind = classify_error(detail)
    error_kinds[kind] = error_kinds.get(kind, 0) + 1

  metrics = {}
  for fname in ('updateWrapper', 'updateBattleLog', 'retrieveBattleLog'):
    metrics[fname] = {m: lambda_metric_sum(fname, m, start, end)
                      for m in ('Invocations', 'Errors', 'AsyncEventsDropped')}

  ##
  ## Log usage
  ##
  stored_total = sum(g.get('storedBytes', 0)
                     for page in logs.get_paginator('describe_log_groups').paginate()
                     for g in page['logGroups'])
  incoming = {name: log_incoming_bytes(group, start, end) for name, group in LOG_GROUPS.items()}

  ##
  ## Compose the report
  ##
  lines = []
  lines.append(f'[SF6 Viewer] Monthly Report {start:%Y-%m}')
  lines.append(f'(period: {start:%Y-%m-%d} - {(end - timedelta(days=1)):%Y-%m-%d} JST)')
  lines.append('')
  lines.append('== Usage ==')
  lines.append(f'- page views (retrieveBattleLog): {total_views} (fetchNow: {fetch_now_count})')
  lines.append(f'- viewed users: {len(views)}')
  for v in views[:5]:
    uc = v['uc']
    lines.append(f'    {fighter_ids.get(uc, "(unregistered)")} ({uc}): {v["cnt"]}')
  lines.append(f'- registered users: {len(users)} (update target: {len(users) - disabled_count} / disabled: {disabled_count})')
  lines.append('')
  lines.append('== Batch updates ==')
  for fname in ('updateWrapper', 'updateBattleLog'):
    m = metrics[fname]
    lines.append(f'- {fname}: {m["Invocations"]} invocations / {m["Errors"]} errors / {m["AsyncEventsDropped"]} dropped')
  lines.append(f'- new battle records: {new_record_count}')
  lines.append(f'- buildId changes: {build_id_changes}')
  lines.append('')
  lines.append('== Errors (updateBattleLog) ==')
  if error_kinds:
    for kind, count in sorted(error_kinds.items(), key=lambda x: -x[1]):
      lines.append(f'- {kind}: {count}')
  else:
    lines.append('- none')
  lines.append('')
  lines.append('== Log usage ==')
  lines.append(f'- total stored (all log groups): {format_bytes(stored_total)}'
               f' ({stored_total / LOG_STORAGE_FREE_TIER_BYTES * 100:.1f}% of 5GB free tier)')
  lines.append(f'- ingested this month:')
  for name, n in incoming.items():
    lines.append(f'    {name}: {format_bytes(n)}')
  return '\n'.join(lines)

def lambda_handler(event, context):
  try:
    start, end = report_period(event)
    report = build_report(start, end)
    logger.info(report)
    sns.publish(
      TopicArn=SNS_TOPIC_ARN,
      Message=report,
      Subject=f'[SF6 Viewer] Monthly Report {start:%Y-%m}'
    )
  except Exception as e:
    logger.error(f'Error occurred: {e}')
    sns.publish(
      TopicArn=SNS_TOPIC_ARN,
      Message=f'An error occurred in the Lambda function: {e}',
      Subject='[ACTION REQUIRED] monthlyReport error'
    )
    raise

  return {
    'statusCode': 200,
    'body': json.dumps('Successfully Completed.')
  }

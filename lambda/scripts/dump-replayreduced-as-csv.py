#!/opt/homebrew/bin/python3
##
## Export battle log as csv
##
import requests
import csv
import sys
from datetime import datetime
import pytz
import configparser

##
## Settings
##
config = configparser.ConfigParser()
config.read('dump-replayreduced-as-csv-config.ini')

user_code = config['Settings']['user_code']
days = config['Settings']['days']
#days = 10 # overwrite settings
aws_api_gateway_url = config['Settings']['aws_api_gateway_url']

##
## Functions
##
def utc_to_jst(utc_timestamp):
  utc_datetime = datetime.utcfromtimestamp(utc_timestamp)
  utc_datetime = pytz.utc.localize(utc_datetime)
  jst_datetime = utc_datetime.astimezone(pytz.timezone('Asia/Tokyo'))
  return jst_datetime.strftime('%Y/%m/%d %H:%M:%S')

def battle_log_to_csv(battle_log_list):
  csv_list = []
  for battle_log in battle_log_list:
    replay_reduced = battle_log["ReplayReduced"]
    opponent = replay_reduced["opponent"]
    csv_list.append({
      'UploadedAt': utc_to_jst((battle_log["UploadedAt"])),
      'FighterID': replay_reduced["fighter_id"],
      'ShortID': replay_reduced["short_id"],
      'PlatformName': replay_reduced["platform_name"],
      'CharacterName': replay_reduced["character_name"],
      'LeaguePoint': replay_reduced["league_point"],
      'BattleInputTypeName': replay_reduced["battle_input_type_name"],
      'Result': replay_reduced["result"],
      'RoundResults': "[" + ",".join(map(str, replay_reduced["round_results"])) + "]",
      'OpponentFighterID': opponent["fighter_id"],
      'OpponentShortID': opponent["short_id"],
      'OpponentPlatformName': opponent["platform_name"],
      'OpponentCharacterName': opponent["character_name"],
      'OpponentLeaguePoint': opponent["league_point"],
      'OpponentBattleInputTypeName': opponent["battle_input_type_name"],
      'OpponentRoundResults': "[" + ",".join(map(str, opponent["round_results"])) + "]",
      'Side': replay_reduced["side"],
      'ReplayID': replay_reduced["replay_id"],
      'Views': replay_reduced["views"],
      'ReplayBattleTypeName': replay_reduced["replay_battle_type_name"]
    })
  return csv_list

##
## main
##
# get battle log
url = f'https://{aws_api_gateway_url}/retrieveBattleLog?USER_CODE={user_code}&RETRIEVE_OPTION={days}'
response = requests.get(url)
response.raise_for_status()
battle_log_list = response.json()

# convert battle log to csv list
csv_list = battle_log_to_csv(battle_log_list)
sorted_csv_list = sorted(csv_list, key=lambda x: x['UploadedAt'], reverse=True)

# print csv list to stdout
fieldnames = sorted_csv_list[0].keys()
writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)
writer.writeheader()
writer.writerows(sorted_csv_list)
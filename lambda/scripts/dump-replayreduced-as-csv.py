#!/opt/homebrew/bin/python3
##
## Export battle log as csv (last 90 days)
##
import requests
import csv
import json
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
aws_api_gateway_url = config['Settings']['aws_api_gateway_url']

##
## Code
##
def utc_to_jst(utc_timestamp):
    utc_datetime = datetime.utcfromtimestamp(utc_timestamp)
    utc_datetime = pytz.utc.localize(utc_datetime)
    jst_datetime = utc_datetime.astimezone(pytz.timezone('Asia/Tokyo'))
    return jst_datetime.strftime('%Y/%m/%d %H:%M:%S')

def json_to_csv(url):
    # Send a GET request to the URL
    response = requests.get(url)
    response.raise_for_status()  # Check for errors

    # Load JSON data
    json_data = response.json()

    # Assume the JSON data is a list of dictionaries, if not, adjust accordingly
    data_list = json_data

    if not data_list:
        return  # Return early if the list is empty

    # Create a CSV writer object
    writer = csv.writer(sys.stdout)

    # Write the header
    header = [
        "UploadedAt", "FighterID", "ShortID", "PlatformName", "CharacterName", "LeaguePoint",
        "BattleInputTypeName", "Result", "RoundResults", "OpponentFighterID", "OpponentShortID",
        "OpponentPlatformName", "OpponentCharacterName", "OpponentLeaguePoint",
        "OpponentBattleInputTypeName", "OpponentRoundResults", "Side",
        "ReplayID", "Views", "ReplayBattleTypeName"
    ]
    writer.writerow(header)

    # Write the data rows
    for row in data_list:
        replay_reduced = row["ReplayReduced"]
        opponent = replay_reduced["opponent"]
        uploaded_at = utc_to_jst((row["UploadedAt"]))
        data_row = [
            uploaded_at, replay_reduced["fighter_id"], replay_reduced["short_id"], replay_reduced["platform_name"],
            replay_reduced["character_name"], replay_reduced["league_point"], replay_reduced["battle_input_type_name"],
            replay_reduced["result"],
            "[" + ",".join(map(str, replay_reduced["round_results"])) + "]", opponent["fighter_id"], opponent["short_id"],
            opponent["platform_name"], opponent["character_name"], opponent["league_point"],
            opponent["battle_input_type_name"], "[" + ",".join(map(str, opponent["round_results"])) + "]",
            replay_reduced["side"], replay_reduced["replay_id"],
            replay_reduced["views"], replay_reduced["replay_battle_type_name"]
        ]
        writer.writerow(data_row)

# API Gateway URL
url = f'https://{aws_api_gateway_url}/retrieveBattleLog?USER_CODE={user_code}&RETRIEVE_OPTION={days}'
json_to_csv(url)
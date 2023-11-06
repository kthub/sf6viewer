#!/bin/sh
# Obtain battlelog JSON from BUCKLER'S BOOT CAMP (STREET FIGHTER 6)

##
## Configuration
##
SCRIPT_DIR=$(cd $(dirname $0); pwd)
source ${SCRIPT_DIR}/get_json_from_bbc_secrets.sh

##
## Main
##
# Target URL
URL1=https://www.streetfighter.com/6/buckler/_next/data/${SERVER_ID}/ja-jp/profile/${USER_CODE}/battlelog.json?sid=${USER_CODE}
URL2=${URL1}\&page=9  # 2ページ目以降はページ数を指定する。10より大きな値を指定すると10を指定した場合と同じになるようだ。

# User-Agent
USER_AGENT="User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"

# Cookie
COOKIE_CONSENT="{stamp:%276oNLBjPlhgvQsfXTcT3nYo80bz5NQ0zBXB/8f2bTC8qu7EGMr60Y/w==%27%2Cnecessary:true%2Cpreferences:true%2Cstatistics:true%2Cmarketing:true%2Cmethod:%27explicit%27%2Cver:2%2Cutc:1691968880965%2Cregion:%27jp%27}"
COOKIE_DATA="CookieConsent=${COOKIE_CONSENT}; buckler_id=${BUCKLER_ID}; _gid=${GID}"

# Query
curl -s ${URL2} \
  -H "${USER_AGENT}" \
  -H "Cookie: '${COOKIE_DATA}'" \
   | jq '.pageProps.replay_list[] | {player1: .player1_info | {character_name: .character_name, round_results: .round_results}, player2: .player2_info | {character_name: .character_name, round_results: .round_results}}'

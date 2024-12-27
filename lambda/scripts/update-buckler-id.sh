#!/bin/sh
set -e # exit when any command fails

SCRIPT_DIR=$(cd $(dirname $0); pwd)
. ${SCRIPT_DIR}/update-buckler-id-secrets.sh

# get buckler_id (new login)
BUCKLER_ID=$(python ${SCRIPT_DIR}/update-buckler-id.py)
echo "BUCKLER_ID=${BUCKLER_ID}"

# get current environment variables
CURRENT_ENV=$(aws lambda get-function-configuration --function-name updateBattleLog --query 'Environment.Variables' --output json)
echo "CURRENT_ENV=${CURRENT_ENV}"

# create updated environment variables
UPDATED_ENV=$(echo $CURRENT_ENV | jq --arg BUCKLER_ID "$BUCKLER_ID" '.BUCKLER_ID = $BUCKLER_ID')
echo "UPDATED_ENV=${UPDATED_ENV}"

# create temporary file
TEMP_FILE=UPDATED_BUCKLER_ID_ENV_TMP.json
echo "{\"Variables\": $UPDATED_ENV}" > $TEMP_FILE

# update environmental variables
aws lambda update-function-configuration \
  --function-name updateBattleLog \
  --environment "file://$TEMP_FILE"

# remove the temporary file
rm $TEMP_FILE

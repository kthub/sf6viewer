#!/bin/sh
set -e # exit when any command fails

# get buckler_id from clip board
BUCKLER_ID=$(pbpaste)
echo "BUCKLER_ID=${BUCKLER_ID}"

# validate buckler_id
length=${#BUCKLER_ID}
if [[ $length -ge 60 && $length -le 70 ]]; then
  if [[ $BUCKLER_ID =~ " " ]]; then
    echo "Invalid buckler_id: contains space."
    exit 1
  fi
else
  echo "Invalid buckler_id: length is not between 60 and 70."
  exit 1
fi

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

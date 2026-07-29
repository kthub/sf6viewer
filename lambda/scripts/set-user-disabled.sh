#!/bin/sh
# Enable/disable a user for the 3-hourly batch update (updateWrapper).
# Disabled users keep their BattleLog history and can still be viewed;
# only the periodic scraping stops.
#
# usage:
#   set-user-disabled.sh <UserCode> on    # exclude from batch update
#   set-user-disabled.sh <UserCode> off   # include in batch update again
#   set-user-disabled.sh --list           # show all users and their status

if [ "$1" = "--list" ]; then
  aws dynamodb scan --table-name User \
        --projection-expression 'UserCode, FighterId, Disabled' \
        --query 'Items[].[UserCode.S, FighterId.S, Disabled.BOOL]' \
        --output text \
    | sed -e 's/	True$/	DISABLED/' -e 's/	None$/	enabled/' \
    | sort -k3
  exit 0
fi

USER_CODE=$1
MODE=$2

case "${USER_CODE}" in
  [0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]) ;;
  *) echo "ERROR : UserCode must be a 10-digit number." ; exit 1 ;;
esac

if [ "${MODE}" = "on" ]; then
  aws dynamodb update-item --table-name User \
        --key "{\"UserCode\":{\"S\":\"${USER_CODE}\"}}" \
        --update-expression 'SET Disabled = :true' \
        --expression-attribute-values '{":true":{"BOOL":true}}' \
        --condition-expression 'attribute_exists(UserCode)'
elif [ "${MODE}" = "off" ]; then
  aws dynamodb update-item --table-name User \
        --key "{\"UserCode\":{\"S\":\"${USER_CODE}\"}}" \
        --update-expression 'REMOVE Disabled' \
        --condition-expression 'attribute_exists(UserCode)'
else
  echo "usage: $0 <UserCode> on|off  (or $0 --list)"
  exit 1
fi

if [ $? -eq 0 ]; then
  echo "SUCCESS : UserCode=${USER_CODE} is now ${MODE} (on=excluded from batch update)."
else
  echo "ERROR : failed to update UserCode=${USER_CODE} (not registered?)."
  exit 1
fi

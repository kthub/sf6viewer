#!/bin/sh
echo "start deploy process..."
if [ -f deployment-package.zip ]; then
  aws lambda update-function-code --function-name updateBattleLog --zip-file fileb://deployment-package.zip
  if [ $? -eq 0 ]; then
    echo "SUCCESS : deployment is completed."
  else
    echo "ERROR : failed to update the function."
  fi
else
  echo "ERROR : deploy archive does not exist."
fi
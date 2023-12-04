#!/bin/sh
echo "start deploying layer..."
if [ -f layer-package.zip ]; then
  aws lambda publish-layer-version \
        --layer-name "web-scraping" \
        --description "libraries required for web scraping." \
        --zip-file fileb://layer-package.zip \
        --compatible-architectures x86_64 \
        --compatible-runtimes python3.11
  if [ $? -eq 0 ]; then
    echo "SUCCESS : deployment is completed."
  else
    echo "ERROR : failed to update the layer."
  fi
else
  echo "ERROR : deploy archive does not exist."
fi
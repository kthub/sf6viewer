#!/bin/sh
SCRIPT_DIR=$(cd $(dirname $0); pwd)
FUNCTION_NAME=$(basename ${SCRIPT_DIR})

${SCRIPT_DIR}/../../scripts/deploy_lambda.sh ${FUNCTION_NAME}

#!/bin/sh
SCRIPT_DIR=$(cd $(dirname $0); pwd)
FUNCTION_NAME=$1
FUNCTION_DIR=${SCRIPT_DIR}/../functions/${FUNCTION_NAME}
WORK_DIR=${FUNCTION_DIR}/work
DEPLOY_PACKAGE=deployment-package.zip

# create work directory
if [ ! -d ${WORK_DIR} ]; then
    mkdir -p ${WORK_DIR}
fi
cd ${WORK_DIR}

##
## create deployment package
##
# copy resources
cp -p ${FUNCTION_DIR}/*.py ${WORK_DIR}

# create deployment-package
zip -r ${DEPLOY_PACKAGE} . > /dev/null 2>&1

##
## deploy function
##
if [ -f ${DEPLOY_PACKAGE} ]; then
  aws lambda update-function-code \
        --function-name ${FUNCTION_NAME} \
        --zip-file fileb://${DEPLOY_PACKAGE} > /dev/null 2>&1
  if [ $? -eq 0 ]; then
    echo "SUCCESS : ${FUNCTION_NAME} is successfully updated."
  else
    echo "ERROR : failed to update the function."
  fi
else
  echo "ERROR : failed to create the deploy package."
fi

# cleanup work directory
cd ${FUNCTION_DIR}
rm -rf ${WORK_DIR}

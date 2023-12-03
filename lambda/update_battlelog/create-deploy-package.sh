#!/bin/sh
SCRIPT_DIR=$(cd $(dirname $0); pwd)
PROJ_DIR=${SCRIPT_DIR}
WORK_DIR=${PROJ_DIR}/work

##
## prepare python dependencies (need to execute only one time)
##
#python3 -m venv ${PROJ_DIR}/.venv
#source ${PROJ_DIR}/.venv/bin/activate
#pip3 install requests

##
## create deployment package
##
# cleanup
#rm -rf ${WORK_DIR}/*

# copy resources
cp -p ${PROJ_DIR}/lambda_function.py ${WORK_DIR}
cp -p ${PROJ_DIR}/replay_utils.py ${WORK_DIR}
cp -r ${PROJ_DIR}/.venv/lib/python3.11/site-packages/* ${WORK_DIR}

# create deployment-package
cd ${WORK_DIR}
zip -r deployment-package.zip .
mv deployment-package.zip ${PROJ_DIR}

# cleanup
rm -rf ${WORK_DIR}/*
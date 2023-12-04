#!/bin/sh
SCRIPT_DIR=$(cd $(dirname $0); pwd)
PROJ_DIR=${SCRIPT_DIR}
WORK_DIR=${PROJ_DIR}/work

##
## for the first time
##
#python3 -m venv ${PROJ_DIR}/.venv
#source ${PROJ_DIR}/.venv/bin/activate
#pip3 install requests beautifulsoup4
#deactivate

##
## for upgrade
##
source ${PROJ_DIR}/.venv/bin/activate
pip3 install --upgrade requests beautifulsoup4
deactivate

##
## create deployment package
##

# create work directory
if [ ! -d ${WORK_DIR} ]; then
    mkdir -p ${WORK_DIR}
fi

# copy python resources
mkdir ${WORK_DIR}/python # top-level directory for python (defined by lambda layer specification)
cp -r ${PROJ_DIR}/.venv/lib/python3.11/site-packages/* ${WORK_DIR}/python
#
# place holder : add copy command for other python resources
#

# create deployment-package
cd ${WORK_DIR}
zip -r layer-package.zip .
mv layer-package.zip ${PROJ_DIR}

# cleanup
rm -rf ${WORK_DIR}
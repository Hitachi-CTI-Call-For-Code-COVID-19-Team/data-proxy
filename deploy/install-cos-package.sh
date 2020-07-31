#!/bin/sh

# reference:
# https://cloud.ibm.com/docs/openwhisk?topic=openwhisk-pkg_obstorage

if [ $# -lt 1 ]; then
	echo "usage:"
  echo "./install-cos-package.sh REGION"
	exit 1
fi

REGION=$1
SCRIPT_DIR=$(cd $(dirname $0); pwd)

git clone https://github.com/ibm-functions/package-cloud-object-storage.git 
pushd .
cp ${SCRIPT_DIR}/../replaced/object-read.js package-cloud-object-storage/runtimes/nodejs/actions/
cp ${SCRIPT_DIR}/../replaced/object-write.js package-cloud-object-storage/runtimes/nodejs/actions/
cd package-cloud-object-storage/runtimes/nodejs
ibmcloud fn deploy
# ibm cloud shows us the cos endpoint as s3.tok.ap.cloud-object-storage.appdomain.cloud
# but it doesn't work.
ibmcloud fn package update cloud-object-storage --param endpoint s3.${REGION}.cloud-object-storage.appdomain.cloud
ibmcloud fn package list

popd
rm -rf package-cloud-object-storage
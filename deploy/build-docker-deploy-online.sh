#!/bin/bash
set -x

VERSION="v"$(date "+%Y%m%d%H%M%S")
cd ../
docker build -f Dockerfile -t autogpt:${VERSION} .
cd -

ONLINE_DIR=/root/Deploy/autogpt/autogpt_backend

cp docker-componse.yaml ${ONLINE_DIR}
cp envoy.yaml ${ONLINE_DIR}

cd ${ONLINE_DIR}
sed -i "/AUTOGPT_VERSION/s/AUTOGPT_VERSION.*/AUTOGPT_VERSION=${VERSION}/g" .env
cat .env

docker-compose up -d

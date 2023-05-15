#!/bin/bash
set -x

VERSION="v"$(date "+%Y%m%d%H%M%S")
docker build -f Dockerfile -t autogpt:${VERSION} .

cd /root/Deploy/autogpt/autogpt_backend
sed -i "/AUTOGPT_VERSION/s/AUTOGPT_VERSION.*/AUTOGPT_VERSION=${VERSION}/g" .env
cat .env

docker-compose up -d

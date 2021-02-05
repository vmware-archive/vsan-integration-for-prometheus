#!/bin/bash
# Copyright (c) 2020-2021 VMware, Inc. All Rights Reserved
# SPDX-License-Identifier: BSD-2
while getopts n: option
do
case "${option}"
in
n) NAME=${OPTARG};;
esac
done

UPPER_NAME=$(echo "$NAME" | tr '[:lower:]' '[:upper:]')
TAG_ENV="${UPPER_NAME}_TAG"

cat ~/dockerPassword.txt |docker login --username svc.humbug --password-stdin sabu-persistence-service-docker-local.artifactory.eng.vmware.com
export TAG=${CI_COMMIT_SHA:0:8}
export $TAG_ENV=$TAG
echo $TAG > ~/$name_tag.txt
cd vsan-prometheus-$NAME
docker build -t sabu-persistence-service-docker-local.artifactory.eng.vmware.com/vsan-prometheus-$NAME:${TAG} .
docker push sabu-persistence-service-docker-local.artifactory.eng.vmware.com/vsan-prometheus-$NAME:${TAG}

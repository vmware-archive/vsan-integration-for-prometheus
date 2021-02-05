# Copyright (c) 2020-2021 VMware, Inc. All Rights Reserved
# SPDX-License-Identifier: BSD-2

docker pull $REPO/vsan-prometheus-servicediscovery:$TAG
docker pull $REPO/vsan-prometheus-setup:$TAG
docker pull $REPO/vsan-prometheus-operator:$TAG
docker pull $REPO/vsan-prometheus-exporter:$TAG

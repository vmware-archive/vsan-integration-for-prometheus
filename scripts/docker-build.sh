# Copyright (c) 2020-2021 VMware, Inc. All Rights Reserved
# SPDX-License-Identifier: BSD-2

docker build -t vsan-prometheus-servicediscovery:$TAG vsan-prometheus-servicediscovery
docker build -t vsan-prometheus-setup:$TAG vsan-prometheus-setup
docker build -t vsan-prometheus-operator:$TAG vsan-prometheus-operator
docker build -t vsan-prometheus-exporter:$TAG vsan-prometheus-exporter

# Copyright (c) 2020-2021 VMware, Inc. All Rights Reserved
# SPDX-License-Identifier: BSD-2

pip3 install -r tests/requirements.txt
export KUBECONFIG=/etc/kubernetes/admin.conf
SERVICEDISCOVERY_TAG=$(< ~/servicediscovery_tag.txt)
SETUP_TAG=$(< ~/setup_tag.txt)
OPERATOR_TAG=$(< ~/operator_tag.txt)
EXPORTER_TAG=$(< ~/exporter_tag.txt)
export SERVICEDISCOVERY_TAG
export SETUP_TAG
export OPERATOR_TAG
export EXPORTER_TAG
python3 tests/unittestRunner.py
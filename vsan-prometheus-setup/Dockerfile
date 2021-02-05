# Copyright (c) 2020-2021 VMware, Inc. All Rights Reserved
# SPDX-License-Identifier: BSD-2
FROM photon:3.0
RUN tdnf install -y python3 python3-pip && pip3 install setuptools && pip3 install pyvmomi && tdnf clean all
WORKDIR /
COPY vsanSetupToken.py vsanapiutils.py vsanmgmtObjects.py /
ENTRYPOINT ["python3", "vsanSetupToken.py"]
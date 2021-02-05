# Copyright (c) 2020-2021 VMware, Inc. All Rights Reserved
# SPDX-License-Identifier: BSD-2
FROM photon:3.0
RUN tdnf install -y python3 python3-pip && pip3 install setuptools && pip3 install pyvmomi flask gunicorn==19.9.0 && tdnf clean all
WORKDIR /
COPY gunicorn.conf wsgi.py server.py connectUtils.py prometheus.py vsanPrometheusStats.py vsanmgmtObjects.py ./
EXPOSE 8080
ENTRYPOINT ["gunicorn", "-c", "gunicorn.conf", "wsgi:app"]
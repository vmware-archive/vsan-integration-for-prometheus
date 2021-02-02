This document describes how to retrieve vSAN metrics stats in prometheus format using the metrics exporter server. It's mainly for release before vSAN 7.0.

## Usage
### Build Docker image
    $ docker build -t vsan-prometheus-exporter .

### Start exporter server
Generate an auth token and use it to start the exporter server. The auth token can be any string, here we use `uuidgen` to make it more random.

If you don't specify the auth token by the environment variable `BEARER_TOKEN`, it will be generated automatically, and you can check it from the log output.

Please write the auth token down as it will be used later when retrieving metrics.

    # generate an auth token
    $ uuidgen
    # start the exporter server with the generated token
    $ docker run --rm -p 8080:8080 -e BEARER_TOKEN=<authToken> -e VCENTER=<vCenterHostname> -e VCPORT=<vCenterPort> -e VCUSER=<vCenterUsername> -e VCPASSWORD=<vCenterPassword> -e CLUSTERNAME=<vCenterClustername> vsan-prometheus-exporter

e.g.:

    $ uuidgen
    d64c4e1d-51b1-461f-8304-f0c7efd6b55c
    $ docker run --rm -p 8080:8080 -e BEARER_TOKEN='d64c4e1d-51b1-461f-8304-f0c7efd6b55c' -e VCENTER='10.160.157.247' -e VCPORT='443' -e VCUSER='administrator@vsphere.local' -e VCPASSWORD='Admin!23' -e CLUSTERNAME='VSAN-Cluster' vsan-prometheus-exporter
    ...
    2019-11-08 08:14:54 +0000 INFO [9|140657098009928] [vsanPrometheusStats::connect] Connected to VC 10.160.157.247 successfully
    ...
    2019-11-08 08:14:57 +0000 INFO [9|140657098009928] [vsanPrometheusStats::connect] Auth token is d64c4e1d-51b1-461f-8304-f0c7efd6b55c

### Get the server list by service discovery
    $ curl -H 'Authorization: Bearer <authToken>' 127.0.0.1:8080/vsan/metrics/serviceDiscovery

e.g.:

    $ curl -H 'Authorization: Bearer d64c4e1d-51b1-461f-8304-f0c7efd6b55c' 127.0.0.1:8080/vsan/metrics/serviceDiscovery
    [{"labels":{"__metrics_path__":"/vsan/metrics/host-16","cluster_id":"domain-c8","cluster_name":"VSAN-Cluster"},"targets":["127.0.0.1:8080"]},{"labels":{"__metrics_path__":"/vsan/metrics/host-22","cluster_id":"domain-c8","cluster_name":"VSAN-Cluster"},"targets":["127.0.0.1:8080"]},{"labels":{"__metrics_path__":"/vsan/metrics/host-28","cluster_id":"domain-c8","cluster_name":"VSAN-Cluster"},"targets":["127.0.0.1:8080"]},{"labels":{"__metrics_path__":"/vsan/metrics/host-34","cluster_id":"domain-c8","cluster_name":"VSAN-Cluster"},"targets":["127.0.0.1:8080"]}]

### Retrieve metrics for all hosts in the cluster
The auth token must be included in the request header, it's printed after connecting to VC successfully.

    $ curl -H 'Authorization: Bearer <authToken>' 127.0.0.1:8080/vsan/metrics

e.g.:

    $ curl -H 'Authorization: Bearer d64c4e1d-51b1-461f-8304-f0c7efd6b55c' 127.0.0.1:8080/vsan/metrics
    ...
    vmware_esx_world_usedtime_seconds_total{subsystem="DOM",host_uuid="5dbbb2a5-3a52-5a9d-12cb-02007459e1d0",world_id="1000082635",role="Owner",hostname="10.78.84.238",vsan_cluster_uuid="52f0245d-c960-c455-18be-ef76434ba696"} 0.000057
    ...
    vmware_esx_world_usedtime_seconds_total{subsystem="DOM",host_uuid="5dbbb2a5-427f-5b9f-6052-020074721b49",world_id="1000082574",role="Client",hostname="10.78.84.171",vsan_cluster_uuid="52f0245d-c960-c455-18be-ef76434ba696"} 0.000064
    ...

### Retrieve metrics for one host
The host id can be seen from service discovery.

    $ curl -H 'Authorization: Bearer <authToken>' 127.0.0.1:8080/vsan/metrics/<hostId>

e.g.:

    $ curl -H 'Authorization: Bearer d64c4e1d-51b1-461f-8304-f0c7efd6b55c' 127.0.0.1:8080/vsan/metrics/host-16
    ...
    vmware_esx_pnic_pkt_total{host_uuid="5dbbb2a5-427f-5b9f-6052-020074721b49",vmnic="vmnic0",io_type="rx",hostname="10.78.84.171",vsan_cluster_uuid="52f0245d-c960-c455-18be-ef76434ba696"} 237431950.000000
    ...

## Environment Variables
| Variables | Default Value | Notes |
|:---:|:---:|---|
| VCENTER      | (not set) | The vCenter IP address         |
| VCPORT       |    443    | The vCenter Port               |
| VCUSER       | (not set) | The username for vCenter login |
| VCPASSWORD   | (not set) | The password for vCenter login |
| CLUSTERNAME  | (not set) | The cluster name in vCenter    |
| BEARER_TOKEN | (not set) | The bearer token used for authorization, will be generated automatically if not set |

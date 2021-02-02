## vsan-prometheus-operator

The vsan-prometheus-operator container uses vCenter service discovery API to create
Kubernetes `Service` and `Endpoint` objects to reference the ESX hosts and their
vSAN Prometheus /metrics API endpoint. These should go with a `ServiceMonitor`
that matches these `Services` by labels, so that Prometheus Operator picks them up
based on service label matching. End-2-end this automates Prometheus picking up
vSAN metrics.

* Python script for auto-updating Kubernetes service endpoints and service monitor based on vCenter service discovery API.
* One vSAN cluster maps to one Kubernetes service and endpoint, while the hosts in the cluster are Kubernetes endpoint subsets addresses.
* The commands for creating the container images.
```
cd vsan-prometheus-operator
docker build -t vsan-prometheus-operator .
```

## ServiceMonitor

The following is an example of a `ServiceMonitor` object which would pick up
the metrics from vSAN based on the `Service` and `Endpoint` objects created
by the `vsan-prometheus-operator`. Note the selector labels which need to
match the label that `vsan-prometheus-operator` is configured to put on the
`Service` objects it creates.
```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: vsan-monitoring
  labels:
    app: vsan-monitoring
spec:
  selector:
    matchLabels:
      app: vsan-monitoring
  endpoints:
  - path: /vsanmetrics
    scheme: https
    honorLabels: true
    bearerTokenFile: /etc/prometheus/secrets/bearer-token-secret/bearer-token
    relabelings:
    - sourceLabels:
      - __metrics_path__
      targetLabel: metrics_path
    tlsConfig:
      insecureSkipVerify: true
```


### Environment Variables in the container
 |  Variables |  Default Value | Notes  | 
|:---:|:---:|:---:|
|  VCENTER | environment variables  | The vCenter IP address  |
|  SCHEME | https  |  The protocol for reaching Prometheus endpoints |
|  Mode | proxy  |  Proxy mode is about to query data from vCenter,  direct mode is about querying data from vSAN hosts. |
|  LABEL | vsan-monitoring  | The Kubernetes service or endpoint label, which can be picked up by Prometheus Operator |
|  LABEL_KEY | app  | The Kubernetes service or endpoint label key, which can be picked up by Prometheus Operator |
|  NAMESPACE | default  | The namespace is updated based on current active namespace |
|  INTERVAL_SEC | 300 (seconds)  | The interval for updating server list  |
|  BEARER_TOKEN_FILE | /etc/secret-volume/bearer-token  | The bearer token secret is mapped into volume  |
|  DISCOVERY_ENDPOINT | vsan/metrics/serviceDiscovery  | The vCenter service discovery endpoint  |
|  CA_CERT_FILE | /etc/secret-volume/ca_cert.pem  | The path for reading CA certificate file  |
|  SECRET_NAME | bearer-token-secret  | The secret name containers bearer token  |
|  BEARER_TOKEN_PROMETHEUS | "/etc/prometheus/secrets/%s/bearer-token" % SECRET_NAME  | The bearer token path in Prometheus server  |
|  PROMETHEUS_CA_CERT_PATH | "/etc/prometheus/secrets/%s/ca_cert.pem" % SECRET_NAME  | The CA certificate file path in Prometheus server  |
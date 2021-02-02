# Getting started with vSAN benchmark runs

- [Prerequisites](#Prerequisites)
- [Deploying vSAN Prometheus with Thanos](#Deploying)
  * [Thanos Sidecar (vSAN70)](#thanos_sidecar)
  * [Prometheus Operator (vSAN70)](#operator)
- [Thanos viewer and Grafana](#viewer)

<a name="Prerequisites"></a>
## Prerequisites
It has the same prerequisites with Docker, Kubernetes, and Helm in this repo.
Please go to prerequisites section of [getting started](./getting-started.md) document.
Before diving into details, please make sure those following preparation steps are done.

Step 1: Please clone this repo and go to the repo folder for all following commands.
```
git clone https://gitlab.eng.vmware.com/cdickmann/vsan-prometheus.git
cd vsan-prometheus 
```

Step 2: Create Kubernetes namespace and make it default for following kubectl commands if it is necessary.
```
kubectl create namespace vsan-prometheus
kubectl config set-context --current --namespace=vsan-prometheus
```

<a name="Deploying"></a>
## Deploying vSAN Prometheus with Thanos 
We provide two options to monitor vSAN benchmark ephemeral runs using Thanos sidecar for uploading Prometeheus snapshot data to Object Store.  
* Option 1: Thanos Sidecar
* Option 2: Prometheus Operator

To cooperate with Prometheus & Prometheus Operator Helm chart, we build an add-on integration named `vsan-prometheus-thanos-config` Helm chart.
It simply packs Thanos Object Store config yaml and Thanos [oneoff script yaml](./benchmark-ephemeral.md).
You can learn more about all possible supported [Thanos Object Store types and config yaml](https://github.com/thanos-io/thanos/blob/master/docs/storage.md).

In this example, we pass a S3 object config yaml:
```
helm install thanos-config helm/vsan-prometheus-thanos-config --set-file configYaml=yaml/vsan-thanos-s3-config.yaml
```
After the command, it generates `thanos-config-config-secret` and `thanos-config-util-configmap` for following usages.

<a name="thanos_sidecar"></a>
### Thanos Sidecar (vSAN70)
Step 1: Create secret for bearer token and vCenter. The secret will mount as volume in Prometheus for scraping vSAN metrics.
```
kubectl create secret generic bearer-token-secret --from-literal=bearer-token=<token> --from-literal=vcenter=<vCenter>
```

Step 2: Deploy Prometheus Helm chart with the customized value.yaml for passing Thanos config and launching Thanos Sidecar. 
```
helm install -f yaml/prometheus-thanos-value.yaml prometheus prometheus-community/prometheus
```
**Note**: In the `prometheus-thanos-value.yaml` you can update the Thanos Secret and Configmap names by matching the generated names.  

Step 3: After vSAN benchmark run is finished, trigger thanos-oneoff script for Prometheus snapshot generating and uploading:
```
kubectl exec -it deployment/prometheus-server --container thanos-sidecar /bin/sh /thanos-util/thanos-oneoff.sh
```

Step 4: Delete Helm charts if they are not necessary:
```
helm delete thanos-config prometheus
```

<a name="operator"></a>
### Prometheus Operator (vSAN70)
Prometheus Operator Helm chart supports Thanos sideCar.
But the feature is experimental, not officially supported.
So our example commands do not guarantee newer release of Prometheus Operator.
The following commands are bsed on current Helm chart Prometheus Operator with version `8.12.3`.

Step 1: Deploy vSAN Prometheus operator service discovery Helm chart:
```
helm install vsan-operator helm/vsan-prometheus-operator-service-discovery --set vcenter=xxx --set bearerToken=xxx
```

Step 2: Deploy Prometheus Operator Helm chart based on customized value.yaml for Thanos setup.
```
helm install -f yaml/prometheus-operator-thanos-value.yaml vsan-monitor prometheus-community/kube-prometheus-stack
```
**Note**: In the `prometheus-operator-thanos-value.yaml` you can update the Thanos Secret and Configmap names by matching the generated names.  

Step 3: After vSAN benchmark run is finished, trigger oneoff script for Prometheus snapshot generating and uploading:
```
kubectl exec -it sts/prometheus-vsan-monitor-kube-promethe-prometheus --container thanos-sidecar /bin/sh /thanos-util/thanos-oneoff.sh
```
**Note**: The StatefulSet name `prometheus-vsan-monitor-kube-promethe-prometheus` is needed to change for different names of Prometheus Operator instance.

Step 4: Delete Helm charts if they are necessary:
```
helm delete thanos-config vsan-operator vsan-monitor
```

<a name="viewer"></a>
## Thanos viewer and Grafana
We can retrieve and visualize Prometheus snapshot from Object Store anytime, any other Kubernetes cluster.
Two Helm charts are provided to achieve the goal:
1) Helm chart `vsan-prometheus-thanos-config` packs Thanos config yaml to Secret and Thanos oneoff script yaml to Configmap.  
2) Helm chart `vsan-prometheus-thanos-viewer` deploys Thanos Query and Thanos Store for retrieving and querying Prometheus snapshot from Object Store.

Step 1: Install Helm chart `vsan-prometheus-thanos-config` by passing Object Store config yaml:
```
helm install thanos-config helm/vsan-prometheus-thanos-config --set-file configYaml=yaml/vsan-thanos-s3-config.yaml
```

Step 2: Deploy Helm chart `vsan-prometheus-thanos-viewer` with Object Store config secret:
```
helm install thanos-viewer helm/vsan-prometheus-thano-viewer --set objectStoreConfigSecret=thanos-config-config-secret
```

Step 3: Create Grafana dashboards configmap and label it, so that the dashboards are auto imported. 
```
kubectl create configmap grafana-dashboards --from-file=grafana-dashboard/dashboards
kubectl label configmap grafana-dashboards grafana_dashboard=1
```

Step 4: Deploy Helm chart Grafana by setup data source with Thanos Service:
```
export THANOS_SERVICE=$(kubectl get svc -l "app=thanos" -o jsonpath="http://{.items[0].metadata.name}:{.items[0].spec.ports[0].port}")
helm install -f yaml/grafana-value.yaml --set datasources."datasources\.yaml".datasources[0].url=${THANOS_SERVICE} grafana grafana/grafana
```
Step 5: Delete Helm charts if they are not necessary:
```
helm delete thanos-config thanos-viewer grafana
```

# Getting started
- [Overview](#Overview)
- [Background](#Background)
- [Prerequisites](#Prerequisites)
- [Supportability Metrics](#Supportability)
- [Deploying](#Deploying)
  * [vSAN 7.0](#vsan7.0)
    + [Option 1: Sidercar container](#option1_vsan70)
    + [Option 2: Prometheus Operator](#option2_vsan70)
  * [vSAN Pre 7.0](#vsanpre7.0)
    + [Option 1: Sidercar container](#option1_prevsan70)
    + [Option 2: Prometheus Operator](#option2_prevsan70)
- [Accessing](#accessing)
- [Dashboards](#dashboards)
- [Ephemeral deployments for vSAN benchmark](#ephemeral)
- [Development](#ephemeral)

<a name="Overview"></a>
# Overview

vSAN Prometheus provides essential container images for monitoring vSAN infrastructure using Prometheus & Grafana.

This page provides examples for deploying vSAN monitoring solutings using Prometheus & Grafana. 
Our examples may not be ideal for (existing) production environments, but should highlight how our service discovery 
(via sidecar or Prometheus Operator) can be integrated into any Prometheus environment. 


The highlights for deploying our sample vSAN monitoring solutions:
* A full end to end vSAN monitoring solution based on  Prometheus & Grafana.
* Using Helm charts for deploying our solution.
* The deployment solution considers vSAN 7.0 and vSAN pre 7.0 versions.
* Sample [Grafana dashboards]((../grafana-dashboard/README.md)) are provided in the deployment.
 
<a name="Background"></a>
# Background
In this repo, we highlight Prometheus and Grafana for vSAN metrics monitoring.
The [background](./background.md) document presents why Prometheus and Grafana are good for vSAN metrics monitoring.

 
<a name="Prerequisites"></a>
# Prerequisites
vSAN Prometheus solution runs on Docker and Kubernetes environment. 
We test the Docker `v18.09.9` and Kubernetes `v1.15.4` for running our deployment solution.

We suggest you can use the latest version of Docker and Kubernetes.
Since our test cannot cover any newer version of Docker and Kubernetes, please file an issue about it.
We also keep updating this project for supporting new release of Docker and Kubernetes.

## Helm
Our solution is based on Helm 3. We suggest to use the stable helm repository.

Install Helm 3 using Homebrew in Mac and add stable repository.
```
brew install helm
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo add stable https://charts.helm.sh/stable
helm repo update
```

<a name="Supportability"></a>
# Supportability Metrics
Two major kinds of deployments are provided based on different vSAN versions.
  * From vSAN 7.0, each vSAN host provides vSAN Prometheus endpoints, so the deployed Prometheus instance can easily scrape vSAN Perf data through the endpoints.
  * To support the older vSAN versions pre vSAN 7.0, this repo provides vsan-prometheus-exporter container to translate vSAN Perf data in Prometheus format.

For each deployment, this repo also provides two options either SideCar or Prometheus Operator way. You can follow either option to intergate existing Prometheus monitoring solution.

Some of vSAN Perf metrics are not avaliable for old vSAN versions, which makes the lacking of data in Grafana dashboards.

The following supportability table summarize those difference between vSAN versions 

 |  vSAN Version |  Deployment Solutions | Dashboard Graph Unavaliable  | 
|:---:|:---:|:---:|
|  vSAN 6.5U3 | vSAN Prometheus Exporter  | vSAN CPU - LLOG, Network, CMMDS; DOM DG, vSAN Layers - DOM CompMgr DG  |
|  vSAN 6.7U3 | vSAN Prometheus Exporter  |  None |
|  vSAN 7.0 | vSAN Prometheus Exporter; Built-In Endpoint   | None |
|  vSAN 7.0U1 | vSAN Prometheus Exporter; Built-In Endpoint  | None  |


<a name="Deploying"></a>
# Deploying
In vSAN 7.0, the vSAN Prometheus endpoint and metrics authorization are introduced in the product,
thus the monitoring solutions have difference between vSAN 7.0 and vSAN pre 7.0.

Step 0.1: Please clone this repo and go to the repo folder for all following commands.
```
git clone https://github.com/vmware/vsan-integration-for-prometheus.git
cd vsan-prometheus 
```

Step 0.2: Create Kubernetes namespace and make it default for following kubectl commands
```
kubectl create namespace vsan-prometheus
kubectl config set-context --current --namespace=vsan-prometheus
```

<a name="vsan7.0"></a>
## vSAN 7.0

Two options are provided for monitoring vSAN 7.0: sidecar container solution and Prometheus Operator. Before applying
either option, the metrics authorization token setup and Grafana dashboard configMap should be prepared.

Step 1: vSphere admin requests metrics authorization token for a specific vSAN cluster.
```
docker run -it vmware/vsan-prometheus-setup:v20210225 --host <vCenter> --username <userName> --cluster <clustername>
```
This is a sample output from above command.
Learn more vsan-prometheus-setup container usage, please go to its [readme](../vsan-prometheus-setup/README.md).
```
Enter password for host 10.160.29.255 and username administrator@vsphere.local:
Successfully connected to vCenter!
Successfully generate a new token:
47718bb7-e368-4c01-beed-943cce
```

Step 2: Create configmap for Grafana dashboards. 
```
kubectl create configmap grafana-dashboards --from-file=grafana-dashboard/dashboards
```

Step 3: It is necessary to label configMaps so that the dashboards are auto imported.
```
kubectl label configmap grafana-dashboards grafana_dashboard=1
```

<a name="option1_vsan70"></a>
### Option 1: Sidercar container
In `prometheus-value.yaml`, we customize the default Prometheus Helm chart for adding a sideCar container named `vsan-prometheus-servicediscovery`.
This container regularly updates Prometheus server list by querying vSAN service discovery endpoint.

In `grafana-value.yaml`, we customize the default Grafana Helm chart for reaching the Prometheus server, and adding our vSAN dashboards.

**Note**: 
* The default Prometheus Helm chart enables metrics for Kubernates cluster and Prometheus,
such as kubernetes-apiservers, kubernetes-nodes, kubernetes-pods, etc.
* The default Grafana Helm chart does not provide any default dashboards.
In our customized file, we add basic Grafana charts for Kubernetes cluster metrics. 

Step 1: Create secret of bearer token and vCenter for passing them to Prometheus.
```
kubectl create secret generic bearer-token-secret --from-literal=bearer-token=<token> --from-literal=vcenter=<vCenter>
```
**Note**: 
* The bearer token secret is used for passing environment variables for vsan-prometheus-servicediscovery container.
More details can be found in this container [readme](../vsan-prometheus-servicediscovery/README.md).

Step 2: Install Prometheus:
```
helm install -f yaml/prometheus-value.yaml prometheus prometheus-community/prometheus
```

Step 3: Install Grafana:
```
helm install -f yaml/grafana-value.yaml grafana grafana/grafana
```

Example commands are provided with a [demo video](../example-demo-videos/vsan70-sidecar.mp4).
```
kubectl create secret generic bearer-token-secret --from-literal=bearer-token=<token> --from-literal=vcenter=<vCenter>
kubectl create configmap grafana-dashboards --from-file=grafana-dashboard/dashboards
kubectl label configmap grafana-dashboards grafana_dashboard=1
helm install -f yaml/prometheus-value.yaml prometheus prometheus-community/prometheus
helm install -f yaml/grafana-value.yaml grafana grafana/grafana
```
**Note**: The example run skips vCenter server security verification.
To enable vSAN Prometheus security verification, please go to vsan-prometheus-servicediscovery container [readme](../vsan-prometheus-servicediscovery/README.md).

Uninstall Helm charts or reinstall the charts 
```
helm delete prometheus grafana
```

<a name="option2_vsan70"></a>
### Option 2: Prometheus Operator
In addition to Prometheus operator helm chart, we build an add-on integration for having our own helm chart named vSAN Prometheus operator service discovery
The helm chart wraps vsan-prometheus-operator container, which generates serviceMonitor for tracking vSAN Prometheus endpoints.
Get more details from this container [readme](../vsan-prometheus-operator/README.md).


Step 1: Install helm chart vSAN Prometheus service discovery:
```
helm install vsan-operator helm/vsan-prometheus-operator-service-discovery --set vcenter=xxx --set bearerToken=xxx
``` 

Step 2: Install helm chart Prometheus Operator:
```
helm install -f yaml/prometheus-operator-value.yaml vsan-monitor prometheus-community/kube-prometheus-stack
```

Example commands are provided with a [demo video](../example-demo-videos/vsan70-operator.mp4).
```
kubectl create configmap grafana-dashboards --from-file=grafana-dashboard/dashboards
kubectl label configmap grafana-dashboards grafana_dashboard=1
helm install vsan-operator helm/vsan-prometheus-operator-service-discovery --set vcenter=xxx --set bearerToken=xxx
helm install -f yaml/prometheus-operator-value.yaml vsan-monitor prometheus-community/kube-prometheus-stack
```

**Note**:
* The helm chart `vsan-prometheus-operator-service-discovery` generates auth secret and deploys `vsan-prometheus-operator` container.
  And the  `vsan-prometheus-operator` container generates ServiceMonitor object for monitoring vSAN endpoints. 
* Since [serviceMonitor](https://github.com/coreos/prometheus-operator/blob/master/Documentation/design.md#servicemonitor) monitors 
  related Kubernetes Service and Endpoint, so Prometheus Operator discovers the Endpoint objects and configures Prometheus to monitor them.
* If security certificate works for IP address in the Endpoint object, please follow helm chart [value.yaml](../helm/vsan-prometheus-operator-service-discovery/values.yaml) to pass certificate file.
*  Please match the secret and serviceMonitor name in `prometheus-operator-value.yaml` if you change the default values.

Uninstall Helm charts or reinstall the charts 
```
helm delete vsan-operator vsan-monitor
```
<a name="vsanpre7.0"></a>
## vSAN Pre 7.0
We create our own helm chart for exporting vSAN pre 7.0 Prometheus data.
The helm chart deploys vsan-prometheus-exporter container.
It creates a Kubernetes service for accessing the container.
Get more details from this container [readme](../vsan-prometheus-exporter/README.md).

The following steps are to prepare Kubernetes resources for monitoring solution deployment

Step 1: Generate a bearer token since vSAN pre 7.0 does not support it.
```
export BEARER_TOKEN=$(uuidgen)
``` 
Step 2: Create configmap for Grafana dashboards.
```
kubectl create configmap grafana-dashboards --from-file=grafana-dashboard/dashboards
```

Step 3: It is necessary to label configMaps so that the dashboards are auto imported.
```
kubectl label configmap grafana-dashboards grafana_dashboard=1
```

<a name="option1_prevsan70"></a>
### Option 1: Sidercar container

Step 1: Install helm chart vSAN Prometheus exporter:
```
helm install vsan-exporter helm/vsan-prometheus-exporter --set vcenter=xxx --set username='xxx' --set passwd='xxx' --set bearerToken=$BEARER_TOKEN
```

Step 2: Install helm chart Prometheus:
```
helm install -f yaml/prometheus-value.yaml prometheus prometheus-community/prometheus
```

Step 3 Install helm chart Grafana:
```
helm install -f yaml/grafana-value.yaml grafana grafana/grafana
```

Example commands are provided with a [demo video](../example-demo-videos/vsan-pre70-sidecar.mp4).
```
export BEARER_TOKEN=$(uuidgen)
kubectl create configmap grafana-dashboards --from-file=grafana-dashboard/dashboards
kubectl label configmap grafana-dashboards grafana_dashboard=1
helm install vsan-exporter helm/vsan-prometheus-exporter --set vcenter=xxx --set username='xxx' --set passwd='xxx' --set bearerToken=$BEARER_TOKEN
helm install -f yaml/prometheus-value.yaml prometheus prometheus-community/prometheus
helm install -f yaml/grafana-value.yaml grafana grafana/grafana
```

Uninstall Helm charts or reinstall the charts 
```
helm delete prometheus grafana
```

<a name="option2_prevsan70"></a>
### Option 2: Prometheus Operator

Step 1: Install helm chart vSAN Prometheus exporter:
```
helm install vsan-exporter helm/vsan-prometheus-exporter --set vcenter=xxx --set username='xxx' --set passwd='xxx' --set bearerToken=$BEARER_TOKEN
```

Step 2: Install helm chart Prometheus Operator:
```
helm install -f yaml/prometheus-operator-value.yaml vsan-monitor prometheus-community/kube-prometheus-stack
```

Step 3: Install helm chart vSAN operator service discovery:

* Step 3-1: Get the vcenter service name
```
export VC_SERVICE=$(kubectl get svc -l "app=vsan-prometheus-exporter" -o jsonpath="{.items[0].metadata.name}:{.items[0].spec.ports[0].port}")
```
* Step 3-2: Install helm chart vSAN operator service discovery
```
helm install vsan-operator helm/vsan-prometheus-operator-service-discovery --set vcenter=$VC_SERVICE  --set bearerToken=$BEARER_TOKEN --set scheme=http
```

Example commands are provided with a [demo video](../example-demo-videos/vsan-pre70-operator.mp4).
```
export BEARER_TOKEN=$(uuidgen)
kubectl create configmap grafana-dashboards --from-file=grafana-dashboard/dashboards
kubectl label configmap grafana-dashboards grafana_dashboard=1
helm install vsan-exporter helm/vsan-prometheus-exporter --set vcenter=xxx --set username='xxx' --set passwd='xxx' --set bearerToken=$BEARER_TOKEN
helm install -f yaml/prometheus-operator-value.yaml vsan-monitor prometheus-community/kube-prometheus-stack
export VC_SERVICE=$(kubectl get svc -l "app=vsan-prometheus-exporter" -o jsonpath="{.items[0].metadata.name}:{.items[0].spec.ports[0].port}")
helm install vsan-operator helm/vsan-prometheus-operator-service-discovery --set vcenter=$VC_SERVICE --set bearerToken=$BEARER_TOKEN --set scheme=http
```

Uninstall Helm charts or reinstall the charts 
```
helm delete vsan-exporter vsan-monitor vsan-operator
```

<a name="accessing"></a>
# Accessing
We suggest to install VMware [octant](https://github.com/vmware-tanzu/octant), which is an open source tool to understand applications run on a Kubernetes cluster.
Using Octant, you can explore Prometheus and Grafana container. By container port forwarding, it gives you local access URLs.

## Prometheus & Grafana Url

<!--- using helm chart, so comment prometheus-70.yaml  ---> 
### NodePort for exposing a static port
<!--- In the `prometheus-70.yaml` file, we declare the service of Prometheus and Grafana as NodePort, which exposes a static port
for accessing from outside.
If you use your own Prometheus and Grafana service, you can apply kubectl port-forward for having a static port.
--->

To get the Prometheus & Grafana access url, you can describe the Kubernetes nodes for having the master node external IP.
```
kubectl get node -o wide
```

If the master node external IP is none, you can try your machine IP address, or hostname or using `localhost` as url.

#### Option 1: Sidercar container
Grafana
* Get the Grafana URL to visit by running the command:
  ```
  kubectl port-forward svc/grafana  30000:80
  ```
* URL: http://url:30000/ 
* UserName / Password : `admin / grafana`

Prometheus
* Get the Prometheus server URL by running these commands in the same shell:
  ```
  kubectl port-forward svc/prometheus-server 30001:80
  ```
 * URL: http://url:30001

#### Option 2: Prometheus Operator
Grafana
* Instead of using octant, you can apply the command line for port forwarding
    ```
    kubectl port-forward svc/vsan-monitor-grafana 30000:80
    ```
* URL: http://url:30000/ 
* UserName / Password : `admin / grafana`

Prometheus
* Instead of using octant, you can apply the command line for port forwarding
    ```
    kubectl port-forward svc/vsan-monitor-kube-promethe-prometheus 30001:9090
    ```
* URL: http://url:30001


## Grafana dashboard access
Once you login Grafana, you can access the predefined dashboards by clicking the dashboard menu, then choosing Manage choice.
Or you append the dashboards after the Grafana URL, e.g. http://localhost:30000/dashboards
 
Here is a [Grafana dashboards list](../screenshots/grafana-dashboards-list.png) screenshot.


## Uninstalling
To remove deployed vSAN Prometheus, you can use the following commands.

### Uninstall Helm charts

#### vSAN 7.0 Uninstall

Sidercar containers
```
helm delete prometheus grafana
```

Prometheus Operator
```
helm delete vsan-operator vsan-monitor
```

#### vSAN pre 7.0 Uninstall
Sidercar containers
```
helm delete prometheus grafana vsan-exporter
```

Prometheus Operator
```
helm delete vsan-exporter vsan-monitor vsan-operator
```

### Reset Kubernetes namespace
```
kubectl delete secret bearer-token-secret 
kubectl delete configmap grafana-dashboards
kubectl config set-context --current --namespace=default
kubectl delete namespace vsan-prometheus
```

<a name="dashboards"></a>
# Dashboards
We provide pre-defined Grafana dashboards for monitoring the key metrics of vSAN 
instead of learning vSAN Prometheus metrics details. The document of [Grafana dashboard](../grafana-dashboard/README.md)
provides how to organize and generate Grafana dashboards.

<a name="ephemeral"></a>
# Ephemeral deployments for vSAN benchmark
We use Thanos to upload Prometheus snapshots to S3 storage. The [benchmark ephemeral document](./benchmark-ephemeral.md)
provides the idea, the design and implementation.

Please go to [Thanos getting started](./benchmark-ephemeral-started.md) for having a try!

<a name="development"></a>
# Development
We provide technical details in [development](./development.md) document.
You can build your own container images or run testing codes based on your requirements.

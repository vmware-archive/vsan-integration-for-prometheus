# Development
<a name="Overview"></a>
# Overview

This document provides how to build your own vSAN Prometheus container images based on your own need, 
or contribute in this repo for rebuilding container images and running tests. 

<a name="Building"></a>
# Container Images Building
In this repo, four container images are used for launching vSAN monitoring using Prometheus and Grafana.
The following table summarizes those containers. 

|  Container Name |  Description | Document  |
|:---:|:---|:---:|
|  vsan-prometheus-setup | Generate vSAN cluster Prometheus bearer token for authentication    | [ReadMe](../vsan-prometheus-setup/README.md)   |
|  vsan-prometheus-servicediscovery |  Prometheus service discovery sidecar container  | [ReadMe](../vsan-prometheus-servicediscovery/README.md)   |
|  vsan-prometheus-operator |   Generate service endpoint for Prometheus Operator usage   | [ReadMe](../vsan-prometheus-operator/README.md)   |
|  vsan-prometheus-exporter | Support previous vSAN versions (pre 7.0) without Prometheus in-built   | [ReadMe](../vsan-prometheus-exporter/README.md)   |

To rebuild all the images, you can run the command, and then update YAML files with the local images.
```
TAG=<yourTag> ./scripts/docker-build.sh
```

<a name="Helm Charts"></a>
# Helm charts
In this repo, four [helm charts](../helm) are provided for orchestrating vSAN Prometheus containers with other Prometheus & Grafana open source resources.
Please update each chart default values for different requirements.

|  Helm chart Name |  Description
|:---:|:---|
|  vsan-prometheus-exporter | Orchestrate vsan-prometheus-exporter container with vSphere secret generation |
|  vsan-prometheus-operator-service-discovery |  Orchestrate vsan-prometheus-operator container with vSphere secret generation |
|  vsan-prometheus-thano-viewer |   Orchestrate thanos container and its configuration |
|  vsan-prometheus-thanos-config | Orchestrate S3 yamls and scripts for Prometheus snapshots |

<a name="Testing"></a>
# Testing

The unit tests are provided based on Python unittest framework.
We support the basic unit test in the CICD pipeline. And end-to-end test needs live vSphere & vSAN environment.

Please go to the tests folder for more details.

We use the Github Actions as our CICD pipeline running envrionment.



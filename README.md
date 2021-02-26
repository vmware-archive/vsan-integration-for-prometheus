[<img src="https://s-a.github.io/license/img/bsd-2-clause.svg" />](https://github.com/vmware/vsan-integration-for-prometheus/blob/master/LICENSE)

## Overview

Lots of new features come in vSphere & vSAN 7.0 release:
* ESXi natively exposes a Prometheus /vsanmetrics API endpoint for vSAN metrics.
* vCenter can act as a network proxy for each ESXi host /vsanmetrics API endpoint.
* High frequency scrape intervals (e.g. 15s) are supported.
* If used with VMware Kubernetes CSI driver, per-volume metrics have rich Kubernetes labels, e.g. PVC name and namespace.

The vSAN Prometheus project aims to make it easier to consume this native Prometheus support, as well as to provide a solution for pre-7.0 vSphere & vSAN.

## Features
This project highlights the following features:
1. Service discovery plugins for both standalone Prometheus and Prometheus Operator
2. Pre-defined Grafana dashboards for monitoring the key metrics of vSAN performance.
1. Getting started guides with example Prometheus/Grafana deployments for vSphere & vSAN 7.0 and pre vSphere & vSAN 7.0 versions.
4. Using [Thanos](https://github.com/thanos-io/thanos) for uploading Prometheus snapshot to Object Store for vSAN benchmark monitoring.    

## Getting Started
Getting started with vSAN Prometheus is simple, and takes a few minutes.
See how it is done in the [Getting started](./docs/getting-started.md) document.

## Contributing
Thanks for taking the time to join our community and start contributing! We welcome pull requests.
Feel free to dig through the issues and jump in.
* Before contributing, please get familiar with our
[Code of Conduct](CODE_OF_CONDUCT.md).
* Check out our [Contributor Guide](./docs/development.md) for information
about setting up your development environment and our contribution workflow.
* Check out [Open Issues](https://github.com/vmware/vsan-integration-for-prometheus/issues).

## License
vSAN Prometheus is licensed under [BSD 2](./LICENSE)
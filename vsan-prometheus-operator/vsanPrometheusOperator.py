#!/usr/bin/env python3
#
# Copyright 2020-2021 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause
#
# This script launchs a deamon for auto updating the Kubernetes services and endpoints,
# which are used by the Prometheus operator service discovery

import json
import time
import hashlib
import logging
import sys
import os
import six
from kubernetes import client, config
import requests
import signal
from functools import partial
import ipaddress
import socket

LABEL = os.environ.get('LABEL', 'vsan-monitoring') # the label will be picked up by Prometheus operator
LABEL_KEY = os.environ.get('LABEL_KEY', 'app')
SERVICEMONITOR_NAME = os.environ.get('SERVICEMONITOR_NAME', LABEL)
NAMESPACE = open("/var/run/secrets/kubernetes.io/serviceaccount/namespace").read()
INTERVAL_SEC = int(os.environ.get('INTERVAL_SEC', 300))# default value is 5 minutes
DISCOVERY_ENDPOINT = 'vsan/metrics/serviceDiscovery' # vCenter service discovery endpoint
BEARER_TOKEN_FILE = '/etc/secret-volume/bearer-token' # vCenter token path
VCENTER = os.environ.get('VCENTER')
SCHEME = os.environ.get('SCHEME', 'https')
MODE = os.environ.get('MODE', 'proxy')
if MODE != 'proxy' and MODE != 'direct':
   print("Illegal MODE %s, defaulting to proxy" % MODE)
   MODE = 'proxy'
if MODE == 'direct':
   DISCOVERY_ENDPOINT = '%s?mode=direct' % DISCOVERY_ENDPOINT

SERVICEMONITOR_GROUP = 'monitoring.coreos.com'
SERVICEMONITOR_VERSION = 'v1'
SERVICEMONITOR_PURAL = 'servicemonitors'
SERVICEMONITOR_KIND = 'ServiceMonitor'
SECRET_NAME = os.environ.get('SECRET_NAME', 'bearer-token-secret')
BEARER_TOKEN_PROMETHEUS = "/etc/prometheus/secrets/%s/bearer-token" % SECRET_NAME
CA_CERT_FILE = '/etc/secret-volume/ca_cert.pem' # vcenter ca certification file
PROMETHEUS_CA_CERT_PATH = "/etc/prometheus/secrets/%s/ca_cert.pem" % SECRET_NAME

# format the logging message
def getLog():
   handler = logging.StreamHandler(sys.stdout)
   handler.setLevel(logging.INFO)
   handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s [%(name)s] %(message)s'))

   root = logging.getLogger()
   root.setLevel(logging.INFO)
   root.addHandler(handler)
   return root

# setup log as global
log = getLog()

# read the bearer token file
def getBearToken():
   with open(BEARER_TOKEN_FILE, 'r') as f:
      return f.read()

# obtain the FQDN from ipAddress
def getFQDNfromIpAddress(ipAddress):
   try:
      ipaddress.IPv4Address(ipAddress)
      hostName = list(socket.gethostbyaddr(ipAddress))[0]
      return hostName
   except:
      # not valid ip address, just return
      return ipAddress

# get hostname if ssl cert is associated with it
def getHostAssociateSSLIfNeed(host):
   ca_cert_existed = os.path.exists(CA_CERT_FILE)
   if not (ca_cert_existed and SCHEME == 'https'):
      return host

   try:
      requests.get(host, verify=CA_CERT_FILE)
      return host
   except:
      return getFQDNfromIpAddress(host)

# obtaining the host exporters list through vCenter service discovery endpoint
def getProviderFromServiceDiscovery(bearer_token):
   hostAddress = getHostAssociateSSLIfNeed(VCENTER)
   discoveryUrl = "%s://%s/%s" % (SCHEME, hostAddress, DISCOVERY_ENDPOINT)
   log.info(discoveryUrl)
   bearer_token = 'Bearer %s' % bearer_token
   headers = {"Authorization": bearer_token}

   ca_cert_existed = os.path.exists(CA_CERT_FILE)
   if SCHEME == 'https' and ca_cert_existed:
      res = requests.get(discoveryUrl, verify=CA_CERT_FILE, headers=headers)
   else:
      res = requests.get(discoveryUrl, verify=False, headers=headers)
   if res.status_code == 404:
      raise Exception("vCenter Prometheus service discovery endpoint is unavailable!")

   providers = res.text
   log.info(providers)
   if not isinstance(providers, str):
      providers = providers.decode("UTF-8")
   if not providers:
      raise Exception("vCenter Prometheus service discovery suffers issues!")
   return providers

# get servceMonitor endPoints for different metrics path
# @clusterDict: the dict generated by vCenter service discovery result
def getServiceMonitorEndPoints(clusterDict):
   endPoints = []
   for cluster, props in six.iteritems(clusterDict):
      metrics_paths = list(set(props['metrics_path']))
      for metrics_path in metrics_paths:
         endPoint = {
            'bearerTokenFile': BEARER_TOKEN_PROMETHEUS,
            'honorLabels': True,
            'path': metrics_path,
            'relabelings': [{'sourceLabels': ['__metrics_path__'], 'targetLabel': 'metrics_path'}],
            'scheme': SCHEME,
            'tlsConfig': {'insecureSkipVerify': True}
         }
         if os.path.exists(CA_CERT_FILE):
            endPoint['tlsConfig']['caFile'] = PROMETHEUS_CA_CERT_PATH
            endPoint['tlsConfig']['insecureSkipVerify'] = False
         endPoints.append(endPoint)
   return endPoints

# create serviceMonitor k8s resource
# @clusterDict: the dict generated by vCenter service discovery result
def createServiceMonitor(clusterDict):
   serviceMonitor = {
      "apiVersion": "%s/%s" %(SERVICEMONITOR_GROUP, SERVICEMONITOR_VERSION),
      "kind": SERVICEMONITOR_KIND,
      "metadata": {
         "labels": {LABEL_KEY: LABEL},
         "name": SERVICEMONITOR_NAME,
         "namespace": NAMESPACE
      },
      "spec": {
         "endpoints": getServiceMonitorEndPoints(clusterDict),
         "selector": {"matchLabels": {LABEL_KEY: LABEL}}
      }
   }

   customApi = client.CustomObjectsApi()
   customApi.create_namespaced_custom_object(
      group=SERVICEMONITOR_GROUP,
      version=SERVICEMONITOR_VERSION,
      namespace=NAMESPACE,
      plural=SERVICEMONITOR_PURAL,
      body=serviceMonitor
   )
   log.info("Create serviceMonitor %s" % str(serviceMonitor))

# update serviceMonitor k8s resource
# @clusterDict: the dict generated by vCenter service discovery result
def updateServiceMonitor(serviceMonitor, clusterDict):
   customApi = client.CustomObjectsApi()
   serviceMonitor['spec']['endpoints'] = getServiceMonitorEndPoints(clusterDict)
   customApi.patch_namespaced_custom_object(
      group=SERVICEMONITOR_GROUP,
      version=SERVICEMONITOR_VERSION,
      namespace=NAMESPACE,
      plural=SERVICEMONITOR_PURAL,
      name=LABEL,
      body=serviceMonitor
   )
   log.info("Patch serviceMonitor %s" % str(serviceMonitor))

# delete the service and endpoint if vSAN cluster does not exist
# @v1: kubernetes core api
# @clusterDict: dict for cluster hosts relationship, which is from vCenter service discovery
# @endpointDict: the dict for service and endpoints, which is from Kurbernete services
def deleteServiceEndpointIfNeed(v1, clusterDict, endpointDict):
   clusterNames = set([cluster.lower() for cluster in clusterDict.keys()])
   obsoletedNames = list(set(endpointDict.keys()) - clusterNames)
   deleteServiceEndpoint(v1, obsoletedNames)

# delete the service and endpoint based on names
def deleteServiceEndpoint(v1, obsoletedNames):
   for obsoletedName in obsoletedNames:
      try:
         v1.delete_namespaced_endpoints(obsoletedName, NAMESPACE)
         v1.delete_namespaced_service(obsoletedName, NAMESPACE)
         log.info("Delete service and endpoint %s in namespace %s" % (obsoletedName, NAMESPACE))
      except Exception as e:
         log.exception("Cannot delete service and endpoint for %s, details: %s" % (obsoletedName, str(e)))

# update the endpoint ip list if hosts have been added or removed
# @v1: kubernetes core api
# @serviceName: the Kubernetes service name
# @endpointDict: the dict,  key:service name, val: endpoint
# @hostNames: the cluster host names
def updateEndpointIfNeed(v1, serviceName, endpointDict, hostNames):
   try:
      endpoint = endpointDict[serviceName]
      addresses = endpoint.subsets[0].addresses
      addressesIps = set([address.ip for address in addresses])
      hostNames = set([host for host in hostNames])
      if addressesIps != hostNames:
         endpoint.subsets[0].addresses = hostNames
         v1.patch_namespaced_endpoints(serviceName, NAMESPACE, endpoint)
         log.info("Update endpoint %s under namespace %s with value %s" %(serviceName, NAMESPACE, endpoint))
   except Exception as e:
      log.exception("Cannot update Kubernetes endpoint details: %s" % (str(e)))


# add a new service and endpoint for a new vSAN cluster
# @v1: kubernetes core api
# @serviceName: Kubernetes service name, which is also cluster name
# @hostNames: the hostNames is used for populated in the endpoint subsets
# @hostPorts: host ports list
def addNewServiceEndpoints(v1, serviceName, hostNames, hostPorts):
   try:
      metadata = {"name": serviceName, "labels": {LABEL_KEY: LABEL}}
      ports = [{"name": "metrics", "port": port} for port in hostPorts]

      service = client.V1Service()
      service.metadata = metadata
      service.spec = {"clusterIP": "None", "ports": ports}
      v1.create_namespaced_service(NAMESPACE, service)
      log.info("Create service %s" % str(service))
   except Exception as e:
      log.exception("Cannot create Kubernates service and endpoint for cluster %s, details: %s" %(serviceName, str(e)))

   try:
      endpoint = client.V1Endpoints()
      endpoint.metadata = metadata
      endpointHosts = [{'ip': host} for host in hostNames]
      endpoint.subsets = [{"addresses": endpointHosts, 'ports': ports}]
      v1.create_namespaced_endpoints(NAMESPACE, endpoint)
      log.info("Create endpoint %s" % str(endpoint))
   except Exception as e:
      log.exception("Cannot create Kubernates service and endpoint for cluster %s, details: %s" %(serviceName, str(e)))

# build dict for cluster-hosts-metrics-path from providers from vc service discovery
def getClusterDictFromProvider(providers):
   clusterDict = {}
   providers = json.loads(providers)
   for provider in providers:
      labels = provider.get('labels') or {}
      cluster_name = labels.get('cluster_name')
      if not clusterDict.get(cluster_name):
         clusterDict[cluster_name] = {
            "hosts": [],
            "metrics_path": [],
            "ports": []
         }
      host_ip_port = provider.get('targets')[0]
      host_ip = host_ip_port.split(':')[0]
      host_port = host_ip_port.split(':')[1]
      try:
         ipaddress.IPv4Address(host_ip)
      except:
         # not valid ip address
         host_ip = socket.gethostbyname(host_ip)
      clusterDict[cluster_name]["hosts"].append(host_ip)
      clusterDict[cluster_name]["ports"].append(int(host_port))
      metrics_path = provider['labels'].get('__metrics_path__')
      clusterDict[cluster_name]['metrics_path'].append(metrics_path)
   log.info(clusterDict)
   return clusterDict

# compare the K8s endpoints and service with the vSAN clusters, update the endpoints and service if needed
# @v1: kubernetes core api
# @providers: the vCenter service discovery api output
def updateK8sServiceEndpoints(v1, providers):
   clusterDict = getClusterDictFromProvider(providers)
   endpoints = v1.list_namespaced_endpoints(NAMESPACE, label_selector="%s=%s" %(LABEL_KEY, LABEL))
   endpointDict = dict((endpoint.metadata.name, endpoint) for endpoint in endpoints.items)

   # handling k8s service and endpoints
   for cluster, props in six.iteritems(clusterDict):
      hosts = list(set(props['hosts']))
      ports = list(set(props['ports']))
      name = cluster.lower()
      if name in endpointDict.keys():
         updateEndpointIfNeed(v1, name, endpointDict, hosts)
      else:
         addNewServiceEndpoints(v1, name, hosts, ports)

   deleteServiceEndpointIfNeed(v1, clusterDict, endpointDict)

   # handling k8s servicemonitor
   customApi = client.CustomObjectsApi()
   serviceMonitors = customApi.list_namespaced_custom_object(
      group=SERVICEMONITOR_GROUP,
      version=SERVICEMONITOR_VERSION,
      namespace=NAMESPACE,
      plural=SERVICEMONITOR_PURAL)
   vSanServiceMonitor = [item for item in serviceMonitors['items'] if item['metadata']['name'] == LABEL]
   if len(vSanServiceMonitor) == 0:
      createServiceMonitor(clusterDict)
   else:
      updateServiceMonitor(vSanServiceMonitor[0], clusterDict)

# clean the services endpoints and serviceMonitor this container has been created
# @v1: kubernetes core api
# @namespace: the current kubernetes namespace
# @signum: signal type, we register signal.SIGTERM as the call back, reserved for callback function
# @frame: the current stack frame, reserved for callback function
def cleanServiceEndpoints(v1, signum, frame):
   log.info("clean service endpoints and serviceMonitor")
   endpoints = v1.list_namespaced_endpoints(NAMESPACE, label_selector="%s=%s" %(LABEL_KEY, LABEL))
   endpointNames = [endpoint.metadata.name for endpoint in endpoints.items]
   deleteServiceEndpoint(v1, endpointNames)

   try:
      customApi = client.CustomObjectsApi()
      customApi.delete_namespaced_custom_object(
         group=SERVICEMONITOR_GROUP,
         version=SERVICEMONITOR_VERSION,
         namespace=NAMESPACE,
         plural=SERVICEMONITOR_PURAL,
         name=LABEL,
         body=client.V1DeleteOptions())
      log.info("Delete ServiceMonitor %s " % LABEL)
   except Exception as e:
      log.exception("Cannot delete serviceMonitor %s, details: %s" %(LABEL, str(e)))

def main():
   serversList_hash = None
   bearer_token = getBearToken()
   config.load_incluster_config()
   v1 = client.CoreV1Api()
   signal.signal(signal.SIGTERM, partial(cleanServiceEndpoints, v1))
   while True:
      try:
         providers = getProviderFromServiceDiscovery(bearer_token)
         providers_hash = hashlib.sha1(providers.encode()).hexdigest()

         if serversList_hash != providers_hash:
            serversList_hash = providers_hash
            updateK8sServiceEndpoints(v1, providers)

      except Exception as e:
         log.exception(str(e))
      time.sleep(INTERVAL_SEC)

# Start program
if __name__ == "__main__":
   main()
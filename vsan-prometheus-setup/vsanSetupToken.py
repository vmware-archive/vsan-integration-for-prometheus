#!/usr/bin/env python3
#
# Copyright 2020-2021 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause
#

from pyVmomi import vim
from pyVim.connect import SmartConnect, Disconnect
import pyVim.task

import atexit
import argparse
import getpass
import uuid
import sys
import ssl

# Import the vSAN API python bindings and utilities.
import vsanmgmtObjects
import vsanapiutils

METRIC_CONFIG_FEATURE = 'metricsconfig'
VC_TYPE = 'VirtualCenter'

# if no password is specified on the command line, prompt for it
def PromptPassword(args):
   if not args.password:
      args.password = getpass.getpass(
         prompt='Enter password for host %s and username %s: ' %(args.host, args.username))
   return args

# setup the command line arguments
def GetArgs():
   parser = argparse.ArgumentParser(description='Arguments for vCenter')

   parser.add_argument('-s', '--host', required=True, action='store',
                       help='vSphere service to connect to')
   parser.add_argument('-o', '--port', type=int, default=443, action='store',
                       help='Port to connect on')
   parser.add_argument('-u', '--username', required=True, action='store',
                       help='User name to use')
   parser.add_argument('-p', '--password', required=False, action='store',
                       help='Password to use')
   parser.add_argument('-c', '--cluster', dest='cluster', action='store',
                      default='VSAN-Cluster')
   args = parser.parse_args()
   PromptPassword(args)
   return args

# get vSAN cluster instance
def getClusterInstance(clusterName, serviceInstance):
   content = serviceInstance.RetrieveContent()
   searchIndex = content.searchIndex
   datacenters = content.rootFolder.childEntity
   for datacenter in datacenters:
      cluster = searchIndex.FindChild(datacenter.hostFolder, clusterName)
      if cluster is not None:
         return cluster
   return None

# using uuid for generating token
def GenerateRandomToken():
   return str(uuid.uuid4())[:30]

# get the metric spec
def SetupClusterMetricSpec(token):
   metricsConfig = vim.vsan.MetricsConfig(profiles=[])
   if token and len(token) <= 30:
      metricsConfig.profiles.append(vim.vsan.MetricProfile(authToken=token))
   spec = vim.vsan.ReconfigSpec()
   spec.metricsConfig = metricsConfig
   return spec

# setup metric token through vSAN config system.
def SetUpMetricToken(si, clusterConfigSystem, cluster):
   token = GenerateRandomToken()
   spec = SetupClusterMetricSpec(token)
   # ReconfigureEx method need privilege Host.Inventory.EditCluster on the cluster
   vsanTask = clusterConfigSystem.ReconfigureEx(cluster, spec)
   vcTask = vsanapiutils.ConvertVsanTaskToVcTask(vsanTask, si._stub)
   vsanapiutils.WaitForTasks([vcTask], si)
   if vcTask.info.state != 'success':
      raise Exception("Failed to reconfig vSAN metrics config: %s. Args: %s" % (vcTask.info, spec))
   return token

# check the feature is supported in vSAN cluster or not
def CheckVsanCapability(vcs, cluster, feature):
   isFeatureSupported = False
   capabilities = vcs.GetCapabilities([cluster])

   for cap in capabilities:
      if feature in cap.capabilities:
         isFeatureSupported = True
   return isFeatureSupported

def main():
   args = GetArgs()

   # login host with default ssl context
   context = ssl.create_default_context()
   context.check_hostname = False
   context.verify_mode = ssl.CERT_NONE

   si = SmartConnect(host=args.host,
                     user=args.username,
                     pwd=args.password,
                     port=int(args.port),
                     sslContext=context)

   atexit.register(Disconnect, si)

   aboutInfo = si.content.about
   apiVersion = vsanapiutils.GetLatestVmodlVersion(args.host)
   if aboutInfo.apiType != VC_TYPE:
      sys.stdout.write("The host %s is not VMware VirtualCenter:\n" % args.host)
      return -1
   sys.stdout.write("Successfully connected to vCenter!\n")

   # Get vSAN clusterConfigSystem from the vCenter Managed Object references.
   vcMos = vsanapiutils.GetVsanVcMos(si._stub, context=context, version=apiVersion)
   vccs = vcMos['vsan-cluster-config-system']

   cluster = getClusterInstance(args.cluster, si)
   if cluster is None:
      sys.stdout.write("Cluster %s is not found for %s\n" % (args.cluster, args.host))
      return -1

   vcs = vcMos['vsan-vc-capability-system']
   if not CheckVsanCapability(vcs, cluster, METRIC_CONFIG_FEATURE):
      sys.stdout.write("Cluster %s does not support token setup\n" % (args.cluster))
      return -1

   try:
      token = SetUpMetricToken(si, vccs, cluster)
      # the last line of output is the token value
      sys.stdout.write("Successfully generate a new token:\n")
      sys.stdout.write("%s\n" % token)
      return 0
   except Exception as e:
      sys.stderr.write("Cannot setup cluster prometheus token: %s" % str(e))
      return -1

# Start program
if __name__ == "__main__":
   main()
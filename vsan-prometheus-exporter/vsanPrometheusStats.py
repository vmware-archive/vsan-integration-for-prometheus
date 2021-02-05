#!/usr/bin/env python3
#
# Copyright 2020-2021 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause
#

import os
import json
import logging
import threading
import time
import uuid
from pyVmomi import vim
from pyVim.connect import Disconnect

import prometheus
from connectUtils import ConnectToVC, ConnectToHost, GetClusterInstance

pre70MissingMetrics = {
   ('/vmkModules/vsan/dom', 'clientStats'): [
      'unmapCount', 'unmapBytes', 'unmapLatencySumUs', 'unmapCongestionSum',
   ],
   ('/vmkModules/vsan/dom', 'ownerStats'): [
      'unmapCount', 'unmapBytes', 'unmapLatencySumUs', 'unmapCongestionSum',
      'writeLeafOwnerCount', 'writeLeafOwnerLatencySumUs',

      'readLeafOwnerCount', 'readLeafOwnerLatencySumUs',
      'unmapLeafOwnerCount', 'unmapLeafOwnerLatencySumUs',
      'recoveryWriteLeafOwnerCount', 'recoveryWriteLeafOwnerLatencySumUs',
      'recoveryUnmapLeafOwnerCount', 'recoveryUnmapLeafOwnerLatencySumUs',
   ],
   ('/vmkModules/vsan/dom', 'compmgrStats'): [
      'unmapCount', 'unmapBytes', 'unmapLatencySumUs', 'unmapCongestionSum',

      'recoveryWriteBytes',
   ],
   ('/vmkModules/vsan/dom/compSchedulers', '%s/stats'): [
      'writeCount', 'writeBytes', 'writeLatencySumUs', 'numOIOSumWrite',
      'readCount', 'readBytes', 'readLatencySumUs', 'numOIOSumRead',
      'unmapCount', 'unmapBytes', 'unmapLatencySumUs', 'numOIOSumUnmap',
      'recoveryWriteCount',

      'recoveryWriteBytes', 'recoveryWriteLatencySumUs',
      'numOIOSumRecoveryWrite', 'numOIOSumRecoveryUnmap',
      'recoveryUnmapCount', 'recoveryUnmapBytes', 'recoveryUnmapLatencySumUs',
   ],
   ('/vmkModules/vsan/dom/compSchedulers', '%s/OriginStatsDecom'): [
      'sumBytesToSync',
   ],
   ('/vmkModules/vsan/dom/compSchedulers', '%s/OriginStatsFixCompliance'): [
      'sumBytesToSync',
   ],
   ('/vmkModules/vsan/dom/compSchedulers', '%s/OriginStatsPolicyChange'): [
      'sumBytesToSync',
   ],
   ('/vmkModules/vsan/dom/compSchedulers', '%s/OriginStatsRebalance'): [
      'sumBytesToSync',
   ],
   ('/vmkModules/plog/devices', '%r/info|elevStats:./%s/info[deviceUUID]'): [
      'memP', 'dataP', 'ssdP', 'maxP', 'zeroP', 'logP',
   ],
   ('/vmkModules/plog/devices', '%r/info|dedupStats:./%s/info[deviceUUID]'): [
      'txnReplayHashmapTime', 'txnReplayBitmapTime', 'txnReplayXmapTime',
      'txnReplayBgWriteIOs', 'txnReplayFgWriteIOs', 'txnWrites',
      'cacheMissesBmap', 'cacheMissesXmap', 'cacheMissesHmap',
      'cacheHitsBmap', 'cacheHitsXmap', 'cacheHitsHmap',
      'pendingTxnReplayYields', 'txnReplayReadIOHits',
   ],
   ('/net/nics', '$getVsanNetworkStats'): [
      'rcvbyte', 'sndbyte', 'rcvduppack', 'rcvdupack',
      'sack_rcv_blocks', 'sack_send_blocks',
      'sack_rexmits', 'rcvoopack',
   ],
}

def _IterateAndFormatStats(vsanStats):
   for node1, node2s, fn in prometheus.paths:
      out = {}
      for node2 in node2s:
         nodeStats = vsanStats['stats'].get('{}/{}'.format(node1, node2))
         if not nodeStats:
            continue
         for entity, values in nodeStats['entities'].items():
            statsDict = dict(zip(nodeStats['metrics'], values))
            missingMetrics = pre70MissingMetrics.get((node1, node2), [])
            for m in missingMetrics:
               if m not in statsDict:
                  # set value "-1" for missing metrics to filter them later
                  statsDict[m] = -1
            try:
               fn(out, node1, node2, entity, statsDict)
            except:
               logging.exception(
                  'Failed to process metrics of entity {}, {}, {}'.format(
                     node1, node2, entity))
      yield out

# Convert vsan metrics stats to prometheus format
def ConvertStats(hostInfo, vsanStats):
   for stats in _IterateAndFormatStats(vsanStats):
      yield prometheus.generatePrometheusFormat(hostInfo, stats, None)

def _GetDiskInfo(diskStruct, isCap, ssd):
   return  {
      'Device': diskStruct.canonicalName,
      'VSAN UUID': diskStruct.vsanDiskInfo.vsanUuid,
      'VSAN Disk Group UUID': ssd.vsanDiskInfo.vsanUuid,
      'Is Capacity Tier': isCap,
   }

def _GetDGInfo(dg):
   out = []
   out.append(_GetDiskInfo(dg.ssd, False, dg.ssd))
   for cap in dg.nonSsd:
      out.append(_GetDiskInfo(cap, True, dg.ssd))
   return out

def GetHostInfo(hostname, vsanConfig):
   disks = []
   for dg in vsanConfig.storageInfo.diskMapping:
      disks.extend(_GetDGInfo(dg))
   out = {
      'vsan_cluster_uuid': vsanConfig.clusterInfo.uuid,
      'host_uuid': vsanConfig.clusterInfo.nodeUuid,
      'hostname': hostname,
      'disks': dict([(d['VSAN UUID'], d) for d in disks])
   }
   return out

# Connect to every host and get their SoapStubAdapter so can call VMODL API later
def GetHostMos(hostRefList):
   hostMos = {}
   def _ConnectToHostThread(hostRef):
      vsanStub = ConnectToHost(hostRef)
      if vsanStub is None:
         return
      vis = vim.cluster.VsanInternalStatsProvider(
         'vsan-internal-statsprovider', vsanStub)
      hostId = hostRef._moId
      hostname = hostRef.name
      vsanConfig = hostRef.configManager.vsanSystem.config
      hostInfo = GetHostInfo(hostname, vsanConfig)
      hostMos[hostId] = (vis, hostInfo)

   threads = []
   for hostRef in hostRefList:
      threads.append(threading.Thread(
         target=_ConnectToHostThread, args=(hostRef,)))

   logging.info('Connecting to hosts')
   [t.start() for t in threads]
   [t.join() for t in threads]
   logging.info('Connected to all hosts')
   return hostMos

# Call VMODL API to retrieve vsan metrics stats
def FetchVsanStats(vis):
   return vis.CaptureInternalStats(None, None, False)

# Retrieve vsan metrics stats for one host
def RetrieveStatsForHost(hostId, hostMoInfo):
   vis, hostInfo = hostMoInfo
   t1 = time.time()
   try:
      stats = json.loads(FetchVsanStats(vis))
   except:
      logging.exception('Failed to retrieve stats for host %s', hostId)
      stats = None
   t2 = time.time()
   logging.info('Fetching stats for %s took %.2fs', hostId, t2 - t1)
   if stats is not None:
      out = ConvertStats(hostInfo, stats)
   else:
      out = []
   return out

# Retrieve vsan metrics stats for all hosts
#
# Sample:
# result = {
#    'host1': [
#       ['h1-metrics1-stats-line1', 'h1-metrics1-stats-line2', '...'],
#       ['h1-metrics2-stats-line1', 'h1-metrics2-stats-line2', '...'],
#    ],
#    'host2': [
#       ['h2-metrics1-stats-line1', 'h2-metrics1-stats-line2', '...'],
#       ['h2-metrics2-stats-line1', 'h2-metrics2-stats-line2', '...'],
#    ],
#    '...': [],
# }
#
def RetrieveStatsForHosts(hostMos):
   result = {}

   def _RetrieveStatsForHostThread(hostId, hostMoInfo):
      result[hostId] = RetrieveStatsForHost(hostId, hostMoInfo)

   threads = []
   for hostId, hostMoInfo in hostMos.items():
      threads.append(threading.Thread(
         target=_RetrieveStatsForHostThread, args=(hostId, hostMoInfo)))
   [t.start() for t in threads]
   [t.join() for t in threads]
   return result

def GenerateStatsAsStream(hostResultList):
   for hostResult in hostResultList:
      for pathStats in hostResult:
         for line in pathStats:
            yield line + '\n'

def GenerateStatsAsString(hostResultList):
  return ''.join(GenerateStatsAsStream(hostResultList))


class VsanPrometheusStats:
   # The interval used to check current connected hosts and the whole hosts in
   # the cluster.
   HOST_CONSISTENCY_CHECK_INTERVAL = int(
      os.environ.get('HOST_CONSISTENCY_CHECK_INTERVAL', 300))

   # If env variable "VCENTER" is set, will connect to it automatically on start
   VCENTER = os.environ.get('VCENTER')
   # The bearer token used for authorization, will be generated automatically
   # if not set
   BEARER_TOKEN = os.environ.get('BEARER_TOKEN')

   def __init__(self):
      self.si = None
      self.vcip = None
      self.vcport = None
      self.vcuser = None
      self.clusterName = None
      self.clusterRef = None
      self.hostMos = {}
      self.lastUpdateTime = None
      self.authToken = None

      # connect to VC automatically once start if env variable "VCENTER" is set
      if self.VCENTER:
         logging.info('Env "VCENTER" is set, connecting to VC automatically')
         self.connectOnStart(self.VCENTER)

   def connectOnStart(self, vcip):
      vcport = os.environ.get('VCPORT', '443')
      vcuser = os.environ.get('VCUSER', '')
      vcpassword = os.environ.get('VCPASSWORD', '')
      clusterName = os.environ.get('CLUSTERNAME', '')
      logging.info('vcip: %s, vcport: %s, vcuser: %s, clusterName: %s',
         vcip, vcport, vcuser, clusterName)
      try:
         self.connect(vcip, vcport, vcuser, vcpassword, clusterName)
      except:
         logging.error('Failed to connect to VC')

   def connect(self, vcip, vcport, vcuser, vcpassword, clusterName):
      try:
         self.si = ConnectToVC(vcip, vcport, vcuser, vcpassword)
      except vim.fault.InvalidLogin as ex:
         logging.error(ex.msg)
         raise Exception(ex.msg)
      except:
         msg = 'Exception when connecting to VC {}'.format(vcip)
         logging.exception(msg)
         raise Exception(msg)

      self.clusterRef = GetClusterInstance(clusterName, self.si)
      if self.clusterRef is None:
         msg = 'Cluster {} not found'.format(clusterName)
         logging.error(msg)
         raise Exception(msg)

      logging.info('Connected to VC %s successfully', vcip)
      self.vcip = vcip
      self.vcport = vcport
      self.vcuser = vcuser
      self.clusterName = clusterName
      self.hostMos = GetHostMos(self.clusterRef.host)
      self.lastUpdateTime = time.time()
      if self.BEARER_TOKEN is not None:
         logging.info('Load auth token from env "BEARER_TOKEN"')
         self.authToken = self.BEARER_TOKEN
      else:
         self.authToken = str(uuid.uuid4())
      logging.info('Auth token is %s', self.authToken)

   def serviceDiscovery(self, serverHost):
      result = []
      if self.clusterRef is None:
         return result

      self._hostConsistencyCheck()
      clusterName = self.clusterRef.name
      clusterId = self.clusterRef._moId
      for hostId in self.hostMos:
         result.append({
            'targets': [serverHost],
            'labels': {
               '__metrics_path__': '/vsan/metrics/{}'.format(hostId),
               'cluster_name': clusterName,
               'cluster_id': clusterId,
               '__scheme__': 'http',
            },
         })
      return result

   def isAuthorized(self, authToken):
     return self.authToken is not None and self.authToken == authToken

   def getStatsForAllHosts(self):
      logging.info('Get stats for all hosts')
      result = None
      if self.clusterRef is None:
         logging.error('Cluster not connected')
         return result

      result = RetrieveStatsForHosts(self.hostMos)
      return result

   def getStatsForHost(self, hostId):
      logging.info('Get stats for host %s', hostId)
      result = None
      if self.clusterRef is None:
         logging.error('Cluster not connected')
         return result

      if hostId not in self.hostMos:
         logging.warning('Host %s not connected, trying to connect', hostId)
         targetHostRef = None
         for hostRef in self.clusterRef.host:
            if hostRef._moId == hostId:
               targetHostRef = hostRef
               break
         if targetHostRef is None:
            logging.error('Host %s not found in cluster', hostId)
         else:
            self.hostMos.update(GetHostMos([targetHostRef]))

      if hostId in self.hostMos:
         result = {}
         result[hostId] = RetrieveStatsForHost(
            hostId, self.hostMos[hostId])
      return result

   # Check whether connected hosts are consistent with all hosts in the cluster
   def _hostConsistencyCheck(self):
      if self.clusterRef is None:
         return
      if (time.time() - self.lastUpdateTime <
            self.HOST_CONSISTENCY_CHECK_INTERVAL):
         return

      logging.info(
         'Check consistency of connected hosts against cluster hosts, '
         'last check time %s', time.strftime('%Y-%m-%d %H:%M:%S+0000',
         time.gmtime(self.lastUpdateTime)))

      allHostIds = []
      missingHostRefs = []
      for hostRef in self.clusterRef.host:
         allHostIds.append(hostRef._moId)
         if hostRef._moId not in self.hostMos:
            missingHostRefs.append(hostRef)
      if missingHostRefs:
         logging.info('Hosts %s not connected, trying to connect',
            [hostRef._moId for hostRef in missingHostRefs])
         self.hostMos.update(GetHostMos(missingHostRefs))

      for hostId in list(self.hostMos.keys()):
         if hostId not in allHostIds:
            logging.info('Host %s obsolete in the connection list, remove it')
            del self.hostMos[hostId]

      self.lastUpdateTime = time.time()

   def generateStatsAsStream(self, result):
      return GenerateStatsAsStream(result.values())

   def generateStatsAsString(self, result):
      return GenerateStatsAsString(result.values())


if __name__ == '__main__':
   logging.basicConfig(level=logging.DEBUG)

   vcip = '10.78.82.107'
   vcport = 443
   vcuser = 'administrator@vsphere.local'
   vcpassword = 'Admin!23'
   clusterName = 'VSAN-Cluster'

   vps = VsanPrometheusStats()
   try:
      vps.connect(vcip, vcport, vcuser, vcpassword, clusterName)
   except Exception as ex:
      logging.error(ex)
      import sys
      sys.exit(1)

   result = vps.getStatsForAllHosts()
   resultStr = vps.generateStatsAsString(result)
   with open('result-all.txt', 'w') as f:
      f.write(resultStr)
   logging.info('Stats for all hosts saved')

   hostRef = vps.clusterRef.host[0]
   hostId = hostRef._moId
   result = vps.getStatsForHost(hostId)
   resultStr = vps.generateStatsAsString(result)
   with open('result-{}.txt'.format(hostId), 'w') as f:
      f.write(resultStr)
   logging.info('Stats for host %s saved', hostId)

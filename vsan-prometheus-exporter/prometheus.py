#!/usr/bin/env python3
#
# Copyright 2020 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause
#

import re
import time
import json
import logging

def pinit(out, metric):
   out.setdefault(metric, {'help': None, 'origin': {'path': None, 'nodes': set()}, 'values': []})

def rec(out, metric, value, labels):
   # filter the non existing metrics
   if value < 0:
      return
   pinit(out, metric)
   out[metric]['values'].append((value, labels))

def phelp(out, metric, helpStr, node1, node2):
   pinit(out, metric)
   out[metric]['help'] = helpStr
   out[metric]['origin']['path'] = node1
   out[metric]['origin']['nodes'].add(node2)

def vcpuMetrics(out, node1, node2, entity, metrics):
   metricMap = {"upTime": "uptime", "usedTime": "usedtime", "readyTime": "readytime"}
   #["$getLsomWorldInformation", "$getDomWorldInformation",
   #  "$getNicWorldInformation", "$getCmmdsWorldInformation"]
   x = entity.split("|")
   if node2 == "$getDomWorldInformation":
      y = x[1].split('_')
      # XXX: Encode DOM
      # XXX: x[1] translation is not universal, depends on DOM vs. PLOG vs ...
      labels = {"subsystem": "DOM", "host_uuid": x[0], "world_id": x[2], "role": y[2]}
   elif node2 == "$getLsomWorldInformation":
      m = re.match(r'(PLOG|LLOG|DDP)-([a-z0-9]{8}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{12})-(.*)', x[1])
      if m:
         labels = {'subsystem': m.group(1), 'host_uuid': x[0], 'disk_uuid': m.group(2), 'name': m.group(3)}
         if len(x) >= 3:
            labels['world_id'] = x[2]
      else:
         m = re.match(r'(VSAN)_(0x[a-f0-9]*)_(.*)', x[1])
         if not m:
            print(x[1])
         assert(m)
         labels = {'subsystem': m.group(3), 'host_uuid': x[0], 'name': x[1]}

      assert(m)
   elif node2 == "$getNicWorldInformation":
      labels = {"subsystem": "Network", "host_uuid": x[0], "name": x[1]}
      # # XXX: Don't seem to match?!
      # metricMap = {"waitTime": "waittime", "runTime": "usedtime", "readyTime": "readytime"}
   elif node2 == "$getCmmdsWorldInformation":
      y = x[1].split('_')
      labels = {"subsystem": "CMMDS", "host_uuid": x[0], "world_id": x[2], "role": x[1] if len(y) == 1 else y[2]}
   else:
      raise Exception(node2)

   phelp(out, 'vmware_esx_world_uptime_seconds_total', "Worlds is what ESX calls threads. Except when noted in the name, refers to a single world. uptime is a sum total of the time the world was not paused", node1, node2)
   phelp(out, 'vmware_esx_world_usedtime_seconds_total', "Worlds is what ESX calls threads. Except when noted in the name, refers to a single world. usedtime is a sum total of the time the world was running on a pCPU. So usedtime/uptime is utilization.", node1, node2)
   phelp(out, 'vmware_esx_world_readytime_seconds_total', "Worlds is what ESX calls threads. Except when noted in the name, refers to a single world. readytime is a sum total of the time the world was activated, but waiting for a pCPU.", node1, node2)
   for cur, new in metricMap.items():
      if cur == 'upTime' and cur not in metrics:
         cur = 'runTime'
      rec(out, "vmware_esx_world_%s_seconds_total" % new, metrics[cur] / 1000.0**3, labels)

def heapMetrics(out, node1, node2, entity, metrics):
   # "/system/heaps/$getHeapInformation":

   x = entity.split("|")
   m = re.match(r"(.*)-(0x[a-f0-9]*)$", x[1])
   assert(m)
   labels = {"subsystem": "system", "host_uuid": x[0], "heap_id": m.group(2), 'heap_name': m.group(1)}
   if 'dom' in x[1]:
      labels['subsystem'] = "DOM"
   if 'CMMDS' in x[1]:
      labels['subsystem'] = "CMMDS"
   if 'virsto' in x[1] or 'LSOM' in x[1]:
      labels['subsystem'] = "LSOM"
   if 'vsanbase' in x[1] or 'vsanutil' in x[1]:
      labels['subsystem'] = "VSAN"
   if 'vsanSparse' in x[1]:
      labels['subsystem'] = "VSANSparse"
   if 'RDT' in x[1]:
      labels['subsystem'] = "RDT"

   phelp(out, "vmware_esx_heap_usage_ratio", "Point in time. Usage of heap (mempool) in percent. For some being full is normal, others may impact control or IO operations", node1, node2)
   rec(out, "vmware_esx_heap_usage_ratio", metrics['heapUtil'] / 100.0, labels)


def domRoleState(out, node1, node2, entity, metrics):
   #"/vmkModules/vsan/dom"
   labels = {
      'host_uuid': entity,
      'role': node2.replace('Stats', ''),
   }
   isOwner = labels['role'] == 'owner'
   isClient = labels['role'] == 'client'

   phelp(out, 'vmware_vsan_dom_io_total', 'Total IOs processed by vSAN DOM since boot.', node1, node2)
   phelp(out, 'vmware_vsan_dom_io_bytes_total', 'Total Bytes processed by vSAN DOM since boot.', node1, node2)
   phelp(out, 'vmware_vsan_dom_io_duration_seconds_total', 'Sum total of duration of IO processed by vSAN DOM since boot.', node1, node2)
   phelp(out, 'vmware_vsan_dom_io_durationsquare_seconds_total', 'Sum total of duration^2 of IO processed by vSAN DOM since boot.', node1, node2)
   phelp(out, 'vmware_vsan_dom_congestion_total', 'Sum total of observed congestion values by vSAN DOM since boot.', node1, node2)
   phelp(out, 'vmware_vsan_dom_numoio_total', 'Sum total of observed Outstanding IOs (aka Queue Depth) by vSAN DOM since boot.', node1, node2)

   keys = ["write", "read", "unmap", "recoveryWrite", "resyncRead"]
   if isClient:
      keys = ["write", "read", "unmap"]

   for key in keys:
      ioLabels = labels.copy()
      ioLabels['io_type'] = key
      rec(out, "vmware_vsan_dom_io_total", metrics['%sCount' % key], ioLabels)
      rec(out, "vmware_vsan_dom_io_bytes_total", metrics['%sBytes' % key], ioLabels)
      rec(out, "vmware_vsan_dom_io_duration_seconds_total", metrics['%sLatencySumUs' % key] / 1000.0**2, ioLabels)
      rec(out, "vmware_vsan_dom_io_durationsquare_seconds_total", metrics.get('%sLatencySqSumUs' % key, 0) / 1000.0**4, ioLabels)
      rec(out, "vmware_vsan_dom_congestion_total", metrics['%sCongestionSum' % key], ioLabels)

   if isOwner:
      for key in ["write", "read", "unmap", "recoveryWrite", "recoveryUnmap"]:
         ioLabels = labels.copy()
         ioLabels['io_type'] = key
         ioLabels['role'] = 'ownerLeaf'
         rec(out, "vmware_vsan_dom_io_total", metrics['%sLeafOwnerCount' % key], ioLabels)
         rec(out, "vmware_vsan_dom_io_duration_seconds_total", metrics['%sLeafOwnerLatencySumUs' % key] / 1000.0**2, ioLabels)

   rec(out, "vmware_vsan_dom_numoio_total", metrics["numOIOSum"], labels)



def domDgState(out, node1, node2, entity, metrics):
   # "/vmkModules/vsan/dom/compSchedulers" "%s/stats"
   labels = {
      'disk_uuid': entity,
   }

            # "sumQueuedBytes",
            # "sumOutstandingBytes",
            # "sumResyncRecWBytes",
            # "sumResyncReadBytes",

            # "sumResyncRecWCount",
            # "sumResyncReadCount",

            # "sumResyncRecWLatencyUs",
            # "sumResyncReadLatencyUs",
            # "sumLatencyForVMDiskUs",
            # "sumLatencyForNameSpaceUs",
            # "sumLatencyForRecoveryUs",
            # "sumLatencyForActivationUs",
            # "sumLatencyForMetaDataUs",

            # "numActivation",
            # "numDirectActivation",

            # "queueBytesMetaData",
            # "queueBytesRecovery",
            # "queueSumOpVMDisk",
            # "queueSumOpNameSpace",
            # "queueSumOpRecovery",
            # "queueBytesNameSpace",
            # "queueSumOpMetaData",
            # "queueBytesVMDisk",


   phelp(out, 'vmware_vsan_domdg_io_total', 'Total IOs processed by vSAN DOM on DiskGroup since boot.', node1, node2)
   phelp(out, 'vmware_vsan_domdg_io_bytes_total', 'Total Bytes processed by vSAN DOM on DiskGroup since boot.', node1, node2)
   phelp(out, 'vmware_vsan_domdg_io_duration_seconds_total', 'Sum total of duration of IO processed by vSAN DOM on DiskGroup since boot.', node1, node2)
   phelp(out, 'vmware_vsan_domdg_numoio_total', 'Sum total of observed Outstanding IOs (aka Queue Depth) by vSAN DOM on DiskGroup since boot.', node1, node2)

   for key in ["write", "read", "unmap", "recoveryWrite", "recoveryUnmap"]:
      ioLabels = labels.copy()
      ioLabels['io_type'] = key
      keyCap = "%s%s" % (key[:1].capitalize(), key[1:])
      rec(out, "vmware_vsan_domdg_io_total", metrics['%sCount' % key], ioLabels)
      rec(out, "vmware_vsan_domdg_io_bytes_total", metrics['%sBytes' % key], ioLabels)
      rec(out, "vmware_vsan_domdg_io_duration_seconds_total", metrics['%sLatencySumUs' % key] / 1000.0**2, ioLabels)
      rec(out, "vmware_vsan_domdg_numoio_total", metrics["numOIOSum%s" % keyCap], ioLabels)

   # "/vmkModules/vsan/dom/compSchedulers": ["%s/stats"]


def plogDevicesStats(out, node1, node2, entity, metrics):
   # "/vmkModules/plog/devices" "%r/info|stats:./%s/info[deviceUUID]"
   labels = {'disk_uuid': entity}
   metrics = dict([(k.replace('stats/', '').replace('/stats', ''), v) for k, v in metrics.items()])

   # for ioType in ['read', 'write']:
   #          "totalQTimeOrdered",
   #          "nrIOs",
   #          "totalQTimeUnOrdered",
   #          "encTimeLatency",
   #          "totalLatency",
   #          "numHelperQueueElems",
   #          "queueTimeLatency"]
   #    pass

   # out["vmware_vsan_plog_readfromcapacity_bytes_total"] = (metrics['totalBytesReadFromMD'], labels)
   # out["vmware_vsan_plog_readfromcache_bytes_total"] = (metrics['totalBytesReadFromSSD'], labels)
   # out["vmware_vsan_plog_read_bytes_total"] = (metrics['totalBytesRead'], labels)
   # out["vmware_vsan_plog_numio_total"] = (metrics['nrIOs'], labels)

   phelp(out, "vmware_vsan_disk_drain_total", "Sum total of bytes drained/destaged from cache to capacity, split by zeros (from component delete, TRIM/UNMAP) and real data.", node1, node2)
   # Not emitting "totalBytesDrained" as it is redundant
   assert(metrics['totalBytesDrained'] == metrics['ssdBytesDrained'] + metrics['zeroBytesDrained'])
   for ioType, name in [('ssd', 'data'), ('zero', 'zero')]:
      ioLabels = labels.copy()
      ioLabels['drain_type'] = name
      rec(out, "vmware_vsan_disk_drain_bytes_total", metrics['%sBytesDrained' % ioType], ioLabels)

def plogDevicesElevStats(out, node1, node2, entity, metrics):
   # "/vmkModules/plog/devices" "%r/info|elevStats:./%s/info[deviceUUID]"

            # "plogDataUsage",
            # "plogMDDataUsage",

            # "elevUnthrottleThresh",
            # "timeToSleepMs",
            # "plogNumFreedLogs",
            # "plogNumWriteLogs",
            # "elevStartThresh",
            # "plogNumCommitLogs",
            # "plogNumFreedCommitLogs",

            # "elevRuns",

            # "numMDWrites",
            # "numRCReads",
            # "numMDReads",
            # "numVMFSReads",
            # "numReads",
            # "numElevSSDReads",
            # "numSSDReads"

   labels = {'disk_uuid': entity}
   metrics = dict([(k.replace('elevStats/', ''), v) for k, v in metrics.items()])

   phelp(out, 'vmware_vsan_plog_elev_bytes_total', 'Total bytes of PLOG elevator', node1, node2)
   phelp(out, 'vmware_vsan_plog_elev_thresholds_ratio', 'Utilization metrics for write buffer of PLOG elevator', node1, node2)

   for key in ['CS', 'FS', 'Zero', 'FSUnmap', 'Del', 'CF']:
      # XXX: Better name?
      ioLabels = labels.copy()
      ioLabels['io_type'] = key
      rec(out, 'vmware_vsan_plog_elev_bytes_total', metrics['total%sBytes' % key], ioLabels)

   for key in ['RC', 'VMFS']:
      # XXX: Better name?
      ioLabels = labels.copy()
      ioLabels['io_type'] = key
      rec(out, 'vmware_vsan_plog_elev_bytes_total', metrics['totalBytesReadBy%s' % key], ioLabels)

   for key in ['mem', 'data', 'ssd', 'max', 'zero', 'log']:
      ioLabels = labels.copy()
      ioLabels['threshold_type'] = key
      rec(out, 'vmware_vsan_plog_elev_thresholds_ratio', metrics['%sP' % key] / 100.0, ioLabels)

def plogDevicesDedupStats(out, node1, node2, entity, metrics):
   # "/vmkModules/plog/devices" "%r/info|dedupStats:./%s/info[deviceUUID]"

   labels = {'disk_uuid': entity}
   metrics = dict([(k.replace('dedupStats/', ''), v) for k, v in metrics.items()])

   phelp(out, 'vmware_vsan_plog_dedup_seconds_total', 'Total seconds of PLOG deduplication', node1, node2)
   phelp(out, 'vmware_vsan_plog_dedup_bytes_total', 'Total bytes of PLOG deduplication', node1, node2)
   phelp(out, 'vmware_vsan_plog_dedup_io_total', 'Total IOs of PLOG deduplication', node1, node2)
   phelp(out, 'vmware_vsan_plog_dedup_events_total', 'Total events of PLOG deduplication', node1, node2)

   for key in ["txnReplayHashmap",
            "txnBuild",
            "hashCalc",
            "txnReplay",
            "compression",
            "txnReplayBitmap",
            "dataWrite",
            "txnReplayXmap",
            "txnWrite"]:
      ioLabels = labels.copy()
      ioLabels['io_type'] = key
      rec(out, "vmware_vsan_plog_dedup_seconds_total", metrics['%sTime' % key] / 1000.0**3, ioLabels)

   for key in [
            "deduped",
            "compressed",
            "total",
            "free",
            "hashed"]:
      ioLabels = labels.copy()
      ioLabels['io_type'] = key
      rec(out, "vmware_vsan_plog_dedup_bytes_total", metrics['%sBytes' % key], ioLabels)

   for key in [
            "txnReplayBgWriteIOs",
            "txnReplayFgWriteIOs",
            "numHashmapReads",
            "numBitmapWrites",
            "numXMapReads",
            "numBitmapReads",
            "numHashmapWrites",
            "numXMapWrites",
            "txnWrites"]:
      ioLabels = labels.copy()
      ioLabels['io_type'] = key
      rec(out, "vmware_vsan_plog_dedup_io_total", metrics['%s' % key], ioLabels)

   for key in [
            "cacheMissesBmap",
            "cacheMissesXmap",
            "cacheMissesHmap",
            "cacheHitsBmap",
            "cacheHitsXmap",
            "cacheHitsHmap",
            "pendingTxnReplayYields",
            "txnReplayReadIOHits"]:
      ioLabels = labels.copy()
      ioLabels['io_type'] = key
      rec(out, "vmware_vsan_plog_dedup_events_total", metrics['%s' % key], ioLabels)

# "%r/info|health/latencyStats:./%s/info[deviceUUID]" is used for DDH only, not as important

def plogDevicesRecoveryStats(out, node1, node2, entity, metrics):
   # "/vmkModules/plog/devices" "%r/info|info:./%s/info[deviceUUID]"

            # "totalRecoveryTime",
            # "recoveryProcessTime",
            # "numRecoveryReads",
            # "recoveryReadTime"

   labels = {'disk_uuid': entity}
   metrics = dict([(k.replace('info/', ''), v) for k, v in metrics.items()])

   phelp(out, 'vmware_vsan_plog_recovery_seconds_total', 'Total seconds of PLOG recovery', node1, node2)
   phelp(out, 'vmware_vsan_plog_recovery_io_total', 'Total IOs of PLOG recovery', node1, node2)

   for key in ["total"]:
      ioLabels = labels.copy()
      ioLabels['io_type'] = key.lower()
      rec(out, "vmware_vsan_plog_recovery_seconds_total", metrics['%sRecoveryTime' % key] / 1000.0**2, ioLabels)

   for key in ["Process", "Read"]:
      ioLabels = labels.copy()
      ioLabels['io_type'] = key.lower()
      rec(out, "vmware_vsan_plog_recovery_seconds_total", metrics['recovery%sTime' % key] / 1000.0**2, ioLabels)

   for key in ["Read"]:
      ioLabels = labels.copy()
      ioLabels['io_type'] = key.lower()
      rec(out, "vmware_vsan_plog_recovery_io_total", metrics['numRecovery%ss' % key], ioLabels)

# "/vmkModules/lsom/disks"
def lsomDisks(out, node1, node2, entity, metrics):
   # "%s/info"
   labels = {'disk_uuid': entity}
   metrics = dict([(k.replace('info/', ''), v) for k, v in metrics.items()])

   phelp(out, "vmware_vsan_disk_congestion_total", "vSAN Disk Group point in time congestion value (0-255). LSOM indicates how much incoming rate it can sustain, typically limited by physical disks or CPU. DOM maps it to bandwidth limit (0 is no limit, 255 is 0 MB/s) using a monotonic non-linear opaque function.", node1, node2)
   for key in ["ssd", "mem", "iops", "slab", "log", "comp"]:
      ioLabels = labels.copy()
      ioLabels['congestion_type'] = key
      rec(out, "vmware_vsan_disk_congestion_total", metrics['%sCongestion' % key], ioLabels)

   phelp(out, "vmware_vsan_disk_congestion_bytespersecond", "vSAN Disk Group point in time congestion value in Bytes/s. LSOM indicates how much incoming rate it can sustain, DOM enforces it.", node1, node2)
   for key in ["Log"]:
      ioLabels = labels.copy()
      ioLabels['congestion_type'] = key.lower()
      rec(out, "vmware_vsan_disk_congestion_bytespersecond", metrics.get('oob%sCongestionIOPS' % key, 0) * 4096, ioLabels)

   phelp(out, "vmware_vsan_disk_writebuffer_usage_bytes", "Point in time, vSAN Cache Disk write buffer consumption by various consumers", node1, node2)
   for key in ["plogLog", "plogData", "llogLog", "llogData"]:
      ioLabels = labels.copy()
      ioLabels['consumer_type'] = key.lower()
      rec(out, "vmware_vsan_disk_writebuffer_usage_bytes", metrics['%sSpace' % key], ioLabels)

   phelp(out, "vmware_vsan_disk_writebuffer_size_bytes", "vSAN Cache Disk write buffer size. Static value.", node1, node2)
   rec(out, "vmware_vsan_disk_writebuffer_size_bytes", metrics['wbSize'], labels)

   # Caacity related metrics
   phelp(out, "vmware_vsan_disk_capacity_bytes", "Point in time, vSAN Capacity Disk logical capacity (up to 10x inflated in dedup case)", node1, node2)
   rec(out, "vmware_vsan_disk_capacity_bytes", metrics['capacity'], labels)
   phelp(out, "vmware_vsan_disk_capacity_used_bytes", "Point in time, vSAN Capacity Disk logical capacity used.", node1, node2)
   rec(out, "vmware_vsan_disk_capacity_used_bytes", metrics['capacityUsed'], labels)
   phelp(out, "vmware_vsan_disk_capacity_reserved_bytes", "Point in time, vSAN Capacity Disk logical capacity reserved.", node1, node2)
   rec(out, "vmware_vsan_disk_capacity_reserved_bytes", metrics['capacityReserved'], labels)

   phelp(out, "vmware_vsan_disk_phys_capacity_bytes", "Point in time, vSAN Capacity Disk physical capacity (after dedup if enabled)", node1, node2)
   rec(out, "vmware_vsan_disk_phys_capacity_bytes", metrics['physDiskCapacity'], labels)
   phelp(out, "vmware_vsan_disk_phys_capacity_used_bytes", "Point in time, vSAN Capacity Disk physical capacity used (after dedup if enabled).", node1, node2)
   rec(out, "vmware_vsan_disk_phys_capacity_used_bytes", metrics['physDiskCapacityUsed'], labels)
   phelp(out, "vmware_vsan_disk_phys_capacity_reserved_bytes", "Point in time, vSAN Capacity Disk physical capacity reserved.", node1, node2)
   rec(out, "vmware_vsan_disk_phys_capacity_reserved_bytes", metrics['physCapacityReserved'], labels)
   phelp(out, "vmware_vsan_disk_phys_capacity_pending_bytes", "Point in time, vSAN Capacity Disk physical capacity Pending (XXX What does it mean?).", node1, node2)
   rec(out, "vmware_vsan_disk_phys_capacity_pending_bytes", metrics['physCapacityPending'], labels)
   phelp(out, "vmware_vsan_disk_phys_capacity_unreservedused_bytes", "Point in time, vSAN Capacity Disk physical capacity UnreservedUsed (XXX What does it mean?).", node1, node2)
   rec(out, "vmware_vsan_disk_phys_capacity_unreservedused_bytes", metrics['physCapacityUnreservedUsed'], labels)

   # XXX: Below metrics are not converted yet ...
      #       "fsMetadataSize",
      #       "conservativePrep",
      #       "unreservedUsage",

      #       "rcSize",
      #       "wbSize",

      #       "reservedOverwrittenEstSinceLastScan",
      #       "reservedWrittenAtLastScan",

      #       "conservativeUsage",
      #       "conservativeUnmap",



      #       "plogCurrSegNo",
      #       "plogStartSegNo",
      #       "llogStartSegNo",
      #       "llogCurrSegNo",

      # XXX: Related to new log congestion, LSOM 1.5 metrics
      #       "currentTrueWBFillRate",
      #       "currentIncomingRate",
      #       "overWriteFactorMovingAvg",
      #       "oobBw",
      #       "drainRateMovingAvg",
      #       "currentDrainRate",
      #       "currentOverWriteFactor",


      #       "recoveryProcessTime",
      #       "recoveryReadTime",
      #       "totalRecoveryTime",
      #       "numRecoveryReads",

      #       "type",

      #       "nrOutstandingRecovWriteOps",
      #       "nrOutstandingRecovIoSize",
      #       "nrOutstandingWriteOps",
      #       "nrOutstandingIoSize",

      # We don't really want precomputed averages
      #       "avgUnmapLatency",
      #       "avgReadLatency",
      #       "avgUnmapTPut",
      #       "avgReadIOPS",
      #       "avgReadTPut",
      #       "avgWriteTPut",
      #       "avgWriteIOPS",
      #       "avgUnmapIOPS",
      #       "avgWriteLatency",

      # XXX: What are these?
      #       "aggStats/writeLeIoTime",
      #       "aggStats/quotaEvictions",
      #       "aggStats/plogCbSlotNotFound",
      #       "aggStats/rar",
      #       "aggStats/readIoTime",
      #       "aggStats/partialMiss",
      #       "aggStats/bytesRead",
      #       "aggStats/rarMem",
      #       "aggStats/wastedPatchedBytes"
      #       "aggStats/rarRCSsd",
      #       "aggStats/payloadIoTime",
      #       "aggStats/unmapLeIoTime",
      #       "aggStats/warEvictions",
      #       "aggStats/readIoCount",
      #       "aggStats/patchedBytes",
      #       "aggStats/bytesWritten",
      #       "aggStats/rawar",
      #       "aggStats/writeIoTime",
      #       "aggStats/rawarBytes",
      #       "aggStats/plogCbBitNotSet",
      #       "aggStats/unmapLeIoCount",
      #       "aggStats/writeLeIoCount",
      #       "aggStats/payloadIoCount",
      #       "aggStats/miss",
      #       "aggStats/writeIoCount",
      #       "aggStats/plogCbInvalidated",
      #       "aggStats/writeLeDataBytes",
      #       "aggStats/payloadDataBytes",
      #       "aggStats/unmapLeDataBytes",
      #       "aggStats/memcacheEvictions",
      #       "aggStats/plogCbPatched",

def lsomDisksCfStats(node1, node2, entity, metrics):
      # "/vmkModules/lsom/disks/%s/CFStats":{
      #    "metrics":[
      #       "extentsProcessed",
      #       "totalVirstoBarrierTime",
      #       "numCFActivations",
      #       "numPLOGIOs",
      #       "unmapBytes",
      #       "totalExtentSizeProcessed",
      #       "componentsToFlush",
      #       "numVirstoBarriers",
      #       "numCksumFlushes",
      #       "totalCFTime",
      #       "totalCksumFlushTime",
      #       "totalPLOGIOTime"
      #    ],
      pass

def lsomDisksVirstoStats(node1, node2, entity, metrics):
      # "/vmkModules/lsom/disks/%s/virstoStats":{
      #    "metrics":[
      #       "mfTotalMetadata",
      #       "mbDirty",
      #       "mbFree",
      #       "mbValid",
      #       "mbcMisses",
      #       "mbcHits",
      #       "heapUtilization",
      #       "mbInvalid",
      #       "mbcEvictions",
      #       "mfRuns",
      #       "mfPendingMetadata"
      pass

def lsomDisksChecksumStats(node1, node2, entity, metrics):
      # "/vmkModules/lsom/disks/%s/checksumErrors":{
      #    "metrics":[
      #       "total"
      pass

def lsomDisksBlkattrStats(out, node1, node2, entity, metrics):
   # "/vmkModules/lsom/disks/%s/blkattrInfo":{
   #    "metrics":[

   labels = {'disk_uuid': entity}
   metrics = dict([(k.replace('info/', ''), v) for k, v in metrics.items()])

   phelp(out, "vmware_vsan_disk_blkattrcache_size_bytes", "vSAN Disk Group blkattr memory cache size.", node1, node2)
   rec(out, "vmware_vsan_disk_blkattrcache_size_bytes", metrics['cacheSize'] * 1024**2, labels)

   phelp(out, "vmware_vsan_disk_blkattrcache_hits_count", "vSAN Disk Group blkattr memory cache hits (number).", node1, node2)
   rec(out, "vmware_vsan_disk_blkattrcache_hits_count", metrics['cacheHits'], labels)

   phelp(out, "vmware_vsan_disk_blkattrcache_misses_count", "vSAN Disk Group blkattr memory cache misses (number).", node1, node2)
   rec(out, "vmware_vsan_disk_blkattrcache_misses_count", metrics['cacheMisses'], labels)

def plogPsaStats(out, node1, node2, entity, metrics):
   # "/storage/scsifw/devices/%r/info|stats:/vmkModules/plog/devices/%s/info[deviceUUID]"

   # DAvg: (issueTime + queueTime - layerTime) / (readOps + writeOps)
   # GAvg: (totalTime) / (readOps + writeOps)

   metrics = dict([(k.replace('info/', '').replace('latency/', '').replace('stats/', ''), v) for k, v in metrics.items()])
   labels = {'disk_uuid': entity}

   blkSize = metrics["capacity/blockSize"]

   phelp(out, 'vmware_vsan_disks_dev_io_total', 'Total IOs processed by ESX device layer since boot.', node1, node2)
   phelp(out, 'vmware_vsan_disks_dev_bytes_total', 'Total Bytes processed by ESX device layer since boot.', node1, node2)
   phelp(out, 'vmware_vsan_disks_dev_duration_seconds_total', 'Total seconds of IO processing time by ESX device layer since boot.', node1, node2)

   for key in ["Write", "Read"]:
      ioLabels = labels.copy()
      ioLabels['io_type'] = key.lower()
      rec(out, "vmware_vsan_disks_dev_io_total", metrics['%sOps' % key.lower()], ioLabels)
      bKey = "Written" if key == "Write" else key
      rec(out, "vmware_vsan_disks_dev_bytes_total", metrics['blocks%s' % bKey] * blkSize, ioLabels)
      bKey = "Writes" if key == "Write" else "Reads"
      rec(out, "vmware_vsan_disks_dev_duration_seconds_total", metrics['totalTime%s' % bKey] / 1024.0**2, ioLabels)

   # XXX: Document the span types ...
   phelp(out, 'vmware_vsan_disks_dev_duration_breakdown_seconds_total', 'Total seconds of IO processing time (broken out into different spans/scopes) by ESX device layer since boot.', node1, node2)
   for key in ['issue', 'layer', 'queue', 'total']:
      keyLabels = labels.copy()
      keyLabels['span'] = key
      rec(out, "vmware_vsan_disks_dev_duration_breakdown_seconds_total", metrics['%sTime' % key] / 1024.0**2, keyLabels)

def netStats(out, node1, node2, entity, metrics):
   # "/net/nics" "$getVsanNetworkStats"

   # XXX: This is a mess because we mix two types ...
            # "connects",
            # "rx_pkts",
            # "rxerrs",
            # "tx_pkt_discards",
            # "tcptimeoutdrops",
            # "rx_bytes",
            # "tx_pkts",
            # "halfconns",
            # "hw",
            # "iochaindrops",
            # "totalPnicPkt",
            # "totalPkt",
            # "tx_bytes",
            # "rx_pkt_discards",


   # Both:
            # "portRxpkts",
            # "portTxpkts",
            # "portTxDrops",
            # "portRxDrops",
            # "iochainRxdrops",
            # "iochainTxdrops",

   if metrics["type"] == "vnic":
            # "rexmits",
            # "sack_rexmits",
            # "rcvdupack",
            # "rcvduppack",
            # "sack_rcv_blocks",
            # "rcvoopack",
            # "sack_send_blocks",

            # "conndrops",

            # "snd_zerowin",

            # "iptotal",
            # "ip6total",
            # "iperrs",
            # "tcperrs",
            # "ip6errs",
      x = entity.split('|')
      labels = {
         'host_uuid': x[0],
         'stack': x[1],
         'vmknic': x[2],
      }

      phelp(out, 'vmware_esx_vmknic_tcppkt_total', 'Total Packets processed by ESX VMkernel NIC TCP since boot.', node1, node2)
      phelp(out, 'vmware_esx_vmknic_tcppkt_bytes_total', 'Total Bytes processed by ESX VMkernel NIC TCP since boot.', node1, node2)

      phelp(out, 'vmware_esx_vmknic_tcppkt_rcvduppack_total', 'Total received duplicate packets by ESX VMkernel NIC TCP since boot.', node1, node2)
      phelp(out, 'vmware_esx_vmknic_tcppkt_rcvdupack_total', 'Total received duplicate ACKs by ESX VMkernel NIC TCP since boot.', node1, node2)
      phelp(out, 'vmware_esx_vmknic_tcppkt_sack_rcv_blocks_total', 'Total received SACK asks for blocks by ESX VMkernel NIC TCP since boot.', node1, node2)
      phelp(out, 'vmware_esx_vmknic_tcppkt_sack_send_blocks_total', 'Total requested SACK retransmit of blocks by ESX VMkernel NIC TCP since boot.', node1, node2)
      phelp(out, 'vmware_esx_vmknic_tcppkt_sack_rexmits_total', 'Total sent SACK asks for blocks by ESX VMkernel NIC TCP since boot.', node1, node2)
      phelp(out, 'vmware_esx_vmknic_tcppkt_sndrexmitpack_total', 'Total retransmitted packets by ESX VMkernel NIC TCP since boot.', node1, node2)
      phelp(out, 'vmware_esx_vmknic_tcppkt_rcvoopack_total', 'Total received out-of-order packets by ESX VMkernel NIC TCP since boot.', node1, node2)


      for key, key2 in [("rx", 'rcv'), ("tx", 'snd')]:
         ioLabels = labels.copy()
         ioLabels['io_type'] = key
         rec(out, "vmware_esx_vmknic_tcppkt_total", metrics['tcp%spkts' % key], ioLabels)
         rec(out, "vmware_esx_vmknic_tcppkt_bytes_total", metrics['%sbyte' % key2], ioLabels)

      rec(out, "vmware_esx_vmknic_tcppkt_rcvduppack_total", metrics["rcvduppack"], labels)
      rec(out, "vmware_esx_vmknic_tcppkt_rcvdupack_total", metrics["rcvdupack"], labels)
      rec(out, "vmware_esx_vmknic_tcppkt_sack_rcv_blocks_total", metrics["sack_rcv_blocks"], labels)
      rec(out, "vmware_esx_vmknic_tcppkt_sack_send_blocks_total", metrics["sack_send_blocks"], labels)
      rec(out, "vmware_esx_vmknic_tcppkt_sack_rexmits_total", metrics["sack_rexmits"], labels)
      rec(out, "vmware_esx_vmknic_tcppkt_sndrexmitpack_total", metrics["rexmits"], labels)
      rec(out, "vmware_esx_vmknic_tcppkt_rcvoopack_total", metrics["rcvoopack"], labels)

   elif metrics["type"] == "pnic":
      x = entity.split('|')
      labels = {
         'host_uuid': x[0],
         'vmnic': x[1],
      }

      phelp(out, 'vmware_esx_pnic_pkt_total', 'Total Packets processed by ESX physical NIC since boot.', node1, node2)
      phelp(out, 'vmware_esx_pnic_pkt_bytes_total', 'Total Bytes processed by ESX physical NIC since boot.', node1, node2)


      for key in ["rx", "tx"]:
         ioLabels = labels.copy()
         ioLabels['io_type'] = key
         rec(out, "vmware_esx_pnic_pkt_total", metrics['%spkt' % key], ioLabels)
         rec(out, "vmware_esx_pnic_pkt_bytes_total", metrics['%sbytes' % key], ioLabels)
         rec(out, "vmware_esx_pnic_pkt_err_total", metrics['%stoterr' % key], ioLabels)
   else:
      assert(False)

def vsanSlabStats(out, node1, node2, entity, metrics):
   # "/vmkModules/vsanutil/slabs" "$getSlabInformation"

   hostUuid, slabName = entity.split("|", 2)
   labels = {"subsystem": "system", "host_uuid": hostUuid}
   slabNameLow = slabName.lower()
   if 'dom' in slabName:
      labels['subsystem'] = "DOM"
   elif 'cmmds' in slabNameLow:
      labels['subsystem'] = "CMMDS"
   elif 'virsto' in slabName or 'LSOM' in slabName or "PLOG" in slabName or 'SSDLOG' in slabName:
      labels['subsystem'] = "LSOM"
   elif 'RcSsd' in slabName or 'BL_' in slabName or 'ioretry' in slabNameLow or 'RCInv' in slabName:
      labels['subsystem'] = "LSOM"
   elif 'vsanbase' in slabName or 'vsanutil' in slabName:
      labels['subsystem'] = "VSAN"
   elif 'vsansparse' in slabNameLow:
      labels['subsystem'] = "VSANSparse"
   elif 'RDT' in slabName:
      labels['subsystem'] = "RDT"
   labels['slab'] = slabName

   phelp(out, "vmware_esx_slab_alloc_count", "Point in time. Number of objects allocated/used. For some being full is normal, others may impact control or IO operations", node1, node2)
   phelp(out, "vmware_esx_slab_max_count", "Point in time. Total number of objects in the slab that could be allocated from. For some being full is normal, others may impact control or IO operations", node1, node2)
   rec(out, "vmware_esx_slab_alloc_count", metrics['allocCount'], labels)
   rec(out, "vmware_esx_slab_max_count", metrics['maxObjs'], labels)

   # XXX: Add new alloc failures ...

def domClientCacheStats(out, node1, node2, entity, metrics):
   # "/vmkModules/vsan/dom" "clientCacheStats"
   labels = {
      'host_uuid': entity,
   }

   phelp(out, "vmware_vsan_dom_clientcache_readio_count", "Total number of Read IOs seen by vSAN DOM Client memory read cache since boot (number).", node1, node2)
   rec(out, "vmware_vsan_dom_clientcache_readio_count", metrics['lookups'], labels)

   phelp(out, "vmware_vsan_dom_clientcache_readhit_count", "Total number of cache hit Read IOs seen by vSAN DOM Client memory read cache since boot (number).", node1, node2)
   rec(out, "vmware_vsan_dom_clientcache_readhit_count", metrics['hits'], labels)

def domOriginStats(out, node1, node2, entity, metrics):
   # "/vmkModules/vsan/dom/compSchedulers": ["%s/OriginStatsPolicyChange",
   #                                         "%s/OriginStatsDecom",
   #                                         "%s/OriginStatsRebalance",
   #                                         "%s/OriginStatsFixCompliance"]
   resyncType = node2.replace('%s/OriginStats', '').lower()
   labels = {
      'disk_uuid': entity,
      'resync_type': resyncType,
   }

   rsyncTypeStr = (
      'PolicyChange: resync traffic caused by change of policy; '
      'Decom: resync traffic caused by maintenance mode and disk evacuation; '
      'Rebalance: resync traffic caused by rebalancing objects; '
      'FixCompliance: resync traffic caused by object repair.'
   )
   phelp(out, 'vmware_vsan_domdg_resync_io_total',
         'Total IOs of resync read/recovery write of PolicyChange/Decom/Rebalance/FixCompliance processed on DiskGroup. %s' % rsyncTypeStr,
         node1, node2)
   phelp(out, 'vmware_vsan_domdg_resync_io_bytes_total',
         'Total bytes of resync read/recovery write of PolicyChange/Decom/Rebalance/FixCompliance processed on DiskGroup. %s' % rsyncTypeStr,
         node1, node2)
   phelp(out, 'vmware_vsan_domdg_resync_io_duration_seconds_total',
         'Sum total of duration of IO of resync read/recovery write of PolicyChange/Decom/Rebalance/FixCompliance processed on DiskGroup. '
         'The duration is the time from the scheduler queueing to the scheduler seeing the completion of the IO. %s' % rsyncTypeStr,
         node1, node2)

   for key in ['read', 'recWrite']:
      ioLabels = labels.copy()
      ioLabels['io_type'] = key.lower()
      rec(out, 'vmware_vsan_domdg_resync_io_total', metrics['%sCount' % key], ioLabels)
      rec(out, 'vmware_vsan_domdg_resync_io_bytes_total', metrics['%sBytes' % key], ioLabels)
      rec(out, 'vmware_vsan_domdg_resync_io_duration_seconds_total', metrics['%sLatencyUs' % key] / 1000.0**2, ioLabels)

   phelp(out, 'vmware_vsan_domdg_resync_tosync_bytes_total',
         'Sum total of bytes which will resync of current active jobs of PolicyChange/Decom/Rebalance/FixCompliance on DiskGroup. %s' % rsyncTypeStr,
         node1, node2)
   rec(out, 'vmware_vsan_domdg_resync_tosync_bytes_total', metrics['sumBytesToSync'], labels)

def hostCpuStats(out, node1, node2, entity, metrics):
   # "/sched/pcpus": ["$getHostCpuInformation"],
   labels = {
      'host_uuid': entity,
   }

   phelp(out, 'vmware_host_cpu_seconds_total',
         'usedtime is a sum total of the used time of all pCPUs on host. '
         'elapsedtime is a sum total of the elapsed time of all pCPUs on host. '
         'utiltime is a sum total of the utilization time of all pCPUs on host. '
         'coreutiltime is a sum total of the utilization time of cores of all pCPUs on host.',
         node1, node2)

   for key in ['coreUtilTime', 'elapsedTime', 'usedTime', 'utilTime']:
      newLabels = labels.copy()
      newLabels['type'] = key.lower()
      rec(out, 'vmware_host_cpu_seconds_total', metrics[key] / 1000.0**3, newLabels)

def virtualSCSIStats(out, node1, node2, entity, metrics):
   # "/worldGroups": ["%v/vscsi/%v/stats/ioStats"],
   vmInstanceUuid, vscsiName = entity.split('|')
   labels = {
      'vm_instance_uuid': vmInstanceUuid,
      'vscsi_name': vscsiName,
      'objuuid': metrics.get('objUuid'),
   }
   for m in ['cns.k8s.pvc.namespace', 'cns.containerCluster.clusterId', 'cns.k8s.pv.name', 'cns.k8s.pvc.name']:
      if m in metrics:
         label = m.replace('.', '_')
         labels[label] = metrics[m]

   phelp(out, 'vmware_vsan_vscsi_io_total', 'Total IOs seen by a VSCSI controller in a VM.', node1, node2)
   phelp(out, 'vmware_vsan_vscsi_io_bytes_total', 'Total bytes seen by a VSCSI controller in a VM.', node1, node2)
   phelp(out, 'vmware_vsan_vscsi_io_duration_seconds_total', 'Sum total of duration of IO seen by a VSCSI controller in a VM.', node1, node2)

   for key in ['Read', 'Write']:
      ioLabels = labels.copy()
      ioLabels['io_type'] = key.lower()
      rec(out, 'vmware_vsan_vscsi_io_total', metrics['num%ss' % key], ioLabels)
      rec(out, 'vmware_vsan_vscsi_io_bytes_total', metrics['bytes%s' % key], ioLabels)
      rec(out, 'vmware_vsan_vscsi_io_duration_seconds_total', metrics['latency%ss' % key] / 1000.0**2, ioLabels)

def virtualDiskStats(out, node1, node2, entity, metrics):
   # "/vmkModules/vsan/dom/topclients": ["$getVirtualDiskStats"],
   labels = {
      'objpath': entity,
      'objuuid': metrics.get('objUuid'),
   }

   phelp(out, 'vmware_vsan_vdisk_normalizedio_total', 'Total normalized IOs of a virtual disk.', node1, node2)
   for key in ['Read', 'ReadDelay', 'Write', 'WriteDelay']:
      ioLabels = labels.copy()
      ioLabels['io_type'] = key.lower()
      rec(out, "vmware_vsan_vdisk_normalizedio_total", metrics['normalized%sCount' % key], ioLabels)

   phelp(out, 'vmware_vsan_vdisk_iopslimit', 'IOPS limit number of a virtual disk.', node1, node2)
   rec(out, "vmware_vsan_vdisk_iopslimit", metrics['objIopsLimit'], labels)

# Whats missing in this file ...
   # P3:
   # "/net/nics": ["$getVsanNetworkStats"],
   # "/vmkModules/vit/targets": ["$getVsanIscsiStats"],
   # "/vmkModules/vsan/sparse" : ["iostats", "allocinfo"],
   # "/vmkModules/vsan/sparse/disks" : ["%s/iostats", "%s/allocinfo"],
   #  "/vmkModules/nfsclient/vol": ["$getNFSVolInformation"],
   # "/memory": ["$getSystemMemInformation"],
   # "/sched/globalStats": ["memLoad"],
   # "/vmkModules/lsom": ["nodeInfo"],
   # "/vsan-file-service": ["$getFileSvcStats"],
   # "/vmkModules/plog/devices": ["%r/info|health/latencyStats:./%s/info[deviceUUID]", (DDH related)

   # XXX:Need to prioritize
   # "/vmkModules/vsan/dom": ["$getVsanDistributionInfo",
   #                          "clientStatsForPerfSvc","ownerStatsForPerfSvc","compmgrStatsForPerfSvc",
   #                          "ownerResyncObjectStats",
   # "/vmkModules/cmmds_net": ["stats"],
   # "/vmkModules/cmmds": ["statistics", "workloadStats"],
   # "/clom-stats": ["$getClomFitnessStats"],
   # "/vmkModules/vsan/dom/proxyowners": ["%s/stats"],
   # "/vmkModules/vsan/dom/clients": ["$getStatsDBMetrics"],

# /vmkModules/vsan/dom -> {clientStats, ownerStats, compmgrStats}
#                      -> clientCacheStats
#                      -> ...
# {/vmkModules/vsan/dom/compReadSchedulers, /vmkModules/vsan/dom/compWriteSchedulers} -> %s/stats -> ...

paths = [
   (
      "/sched/Vcpus",
      ["$getLsomWorldInformation", "$getDomWorldInformation", "$getNicWorldInformation", "$getCmmdsWorldInformation"],
      vcpuMetrics
   ),
   (
      "/vmkModules/vsan/dom",
      ["clientStats", "ownerStats", "compmgrStats"],
      domRoleState
   ),
   (
      "/vmkModules/vsan/dom/compSchedulers",
      ["%s/stats"],
      domDgState
   ),
   (
      "/vmkModules/vsan/dom",
      ["clientCacheStats"],
      domClientCacheStats
   ),
   (
      "/vmkModules/lsom/disks",
      ["%s/info"],
      lsomDisks
   ),
   (
      "/vmkModules/lsom/disks",
      ["%s/blkattrInfo"],
      lsomDisksBlkattrStats
   ),
   (
      "/vmkModules/plog/devices",
      ["%r/info|stats:./%s/info[deviceUUID]"],
      plogDevicesStats
   ),
   (
      "/vmkModules/plog/devices",
      ["%r/info|elevStats:./%s/info[deviceUUID]"],
      plogDevicesElevStats
   ),
   (
      "/vmkModules/plog/devices",
      ["%r/info|dedupStats:./%s/info[deviceUUID]"],
      plogDevicesDedupStats
   ),
   (
      "/vmkModules/plog/devices",
      ["%r/info|info:./%s/info[deviceUUID]"],
      plogDevicesRecoveryStats
   ),
   (
      "/system/heaps",
      ["$getHeapInformation"],
      heapMetrics
   ),
   (
      "/storage/scsifw/devices",
      ["%r/info|stats:/vmkModules/plog/devices/%s/info[deviceUUID]"],
      plogPsaStats
   ),
   (
      "/vmkModules/vsanutil/slabs",
      ["$getSlabInformation"],
      vsanSlabStats
   ),
   (
      "/net/nics",
      ["$getVsanNetworkStats"],
      netStats
   ),
   (
      "/vmkModules/vsan/dom/compSchedulers",
      ["%s/OriginStatsPolicyChange", "%s/OriginStatsDecom",
       "%s/OriginStatsRebalance", "%s/OriginStatsFixCompliance"],
      domOriginStats
   ),
   (
      "/sched/pcpus",
      ["$getHostCpuInformation"],
      hostCpuStats
   ),
   (
      "/worldGroups",
      ["%v/vscsi/%v/stats/ioStats"],
      virtualSCSIStats
   ),
   (
      "/vmkModules/vsan/dom/topclients",
      ["$getVirtualDiskStats"],
      virtualDiskStats
   ),
]

def augmentLabels(labels, hostInfo):
   if 'host_uuid' not in labels:
      labels['host_uuid'] = hostInfo['host_uuid']
   if 'hostname' not in labels:
      assert(labels['host_uuid'] == hostInfo['host_uuid'])
      labels['hostname'] = hostInfo['hostname']
   if 'vsan_cluster_uuid' not in labels:
      labels['vsan_cluster_uuid'] = hostInfo['vsan_cluster_uuid']
   if 'disk_uuid' in labels and labels['disk_uuid'] in hostInfo['disks']:
      diskInfo = hostInfo['disks'][labels['disk_uuid']]
      if 'diskgroup_uuid' not in labels:
         labels['diskgroup_uuid'] = diskInfo['VSAN Disk Group UUID']
      if 'diskname' not in labels:
         labels['diskname'] = diskInfo["Device"]
      if 'disk_role' not in labels:
         labels['disk_role'] = 'capacity' if diskInfo["Is Capacity Tier"] else 'cache'


# hostInfo:
#   host_uuid: ...
#   hostname: ...
#   vsan_cluster_uuid: ...
#   disks:
#     <uuid>:
#       VSAN Disk Group UUID: ...
#       "Is Capacity Tier": ...
#       Device: ...

# Prometheus format:
# metric_name [
#  "{" label_name "=" `"` label_value `"` { "," label_name "=" `"` label_value `"` } [ "," ] "}"
# ] value [ timestamp ]
# metric_name: Uses underscore-seperated hierarchy (general to specific)
# XXX query was added to mirror generateWavefrontFormat signature, implement later
def generatePrometheusFormat(hostInfo, stats, query):
   outStr = []
   for metric, info in stats.items():
      if info['help'] is not None:
         helpStr = info['help']
         origin = info['origin']
         originStr = "%s %s" % (origin['path'], ",".join(origin['nodes']))
         helpStr = "%s [from %s]" % (helpStr, originStr)
         outStr.append("# HELP %s %s" % (metric, helpStr))
      for val, labels in info['values']:
         augmentLabels(labels, hostInfo)

         labelsStr = ",".join(['%s="%s"' % (k, v) for k, v in labels.items()])
         outStr.append("%s{%s} %f" % (metric, labelsStr, val))
      outStr.append("")
   return outStr

# source: Overrides the source tag in Wavefront format
# labels: Additional labels to be added, may override system generated ones
#         if there is a collision
# timestamp: If true, timestamp will be included for every metric
# metrics: White list of all the metrics we will return.
#
# Return:
#   dict:
#     source: sourceName
#     labels:
#       foo: bar
#     timestamp: boolean
#     metrics: [<metricName1>, <metricName2>, ...]
def _DecodeQuery(query):
   try:
      return json.loads(query)
   except:
      return {}

# Wavefront format:
# <metricName> <metricValue> [<timestamp>] source=<source> [pointTags]
# metricName: Uses dot-seperated hierarchy (general to specific)
# pointTags: An arbitrary number of key-value pairs separated by spaces: <k1>="<v1>" ... <kn>="<vn>"
# https://docs.wavefront.com/wavefront_data_format.html
def generateWavefrontFormat(hostInfo, stats, query):
   query = _DecodeQuery(query)
   source = query.get('source', None)
   tsStr = ''
   metricPrefix = query.get('metricPrefix', None)
   if query.get('timestamp', False):
      # From the docs the unit is seconds, not clear if float is supported
      # After several tests, we will use float type now.
      tsStr = '%.3f ' % time.time()
   outStr = []
   for metric, info in stats.items():
      metric = metric.replace('_', '.')
      if 'metrics' in query and metric not in query['metrics']:
         # Not the most efficient place to filter, but we aren't sure about the use case
         # to begin with, so this is easy to implement.
         continue
      full_metric = '%s.%s' %(metricPrefix, metric) if metricPrefix else metric
      for val, labels in info['values']:
         augmentLabels(labels, hostInfo)
         if 'labels' in query:
            labels.update(query['labels'])

         pointTagsStr = " ".join(['%s="%s"' % (k, v) for k, v in labels.items()])
         src = source or ('vsan-%s' % labels['host_uuid'])
         outStr.append("%s %f %s source=%s %s" % (
            full_metric, val, tsStr, src, pointTagsStr))
      outStr.append("")
   return outStr

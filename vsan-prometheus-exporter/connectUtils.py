#!/usr/bin/env python3
#
# Copyright 2020-2021 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause
#

import ssl
import atexit
import logging

from pyVim.connect import SmartConnectNoSSL, Disconnect, VimSessionOrientedStub
from pyVmomi import vim, SoapStubAdapter
import vsanmgmtObjects


def GetClusterInstance(clusterName, serviceInstance):
   content = serviceInstance.RetrieveContent()
   searchIndex = content.searchIndex
   datacenters = content.rootFolder.childEntity
   for datacenter in datacenters:
      cluster = searchIndex.FindChild(datacenter.hostFolder, clusterName)
      if cluster is not None:
         return cluster
   return None

def ConnectToVC(vchost, vcport, vcuser, vcpassword):
   si = SmartConnectNoSSL(
      host=vchost, user=vcuser,
      pwd=vcpassword, port=vcport)

   stub = VimSessionOrientedStub(si._stub,
      VimSessionOrientedStub.makeUserLoginMethod(vcuser, vcpassword))
   si = vim.ServiceInstance("ServiceInstance", stub)
   atexit.register(Disconnect, si)
   return si

def ConnectToHost(hostRef):
   hostname = hostRef.name
   stub = SoapStubAdapter(
      host=hostname,
      path='/vsan',
      version='vim.version.version9',
      sslContext=ssl._create_unverified_context())

   token = hostRef.configManager.vsanSystem.FetchVsanSharedSecret()
   return VimSessionOrientedStub(stub, _makeHostLoginMethod(hostname, token))

def _makeHostLoginMethod(hostname, token):
   def _doLogin(soapStub):
      vpm = vim.cluster.VsanPerformanceManager(
         'vsan-performance-manager', soapStub)
      if vpm.Login(token):
         logging.info('Host %s authenticated successfully', hostname)
      else:
         logging.error('Host %s failed to authenticate', hostname)
   return _doLogin


from pyVmomi.VmomiSupport import (
   CreateManagedType, Capitalize, GetVmodlType,
   LazyObject, ManagedMethod, F_OPTIONAL, F_SECRET)

## Add new managed methods to existing managed object
# This function is used to add internal methods to public pyvmomi lib
#
# @param vmodlName the VMODL name of the type
# @param methods methods of the type
def _AddManagedMethod(vmodlName, methods):
   vmodlType = GetVmodlType(vmodlName)
   for (mVmodl, mWsdl, mVersion, mParams, mResult, mPrivilege, mFaults) in methods:
      if mFaults is None:
         mFaults = []
      mName = Capitalize(mVmodl)
      isTask = False
      if mName.endswith("_Task"):
         mName = mName[:-5]
         isTask = True

      if mName in vmodlType._methodInfo:
         return

      params = tuple([LazyObject(name=p[0], typeName=p[1], version=p[2], flags=p[3],
                     privId=p[4]) for p in mParams])
      info = LazyObject(name=mName, typeName=vmodlName, wsdlName=mWsdl,
                    version=mVersion, params=params, isTask=isTask,
                    resultFlags=mResult[0], resultName=mResult[1],
                    methodResultName=mResult[2], privId=mPrivilege, faults=mFaults)
      mm = ManagedMethod(info)
      vmodlType._methodInfo[mName] = info
      setattr(vmodlType, mWsdl, mm)
      setattr(vmodlType, mName, mm)

_AddManagedMethod('vim.cluster.VsanPerformanceManager', [('login', 'VsanPerfLogin', 'vim.version.version9', (('token', 'string', 'vim.version.version9', 0, None), ), (0, 'boolean', 'boolean'), 'System.Anonymous', None)])
_AddManagedMethod('vim.host.VsanSystem', [("fetchVsanSharedSecret", "FetchVsanSharedSecret", "vim.version.version9", (), (F_SECRET, "string", "string"), "Host.Config.Storage", None)])
CreateManagedType('vim.cluster.VsanInternalStatsProvider', 'VsanInternalStatsProvider', 'vmodl.ManagedObject', 'vim.version.version9', [], [('captureInternalStats', 'CaptureInternalStats', 'vim.version.version9', (('callerNodeId', 'string', 'vim.version.version9', 0 | F_OPTIONAL, None), ('interval', 'int', 'vim.version.version9', 0 | F_OPTIONAL, None), ('verboseMode', 'boolean', 'vsan.version.version3', 0 | F_OPTIONAL, None), ), (0, 'string', 'string'), 'System.Read', None)])

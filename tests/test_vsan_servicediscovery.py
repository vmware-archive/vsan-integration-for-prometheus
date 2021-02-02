#!/usr/bin/env python3
#
# Copyright 2020 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause
#
# This is the unit test for vSAN service discovery.

import os
import unittest
from unittest.mock import patch
from testUtil import MockVsanObject
import vsanServicediscovery
import importlib

VSAN_PROVIDER = '[{"labels":{"__metrics_path__":"/vsan/metrics/host-16",' \
                '"cluster_id":"domain-c8","cluster_name":"VSAN-Cluster"},"targets":["127.0.0.1:8080"]}]'
SERVER_JSON = './servers.json'
TOKEN = 'f3209af8-9d73-4d74-a4c9-5d1f14'

class TestVsanPrometheusSetup(unittest.TestCase):
   @classmethod
   def setUpClass(cls):
      os.environ['VCENTER'] = '0.0.0.0'
      os.environ['SCHEME'] = 'https'
      os.environ['DISCOVERY_ENDPOINT'] = 'vsan/metrics/serviceDiscovery'
      os.environ['MODE'] = 'proxy'
      os.environ['CONFIG_DIR'] = SERVER_JSON
      importlib.reload(vsanServicediscovery)

      def mockRequestGet(url, verify=True, headers=None):
         assert url == 'https://0.0.0.0/vsan/metrics/serviceDiscovery'
         assert verify == False
         assert headers.get('Authorization') == 'Bearer %s' % TOKEN
         retObj = MockVsanObject(status_code='200', text=VSAN_PROVIDER)
         return retObj
      patcher = patch('requests.get', side_effect=mockRequestGet)
      patcher.start()

   @classmethod
   def tearDownClass(cls):
      patch.stopall()

   def test_getProvider(self):
      provider = vsanServicediscovery.getProviderFromServiceDiscovery(TOKEN)
      self.assertEqual(provider, VSAN_PROVIDER)
      vsanServicediscovery.updateServerList(VSAN_PROVIDER)
      self.assertTrue(os.path.exists(SERVER_JSON))
      with open(SERVER_JSON, 'r') as f:
         content = f.read()
         self.assertEqual(content, VSAN_PROVIDER)
      os.remove(SERVER_JSON)

if __name__ == '__main__':
    unittest.main()



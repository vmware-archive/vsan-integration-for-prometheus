#!/usr/bin/env python3
#
# Copyright 2020-2021 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause
#

import unittest
from unittest.mock import patch
from pyVmomi import vim
from testUtil import MockVsanConfigSystem, MockVsanObject
import vsanSetupToken

class TestVsanPrometheusSetup(unittest.TestCase):
   @classmethod
   def setUpClass(cls):
      def mockWaitTask(self):
         return 'success'
      patcher = patch('pyVim.task.WaitForTask', side_effect=mockWaitTask)
      patcher.start()

   @classmethod
   def tearDownClass(cls):
      patch.stopall()

   @patch.object(vim, 'VsanVcClusterConfigSystem')
   def test_VsanTokenSetup(self, mockConfigRet):
      mockConfigRet.return_value = MockVsanConfigSystem()
      token = vsanSetupToken.setUpMetricToken(MockVsanObject(), None)
      self.assertEqual(len(token), 30)

if __name__ == '__main__':
    unittest.main()

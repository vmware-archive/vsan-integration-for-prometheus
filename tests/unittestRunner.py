#!/usr/bin/env python3
#
# Copyright 2020-2021 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause
#
# This is the entry for running unit tests.

import os
import unittest
from testUtil import logStream

def curDir():
   curFile = os.path.realpath(__file__)
   return os.path.dirname(curFile)

def _runTestsuite(suite):
   runner = unittest.TextTestRunner(verbosity=2, stream=logStream)
   results = runner.run(suite)
   try:
      assert (len(results.failures) == 0)
      assert (len(results.errors) == 0)
   except AssertionError as ae:
      logStream.write("Failures: %s" % results.failures)
      raise ae

def runAllTestsInPath(path):
   suite = unittest.TestSuite()
   tests = unittest.TestLoader().discover(path)
   suite.addTest(tests)
   _runTestsuite(suite)

if __name__ == '__main__':
   runAllTestsInPath(curDir())
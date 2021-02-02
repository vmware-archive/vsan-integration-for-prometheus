#!/usr/bin/env python3
#
# Copyright 2020 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause
#
# This is the test util file, which defines the Mock objects of unit tests.

import logging
import sys
import os
import json
import six

def curDir():
   curFile = os.path.realpath(__file__)
   return os.path.dirname(curFile)

vsan_setup_dir = os.path.join(curDir(), '..', 'vsan-prometheus-setup')
sys.path.append(vsan_setup_dir)
servicediscovery_dir = os.path.join(curDir(), '..', 'vsan-prometheus-servicediscovery')
sys.path.append(servicediscovery_dir)

def read_test_env():
   try:
      jsonData = open(curDir() + '/test_env.json').read()
      test_env_data = json.loads(jsonData)

      for name, value in six.iteritems(test_env_data):
         os.environ[name] = value
   except:
      pass

read_test_env()

def createLogger(name, logLevel=logging.INFO):
   logHandler = logging.StreamHandler(sys.stdout)
   logHandler.setLevel(logLevel)
   logHandler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s [%(name)s] %(message)s'))

   logger = logging.getLogger(name)
   logger.setLevel(logLevel)
   logger.addHandler(logHandler)
   return logger

class StreamToLogger:
   def __init__(self, logger=logging.getLogger(), level=logging.INFO):
      self.logger = logger
      self.level = level

   def write(self, msg):
      self.logger.log(self.level, msg)

   def flush(self):
      pass
logger = createLogger("unittest_stream")
logStream = StreamToLogger(logger=logger)

class MockMoObject():
   def __init__(self, moId=None):
      self._moId = moId

class MockVsanObject(MockMoObject):
   def __init__(self, _stub=None, **kwargs):
      self._stub = _stub
      self.__dict__.update(**kwargs)

class MockTask():
   def __init__(self):
      self._moId = 'task-1'


class MockVsanConfigSystem:
   def ReconfigureEx(self, cluster, spec):
      return MockMoObject(moId='task-1')
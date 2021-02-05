#!/usr/bin/env python3
#
# Copyright 2020-2021 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause
#
# This is the unit test for generate bearer tokens.

import os
import unittest
import subprocess
from testUtil import logStream, curDir
import time
import requests

class TestVsanPrometheusE2E(unittest.TestCase):
   prometheus_token = None

   # run the shell command
   @classmethod
   def runCommand(cls, command):
      logStream.write("running command %s" % command)
      exitcode, output = subprocess.getstatusoutput(command)
      logStream.write(output)
      if exitcode != 0:
         error_message = "Error: fail to run command : %s" % command
         logStream.write(error_message)
         logStream.write(output)
         raise Exception(error_message)
      return output

   @classmethod
   def waitCommand(cls, commandHandler, command, checkHandler, finallyHandler=None, timeout=60):
      max_tries = int(timeout/5) # check every 5 seconds
      output = commandHandler(command)
      while True:
         if checkHandler(output):
            break
         else:
            time.sleep(5)
            max_tries -= 1
            output = commandHandler(command)
            if max_tries == 0:
               if finallyHandler:
                  finallyHandler()
               cls.prometheusTeardown()
               raise Exception("Cannot finish command %s within %s seconds" %(timeout))

   @classmethod
   def containerImagesPreparation(cls):
      tc = unittest.TestCase('__init__')
      repo = os.environ.get('REPO')
      tc.assertIsNotNone(repo)
      container_abbrevs = ['setup', 'operator', 'exporter', 'servicediscovery']
      for container in container_abbrevs:
         env_tag = os.environ.get('%s_TAG' % container.upper())
         tc.assertIsNotNone(env_tag)
         pull_image = 'docker pull %s/vsan-prometheus-%s:%s' % (repo, container, env_tag)
         cls.runCommand(pull_image)

   # do the perparation work and launch prometheus
   @classmethod
   def prometheusPreparation(cls):
      vCenter = os.environ.get('VCENTER')
      userName = os.environ.get('USERNAME')
      passWd = os.environ.get('PASSWD')
      cluster = os.environ.get('CLUSTER')
      repo = os.environ.get('REPO')
      setup_tag = os.environ.get('SETUP_TAG')

      tc = unittest.TestCase('__init__')
      tc.assertIsNotNone(vCenter)
      tc.assertIsNotNone(userName)
      tc.assertIsNotNone(passWd)
      tc.assertIsNotNone(cluster)
      tc.assertIsNotNone(repo)

      # --- step 1: pull container images -----#
      cls.containerImagesPreparation()

      # --- step 2: obtain the bearer token from vCenter ---#
      get_bearerToken = 'docker run %s/vsan-prometheus-setup:%s --host %s --username %s --password %s --cluster %s' % (
         repo, setup_tag, vCenter, userName, passWd, cluster)
      out = cls.runCommand(get_bearerToken)
      token = out.split('\n')[-1]
      cls.prometheus_token = token

      # --- step 3: create k8s secret and configmap ---#
      bearer_secret = 'kubectl create secret generic bearer-token-secret ' \
                      '--from-literal=bearer-token=%s --from-literal=vcenter=%s' % (token, vCenter)
      cls.runCommand(bearer_secret)
      config_map = 'kubectl create configmap grafana-dashboards --from-file=%s/../grafana-dashboard.json' % curDir()
      cls.runCommand(config_map)

      vc_secret = 'kubectl create secret generic vc-info-secret --from-literal=VCENTER=%s --from-literal=VCPORT=%s ' \
                  '--from-literal=VCUSER=%s --from-literal=VCPASSWORD=%s --from-literal=CLUSTERNAME=%s' \
                  %(vCenter, '443', userName, passWd, cluster)

      cls.runCommand(vc_secret)

   # clean the prometheus resources
   @classmethod
   def prometheusTeardown(cls):
      delete_secret = 'kubectl delete secret bearer-token-secret'
      cls.runCommand(delete_secret)
      delete_secret = 'kubectl delete secret vc-info-secret'
      cls.runCommand(delete_secret)
      delete_configmap = 'kubectl delete configmap grafana-dashboards'
      cls.runCommand(delete_configmap)

      # check k8s pods are removed
      check_pods = 'kubectl get pods'
      output_check = lambda output: 'No resources found' in output
      cls.waitCommand(cls.runCommand, check_pods, output_check)

   # check the vSAN Prometheus status
   def checkPrometheusStatus(self, prometheus_yaml, numPods=2):
      def _deleteYaml():
         delete_prometheus = 'kubectl delete -f %s' % prometheus_yaml
         TestVsanPrometheusE2E.runCommand(delete_prometheus)

      def _checkPods(output):
         pods_status = output.split('\n')
         pods_status = pods_status[1:]  # remove first line
         if len(pods_status) < numPods:
            return False
         elif False in set(['Running' in status for status in pods_status]):
            return False
         else:
            return True

      def _checkPrometheusQuery(output):
         if output.status_code != 200:
            return False
         logStream.write(output.text)
         return 'vmware_esx_heap_usage_ratio' in output.text

      run_prometheus_yaml = 'envsubst < %s | kubectl apply -f -' % prometheus_yaml
      TestVsanPrometheusE2E.runCommand(run_prometheus_yaml)

      # wait for k8s pods launched
      check_pods = 'kubectl get pods'
      TestVsanPrometheusE2E.waitCommand(TestVsanPrometheusE2E.runCommand, check_pods, _checkPods, _deleteYaml)

      hostname = TestVsanPrometheusE2E.runCommand('hostname')
      # do the prometheus query
      prometheus_query_url = 'http://%s:30001/api/v1/query?query=vmware_esx_heap_usage_ratio' % hostname
      logStream.write(prometheus_query_url)
      TestVsanPrometheusE2E.waitCommand(requests.get, prometheus_query_url, _checkPrometheusQuery, _deleteYaml)

      _deleteYaml()

   def applyExporterYaml(self, exporter_yaml):
      delete_secret = 'kubectl delete secret bearer-token-secret'
      TestVsanPrometheusE2E.runCommand(delete_secret)
      token = TestVsanPrometheusE2E.prometheus_token
      vCenter = 'exporter:8080'
      apply_secret = 'kubectl create secret generic bearer-token-secret --from-literal=bearer-token=%s ' \
                      '--from-literal=vcenter=%s --from-literal=scheme="http"' % (token, vCenter)
      TestVsanPrometheusE2E.runCommand(apply_secret)
      run_yaml = 'envsubst < %s | kubectl apply -f -' % exporter_yaml
      TestVsanPrometheusE2E.runCommand(run_yaml)


   def testPrometheusVsan70SiderCar(self):
      prometheus_yaml = '%s/../prometheus-70.yaml' % curDir()
      self.checkPrometheusStatus(prometheus_yaml, numPods=2)

   @unittest.skip("Skip it since it needs to install helm chart")
   def testPrometheusVsanOperator(self):
      prometheus_yaml = '%s/../prometheus-operator.yaml' % curDir()
      self.checkPrometheusStatus(prometheus_yaml, numPods=3)

   def testPrometheusVsanExporterSideCar(self):
      exporter_yaml = '%s/../exporter-pre70.yaml' % curDir()
      self.applyExporterYaml(exporter_yaml)

      prometheus_yaml = '%s/../prometheus-70.yaml' % curDir()
      self.checkPrometheusStatus(prometheus_yaml, numPods=3)

      delete_exporter = 'kubectl delete -f %s' % exporter_yaml
      TestVsanPrometheusE2E.runCommand(delete_exporter)

   @classmethod
   def setUpClass(cls):
      cls.prometheusPreparation()

   @classmethod
   def tearDownClass(cls):
      cls.prometheusTeardown()



if __name__ == '__main__':
    unittest.main()
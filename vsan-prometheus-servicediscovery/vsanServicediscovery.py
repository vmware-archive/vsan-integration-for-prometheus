#!/usr/bin/env python3
#
# Copyright 2020 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause
#
# this script launchs a daemon for auto updating the server list file, which consumes by the prometheus container

import hashlib
import ipaddress
import logging
import os
import requests
import sys
import tempfile
import time
import json
import signal
import socket

DISCOVERY_ENDPOINT = os.environ.get('DISCOVERY_ENDPOINT', 'vsan/metrics/serviceDiscovery')
MODE = os.environ.get('MODE', 'proxy')
if MODE != 'proxy' and MODE != 'direct':
   print("Illegal MODE %s, defaulting to proxy" % MODE)
   MODE = 'proxy'
if MODE == 'direct':
   DISCOVERY_ENDPOINT = '%s?mode=direct' % DISCOVERY_ENDPOINT
CONFIG_DIR = os.environ.get('CONFIG_DIR', '/prom-config-server/servers.json')
INTERVAL_SEC = int(os.environ.get('INTERVAL_SEC', 300))# default value is 5 minutes.
BEARER_TOKEN_FILE = os.environ.get('BEARER_TOKEN_FILE', '/etc/secret-volume/bearer-token')
VCENTER = os.environ.get('VCENTER')
SCHEME = os.environ.get('SCHEME', 'https')
CA_CERT_FILE = os.environ.get('CA_CERT_FILE', '/etc/cert-volume/ca_cert.pem')


# format the logging message
def getLog():
   handler = logging.StreamHandler(sys.stdout)
   handler.flush = sys.stdout.flush
   handler.setLevel(logging.INFO)
   handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s [%(name)s] %(message)s'))

   root = logging.getLogger()
   root.setLevel(logging.INFO)
   root.addHandler(handler)

   return root

# obtain the FQDN from ipAddress since SSL Certificate is used on FQDN
def getFQDNfromIpAddress(ipAddress):
   try:
      ipaddress.IPv4Address(ipAddress)
      hostName = list(socket.gethostbyaddr(ipAddress))[0]
      return hostName
   except:
      # not valid ip address, just return
      return ipAddress

# obtaining the host exporters list through vCenter service discovery endpoint
def getProviderFromServiceDiscovery(bearer_token):
   ca_cert_existed = os.path.exists(CA_CERT_FILE)
   security_check = SCHEME == 'https' and ca_cert_existed
   address = VCENTER
   if security_check:
      address = getFQDNfromIpAddress(VCENTER)
   vCenterServiceDiscovery = "%s://%s/%s" % (SCHEME, address, DISCOVERY_ENDPOINT)
   print(vCenterServiceDiscovery)

   bearer_token = 'Bearer %s' % bearer_token
   headers = {"Authorization": bearer_token}

   if security_check:
      res = requests.get(vCenterServiceDiscovery, verify=CA_CERT_FILE, headers=headers)
   else:
      res = requests.get(vCenterServiceDiscovery, verify=False, headers=headers)

   if res.status_code == 404:
      raise Exception("vCenter prometheus service discovery endpoint is unavaliable!")

   providers = res.text
   if not isinstance(providers, str):
      providers = providers.decode("UTF-8")
   if not providers:
      raise Exception("vCenter prometheus service discovery suffers issues!")
   return providers

# update the server list file, write to a tmp file, and do atomic file move.
def updateServerList(providers):
   # make the config directory if needed
   if not os.path.exists(os.path.dirname(CONFIG_DIR)):
      os.makedirs(os.path.dirname(CONFIG_DIR))
   # having a temporal file first, the do the atomic file moving to the default directory
   tmp = tempfile.NamedTemporaryFile(dir=os.path.dirname(CONFIG_DIR), delete=False)

   with open(tmp.name, 'w') as f:
      f.write(providers)
   # atomic operation for moving file
   try:
      os.rename(tmp.name, CONFIG_DIR)
      os.chmod(CONFIG_DIR, 0o754)  # assigning permission
   except OSError as e:
      sys.stderr.write("Cannot perform atomic file moving: %s" % str(e))

# read the bearer token file
def getBearToken():
   if os.environ.get('BEARER_TOKEN') is not None:
      return os.environ['BEARER_TOKEN']

   with open(BEARER_TOKEN_FILE, 'r') as f:
      return f.read()

# get the signal for terminating container
def terminateContainer(signum, frame):
   print('Signal handler called with signal', signum)
   sys.exit(0)

def main():
   """
   Launching the deamon for auto-updating the server list.
   """

   log = getLog()
   serversList_hash = None
   standalone = False
   if os.environ.get('STANDALONE') is not None:
      standalone = True
   bearer_token = getBearToken()
   signal.signal(signal.SIGTERM, terminateContainer)
   while True:
      try:
         # We retrieve the bearer token from the file every time in order to
         # be able to pick up bearer token updates
         bearer_token = getBearToken()
         providers = getProviderFromServiceDiscovery(bearer_token)
         log.info(providers)
         providers_hash = hashlib.sha1(providers.encode()).hexdigest()

         if serversList_hash != providers_hash:
            serversList_hash = providers_hash
            updateServerList(providers)
      except Exception as e:
         log.error("Cannot get the provider through service discovery, detail: %s" % str(e))

      if standalone:
         with open(CONFIG_DIR, 'r') as fp:
            print(json.dumps(json.load(fp), indent=2))
         break
      time.sleep(INTERVAL_SEC)
      log.info("daemon wakes up...")


# Start program
if __name__ == "__main__":
   main()

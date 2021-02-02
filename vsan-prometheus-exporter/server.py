#!/usr/bin/env python3
#
# Copyright 2020 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause
#

import logging
from flask import Flask, request, jsonify, Response
import sys
import signal
from vsanPrometheusStats import VsanPrometheusStats


vps = VsanPrometheusStats()

def create_app():
   app = Flask(__name__)

   @app.route('/')
   def index():
      return {'msg': 'Hello'}

   @app.route('/vsan/metrics')
   @app.route('/vsan/metrics/<host>')
   def generate_vsanmetrics(host=None):
      logging.info('Requesting %s', request.path)
      is_authorized = _is_authorized(request)

      if host == 'serviceDiscovery':
         result = []
         if is_authorized:
            try:
               result = vps.serviceDiscovery(request.host)
            except:
               logging.exception('Exception in service discovery')
         else:
            logging.warning('Not authorized for service discovery')
         return jsonify(result)

      if not is_authorized:
         return {'msg': 'Not authorized'}, 401

      if host is None:
         result = vps.getStatsForAllHosts()
      else:
         result = vps.getStatsForHost(host)
      if result is None:
         return {'msg': 'Metrics not found'}, 404
      return Response(vps.generateStatsAsStream(result), mimetype='text/plain')

   def _is_authorized(request):
      headers = request.headers
      auth_str = headers.get('Authorization', '')
      token = _parse_auth_info(auth_str)
      return vps.isAuthorized(token)

   def _parse_auth_info(auth_str):
       token = None
       if not auth_str:
           return token

       try:
           auth_type, auth_info = auth_str.split(None, 1)
           auth_type = auth_type.lower()
       except ValueError:
           return token

       if auth_type == 'bearer':
           token = auth_info
       return token

   return app


# get the signal for terminating container
def terminateContainer(signum, frame):
   print('Signal handler called with signal', signum)
   sys.exit(0)

if __name__ == '__main__':
   logging.basicConfig(
      format='%(asctime)s %(levelname)-8s| %(message)s', level=logging.DEBUG)
   signal.signal(signal.SIGTERM, terminateContainer)
   app = create_app()
   app.run()

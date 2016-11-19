#!/usr/bin/env python2

from __future__ import print_function

import Cookie
import argparse
import httplib
import json
import logging
import os
import urllib
import urllib2
import urlparse
import sys

class BBoxAPI:
	def __init__ (self, logger, url, password):
		components = urllib2.urlparse.urlparse (url)

		if components[0] != 'http':
			logger.error ('URL scheme must be http://')

			sys.exit (1)

		self.cookie = None
		self.host = components[1]
		self.logger = logger
		self.path = components[2]

		response = self.query ('POST', 'login', {'password': password})
		cookie = response is not None and response.getheader ('Set-Cookie') or None

		if cookie is None:
			logger.error ('cannot authenticate to API (wrong password?)')

			sys.exit (1)

		self.cookie = Cookie.BaseCookie ()
		self.cookie.load (cookie)

	def get_bool (self, method, path, data = None):
		return self.query (method, path, data) is not None

	def get_json (self, method, path, data = None):
		response = self.query (method, path, data)

		if response is not None:
			data = response.read ()

			if data != '':
				return json.loads (data)

		return {}

	def get_str (self, method, path, data = None):
		response = self.query (method, path, data)

		if response is not None:
			return response.read ()

		return ''

	def query (self, method, path, data):
		if path.endswith ('btoken='):
			token = self.get_json ('GET', 'device/token', self.cookie).get ('token', None)

			if token is None:
				self.logger.warning ('cannot get device token')

				return {}

			path = path + token

		if data is not None:
			body = urllib.urlencode (data)
		else:
			body = None

		if self.cookie is not None:
			headers = dict ((('Cookie', name + '=' + morsel.coded_value) for (name, morsel) in self.cookie.items ()))
		else:
			headers = {}

		connection = httplib.HTTPConnection (self.host)
		connection.request (method, self.path + '/' + path, body, headers)
		response = connection.getresponse ()

		if response.status != 200:
			self.logger.warning ('call {0} {1} returned {2}'.format (method, path, response.status))

			return None

		return response

class Config:
	def __init__ (self, path):
		if os.path.isfile (path):
			with open (path, 'rb') as file:
				data = dict (json.load (file))
		else:
			data = {}

		self.password = data.get ('password', None)
		self.url = data.get ('url', 'http://192.168.1.254/api/v1')

# Setup logging facility
formatter = logging.Formatter ('%(levelname)s: %(message)s')

console = logging.StreamHandler ()
console.setFormatter (formatter)

logger = logging.getLogger ()
logger.addHandler (console)
logger.setLevel (logging.INFO)

# Load configuration and setup API
config = Config ('.bbox.config')

if config.password is None:
	logger.error ('password is not defined')

	sys.exit (1)

# Parse command line arguments and execute command
parser = argparse.ArgumentParser (description = 'Python2 CLI utility for Bouygues Telecom\'s BBox Miami Router API.')
parsers = parser.add_subparsers (help = 'API command to execute')

parser_raw = parsers.add_parser ('raw', help = 'Execute raw command')
parser_raw.add_argument ('method', action = 'store', help = 'HTTP method', metavar = 'VERB')
parser_raw.add_argument ('path', action = 'store', help = 'API command', metavar = 'PATH')
parser_raw.add_argument ('params', action = 'store', nargs = '?', type = urlparse.parse_qsl, help = 'API command arguments', metavar = 'ARGS')
parser_raw.set_defaults (func = lambda logger, api, args: print (api.get_str (args.method, args.path, args.params)))

parser_wifi_get = parsers.add_parser ('wifi:get', help = 'Get wireless status')
parser_wifi_get.add_argument ('channel', action = 'store', nargs = '?', default = '24', help = 'Channel (24 / 50)')
parser_wifi_get.set_defaults (func = lambda logger, api, args: print (api.get_json ('GET', 'wireless')[0]['wireless']['radio'][args.channel]['enable']))

parser_wifi_set = parsers.add_parser ('wifi:set', help = 'Set wireless status')
parser_wifi_set.add_argument ('enable', action = 'store', type = int, help = 'Enable (0 / 1)', metavar = 'FLAG')
parser_wifi_set.set_defaults (func = lambda logger, api, args: print (api.get_bool ('PUT', 'wireless', {'radio.enable': args.enable})))

args = parser.parse_args ()
args.func (logger, BBoxAPI (logger, config.url, config.password), args)

# XBMC modules
import xbmc
import xbmcaddon
import xbmcgui

# STANDARD library modules
import json
import os
import socket
import sys
import time
import traceback

# LAZYTV modules
import lazy_queries 			as Q
import lazy_tools   			as T
from   lazy_logger				import LazyLogger
from   lazy_settings_handler 	import LazySettingsHandler

__addon__        = xbmcaddon.Addon()
__addonid__      = __addon__.getAddonInfo('id')
__addonversion__ = tuple([int(x) for x in __addon__.getAddonInfo('version').split('.')])
__scriptPath__   = __addon__.getAddonInfo('path')
__setting__      = __addon__.getSetting
__scriptName__   = __addon__.getAddonInfo('Name')


class LazyLauncher(object):
	''' Constructs and sends a request to the service to launch some action '''

	def __init__(self):

		# GUI constructs
		self.WINDOW = xbmcgui.Window(10000)
		self.DIALOG = xbmcgui.Dialog()

		# creates the logger & translator
		keep_logs 	= True if __setting__('logging') == 'true' else False
		self.logger = LazyLogger(__addon__, __addonid__ + ' service', keep_logs)
		self.log    = self.logger.post_log
		self.lang   = self.logger.lang

		# ping the service to get the version number, if it differs, then ask if user wants to update clone
		self.address = ('localhost', 16458)
		self.sock    = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

		# check if service is available, then alert user that service needs to be restarted
		# also check if the addon is the same version as the service
		self.version_check()

		# create lazy_settings
		self.lazy_settings = LazySettingsHandler(self, __setting__, self.log, self.lang)
		
		# generate settings dictionary
		script_settings = self.lazy_settings.get_settings_dict()

		# send the request to the service
		message = {'user_called': {'settings_from_script': script_settings}}
		self.send_request(message)

		self.sock.close()

		del self.sock


	def send_request(self, message):
		''' Sends the request to the service '''

		self.log('sending message: %s' % message)

		self.sock.connect(self.address)
		json_message = json.dumps(message)

		try:
			self.sock.send(json_message)

		except Exception, e:

			self.self.log('Error connecting to lazy service: {}'.format(e))

		self.sock.close()

		self.log('message sent')


	def version_check(self):
		''' create the socket and send a ping to the service '''

		s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		s.connect(self.address)
		s.setblocking(1)
		s.settimeout(3)
		message = json.dumps({'version_request': {}})
		s.send(message)

		total_data=[]

		# give Service chance to respond
		xbmc.sleep(5)
		while True:
			try:

				# recv will block here and time out after 3 seconds
				data = s.recv(16)
				s.setblocking(0)

				# if no data then end the loop
				if not data:
					break

				self.log('data recieved')
				# otherwise append the data to the total
				total_data.append(data)

			except socket.timeout:
				s.close()
				del s
				self.log('not able to contact service')
			
				# notify the user that the service is unavailable, and ask if they want to restart it
				ans = self.DIALOG.yesno('LazyTV',self.lang(32106),self.lang(32107))

				if ans == 1:
					# this will always happen after the first install. The addon service is not auto started after install.
					xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Addons.SetAddonEnabled","id":1,"params":{"addonid":"script.lazytv","enabled":false}}')
					xbmc.sleep(7000)
					xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Addons.SetAddonEnabled","id":1,"params":{"addonid":"script.lazytv","enabled":true}}')

				sys.exit()

			except:
				self.log('unknown other error with contacting service')
				break

		s.close()

		del s
		
		raw_response = ''.join(total_data)

		if not raw_response:
			self.log('no response from service')
			sys.exit()

		response = json.loads(raw_response)

		try:
			service_version = response.get('version', 'failed')
			service_path = response.get('path','failed')

			self.log(service_version, 'service version')
			self.log(service_path, 'service_path')

		except:
			self.log('unknown error extracting service version:\n %s' % traceback.format_exc())

			sys.exit()

		self.log(__addonversion__, '__addonversion__')

		if service_version == 'failed':
			sys.exit()

		elif service_version > __addonversion__:

			self.log('clone out of date')
			clone_upd = self.DIALOG.yesno('LazyTV',self.lang(32110),self.lang(32111))

			# this section is to determine if the clone needs to be up-dated with the new version
			# it checks the clone's version against the services version.
			if clone_upd == 1:
				update_script = os.path.join(__scriptPath__,'resources','lib','lazy_clone_updater.py')
				xbmc.executebuiltin('RunScript(%s,%s,%s,%s,%s)' % (update_script, service_path, __scriptPath__, __addonid__, __scriptName__))
				sys.exit()

		return 'passed'


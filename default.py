#!/usr/bin/python
# -*- coding: utf-8 -*-

#  Copyright (C) 2013 KodeKarnage
#
#  This Program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2, or (at your option)
#  any later version.
#
#  This Program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with XBMC; see the file COPYING.  If not, write to
#  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
#  http://www.gnu.org/copyleft/gpl.html
#

# XBMC modules
import xbmcgui
import xbmc
import xbmcaddon

# STANDARD library modules
import random
import socket
import time
import datetime
import os
import ast
import json
import Queue
import pickle
import sys
sys.path.append(xbmc.translatePath(os.path.join(xbmcaddon.Addon().getAddonInfo('path'), 'resources','lib')))

# LAZYTV modules
import lazy_classes as C
import lazy_queries as Q
import lazy_tools   as T

__addon__        = xbmcaddon.Addon()
__addonid__      = __addon__.getAddonInfo('id')
__addonversion__ = tuple([int(x) for x in __addon__.getAddonInfo('version').split('.')])
__scriptPath__   = __addon__.getAddonInfo('path')
__setting__      = __addon__.getSetting
__scriptName__       = __addon__.getAddonInfo('Name')
language         = xbmc.getInfoLabel('System.Language')

# GUI constructs
WINDOW           = xbmcgui.Window(10000)
DIALOG           = xbmcgui.Dialog()

# creates the logger & translator
keep_logs = True if __setting__('logging') == 'true' else False
logger    = C.lazy_logger(__addon__, __addonid__ + ' default', keep_logs)
log       = logger.post_log
lang      = logger.lang
# log('Running: ' + str(__release__))

class main_default(object):
	''' Constructs and sends a request to the service to launch some action '''

	def __init__(self):

		# desired action
		self.service_action = ''

		# required data
		self.service_data = {}

		# create settings genie to get all the settings
		Settings_Genie = C.settings_handler(__setting__)

		# get all the settings
		self.s = Settings_Genie.get_settings_dict()

		# ping the service to get the version number, if it differs, then ask if user wants to update clone
		self.address = ('localhost', 16458)
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

		# check if service is available, then alert user that service needs to be restarted
		# also check if the addon is the same version as the service
		self.version_check()

		# playlist used for filtering
		self.playlist = 'empty'

		# allow the user to select a playlist if they wish
		if self.s['filterYN']:
			log('settings')
			log(self.s['populate_by_d'])
			log(self.s['select_pl'] )

			# populate using playlist, and select which playlist on launch
			if self.s['populate_by_d'] == 1 and self.s['select_pl'] == 0:

				log('opening playlist selection window')
				self.playlist = T.playlist_selection_window(lang)

			# populate with playlist, and use default playlist
			elif self.s['populate_by_d'] == 1 and self.s['select_pl'] == 1:
				self.playlist = self.s['users_spl', 'empty']

			# populate with the users manual selections
			else:

				log(self.s.get('selection',''))
				manual_selection = self.s.get('selection','')  # .replace('[','').replace(']','')

				# manual_selection = manual_selection.split(',')
				
		# retrieve permitted showids
		if self.s['populate_by_d'] == 0:
			self.permitted_ids = [int(x) for x in manual_selection]
		elif self.playlist != 'empty':
			self.permitted_ids = T.convert_pl_to_showlist(self.playlist)
		else:
			self.permitted_ids = 'all'

		# determine the required action
		# primary functions are 1: random_playlist, 0: lazy_gui, 2: user_choice
		self.functions = {1: 'open_random_player', 0: 'open_lazy_gui'}
		self.primary_function = self.s['primary_function']
		if self.primary_function == 2:
			self.primary_function = self.desired_action()

		# this is the desired function of the addon
		self.function = self.functions[self.primary_function]

		# bundle settings in data
		self.bundled_settings = {}

		# add the permitted ids
		self.bundled_settings['permitted_showids'] = self.permitted_ids

		# bundle up the other settings
		self.bundle_settings()

		# send the request to the service
		message = {self.function: self.bundled_settings}
		self.send_request(message)

		self.sock.close()

		del self.sock


	def desired_action(self):
		''' If needed, asks the user which action they would like to perform '''

		#assume this is selection
		choice = DIALOG.yesno('LazyTV', lang(32100),'',lang(32101), lang(32102),lang(32103))
		if choice < 0:
			sys.exit()

		return choice


	def bundle_settings(self):
		''' adds the required settings to the data bundle to be sent to the service '''

		log('bundling settings')

		if self.primary_function == 0:
			setting_keys = ['skinorno',
							'skin_return',
							'limitshows',
							'window_length',
							'sort_by',
							'sort_reverse',
							'excl_randos']
		else:
			setting_keys = ['length',
							'multipleshows',
							'premieres',
							'resume_partials',
							'start_partials',
							# 'notify',
							'playlist_notifications',
							'movies',
							'moviesw',
							'moviemid',
							'movieweight',
							'noshow']

		self.bundled_settings['settings'] = {}

		for key in setting_keys:
			self.bundled_settings['settings'][key] = self.s[key]

		log('bundling settings complete')


	def send_request(self, message):
		''' Sends the request to the service '''

		log(message, 'sending message')

		self.sock.connect(self.address)
		pickled_message = pickle.dumps(message)

		log('size of dict')

		log(sys.getsizeof(pickled_message))

		try:
			self.sock.send(pickled_message)

		except Exception, e:
			self.log('Error connecting to lazy service: {}'.format(e))

		self.sock.close()

		log('message sent')


	def version_check(self):
		''' create the socket and send a ping to the service '''

		s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		s.connect(self.address)
		s.setblocking(1)
		s.settimeout(3)
		message = pickle.dumps({'version_request': {}})
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

				log('data recieved')
				# otherwise append the data to the total
				total_data.append(data)

			except socket.timeout:
				s.close()
				del s
				log('not able to contact service')
			
				# notify the user that the service is unavailable, and ask if they want to restart it
				ans = DIALOG.yesno('LazyTV',lang(32106),lang(32107))

				if ans == 1:
					# this will always happen after the first install. The addon service is not auto started after install.
					xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Addons.SetAddonEnabled","id":1,"params":{"addonid":"script.lazytv","enabled":false}}')
					xbmc.sleep(1000)
					xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Addons.SetAddonEnabled","id":1,"params":{"addonid":"script.lazytv","enabled":true}}')

				sys.exit()

			except:
				log('unknown other error with contacting service')
				break

		s.close()
		del s
		
		raw_response = ''.join(total_data)

		if not raw_response:
			log('no response from service')
			sys.exit()

		response = pickle.loads(raw_response)

		try:
			service_version = response.keys()[0]
			service_path = response[service_version]

			log(service_version, 'service version')
			log(service_path, 'service_path')

		except:
			log('unknown error extracting service version')

			sys.exit()

		log(__addonversion__, '__addonversion__')

		if service_version > __addonversion__:

			log('clone out of date')
			clone_upd = DIALOG.yesno('LazyTV',lang(32110),lang(32111))

			# this section is to determine if the clone needs to be up-dated with the new version
			# it checks the clone's version against the services version.
			if clone_upd == 1:
				update_script = os.path.join(__scriptPath__,'resources','update_clone.py')
				xbmc.executebuiltin('RunScript(%s,%s,%s,%s,%s)' % (update_script, service_path, __scriptPath__, __addonid__, __scriptName__))
				sys.exit()

		return 'passed'

if __name__ == '__main__' :
	main_default()


'''
check if service is running 

if required, ask user about action

if required, ask user about playlist

get permitted showids

send request to SERVICE over socket

end


'open_lazy_gui'			
	# DATA {permitted_showids: [], 
	#		skinorno: number, 
	#		skin_return: bool,
	#		limit_shows: bool,
	# 		window_length: int,
	#		sort_by: int,
	#		sort_reverse: bool
	#		exclude_randos: bool}

'open_random_player'
	# DATA {








	}










'''

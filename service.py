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

'''
#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
#@@@@@@@@@@
#@@@@@@@@@@ - allow for next ep notification in LazyTV smartplaylist READY FOR TESTING
#@@@@@@@@@@ - suppress notification at start up READY FOR TESTING
#@@@@@@@@@@ - improve handling of specials
#@@@@@@@@@@ - improve refreshing of LazyTV Show Me window
#@@@@@@@@@@
#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@'''

# XBMC modules
import xbmc
import xbmcgui
import xbmcaddon

# Standard Library Modules
import os
import Queue
import time
import datetime
import ast
import json
import re
import random
import pickle
import collections
import pprint
import sys
sys.path.append(xbmc.translatePath(os.path.join(xbmcaddon.Addon().getAddonInfo('path'), 'resources','lib')))

try:
    from cStringIO import StringIO
except:
    from StringIO import StringIO


# LazyTV Modules
import lazy_classes as C
import lazy_queries as Q
import lazy_tools   as T


# This is a throwaway variable to deal with a python bug
T.datetime_bug_workaround()

# addon structure variables
__addon__               = xbmcaddon.Addon()
__addonid__             = __addon__.getAddonInfo('id')
__addonversion__        = tuple([int(x) for x in __addon__.getAddonInfo('version').split('.')])
__scriptPath__          = __addon__.getAddonInfo('path')
__profile__             = xbmc.translatePath(__addon__.getAddonInfo('profile'))
__setting__             = __addon__.getSetting
__release__			 	= T.current_KODI_version()

# creates the logger & translator
keep_logs = True if __setting__('logging') == 'true' else False
logger    = C.lazy_logger(__addon__, __addonid__ + ' service', keep_logs)
log       = logger.post_log
lang      = logger.lang
log('Running: ' + str(__release__))

# GUI constructs
WINDOW                 = xbmcgui.Window(10000)
DIALOG                 = xbmcgui.Dialog()


WINDOW.setProperty("LazyTV.Version", str(__addonversion__))
WINDOW.setProperty("LazyTV.ServicePath", str(__scriptPath__))
WINDOW.setProperty('LazyTV_service_running', 'starting')

# settings dictionary
s = {}

# localises tools
json_query = T.json_query
stringlist_to_reallist = T.stringlist_to_reallist
runtime_converter = T.runtime_converter
fix_SE = T.fix_SE


class LazyTV:

	def __init__(self):

		# show_store holds all the TV show objects
		self.show_store = {}

		# Try to load the previously saved show_store info.
		# Even though the full update will run, this will make the store_available
		# immediately on LazyTV instantiation.
		'''self.unpickle_show_store() ## will not work as changes to attributes will
			not be saved with pickle.'''

		# communication with the LazyMonitor and LazyPlayer and LazyUI
		# is handled using this queue and instructions are passed as ACTIONS
		# multiple items can be included in each ACTION
		# the queue takes a dict with the following structure,
		# { ACTION: DATA, ACTION: DATA, ...}
		self.lazy_queue = Queue.Queue()

		# communications queue for sending data to the GUI
		self.comm_queue = Queue.Queue()

		# self.lazy_queue = collections.deque()

		# create lazy_settings
		self.lazy_settings = C.settings_handler(__setting__)
		
		# generate settings dictionary
		self.s = self.lazy_settings.get_settings_dict()

		# apply the initial settings
		self.apply_settings(delta_dict = self.s, first_run = True)

		# spawns an instance of the postion_tracking_IMP, which will monitor the position
		# of playing episodes and announce when the swap_over has been triggered
		self.IMP = C.postion_tracking_IMP(self.s['trigger_postion_metric'], self.lazy_queue, log)

		# spawns an instance of the LazyPlayer
		self.LazyPlayer = C.LazyPlayer(queue = self.lazy_queue, log = log)

		# spawns an instance of the LazyMonitor
		self.LazyMonitor = C.LazyMonitor(queue = self.lazy_queue, log = log)

		# spawns the LazyComms to handle communications with the GUI
		self.LazyComms = C.LazyComms(self.lazy_queue, self.comm_queue, log)
		self.LazyComms.start()

		# show_base_info holds the id, name, lastplayed of all shows in the db
		# if nothing is found in the library, the existing show info is retained
		self.show_base_info = {}

		# create all shows and load them into the store
		self.full_library_refresh()

		# playlist playing indicates whether a playlist is playing,
		self.playlist = False

		# Tracks whether the currently playing show have been swapped. This occurs
		# when the trigger is pulled by the IMP
		self.swapped = False

		# holds the 'next episode' data temporarily
		self.temp_next_epid = False

		# ACTION dictionary
		self.action_dict = {

				'update_settings'       : self.apply_settings,
				'establish_shows'       : self.establish_shows,
				'episode_is_playing'    : self.episode_is_playing, # DATA: {allow_prev: v, showid: x, epid: y, duration: z, resume: aa}
				'player_has_stopped'    : self.player_has_stopped,
				'IMP_reports_trigger'   : self.swap_triggered,
				'manual_watched_change' : self.manual_watched_change, # DATA: epid
				'refresh_single_show'   : self.refresh_single, # DATA: self.showID
				'full_library_refresh'	: self.full_library_refresh,
				'update_smartplaylist'	: self.update_smartplaylist, # DATA {showid: False for full create, remove: False by default}
				'remove_show'			: self.remove_show, # DATA {'showid': self.showID}
				'movie_is_playing'		: self.movie_is_playing, # DATA {'movieid': movieid}
				'retrieve_add_ep'		: self.retrieve_add_ep, # DATA {'showid': x, 'epid_list': [] }
				'pass_settings_dict'	: self.pass_settings_dict, # DATA {}
				'pass_all_epitems'		: self.pass_all_epitems, # DATA {}
				'lazy_playlist_started' : self.lazy_playlist_started,
				'lazy_playlist_ended'   : self.lazy_playlist_ended,
				}

		# clear the queue, this removes noise from the initial setup
		self.lazy_queue.queue.clear()

		# create the initial smartplaylist
		self.update_smartplaylist()

		#self.pickle_show_store()

		# daemon keeps everything alive and monitors the queue for instructions
		self._dispatch_daemon()

	# DAEMON
	def _dispatch_daemon(self):
		''' Keeps everything alive, gets instructions from the queue,
			and executes them '''

		log('LazyTV daemon started')

		# Post notification that LazyTV has started
		if self.s['startup']:
			xbmc.executebuiltin('Notification(%s,%s,%i)' % ('LazyTV',lang(32173),5000))

		while not xbmc.abortRequested:

			xbmc.sleep(10)

			try:

				# if not self.lazy_queue:
				# 	continue

				instruction = self.lazy_queue.get(False)
				# instruction = self.lazy_queue.popleft()

			except Queue.Empty:

				continue

			log(instruction, 'Processing instruction: ')

			for k, v in instruction.iteritems():

				# try:
				self.action_dict[k](**v)

				# except KeyError:
				# 	log(v, 'Key not found in Action_Dict')

				# except Exception, e:

				# 	log(e, 'Error executing instruction')

			self.lazy_queue.task_done()

			log('Instruction processing complete')

		self.clear_listitems()
	
	# EXIT method
	def clear_listitems(self):
		''' clears the listitems from memory '''

		rem_list = [v.showID for k, v in self.show_store.iteritems()]

		for showid in rem_list:

			self.remove_show(showid, update_spl = False)

		self.LazyComms.stop()

		del self.LazyPlayer
		del self.LazyMonitor

	# SETTINGS method
	def apply_settings(self, delta_dict = {}, first_run = False):
		''' enacts the settings provided in delta-dict '''

		log('apply_settings reached, delta_dict: {}, first_run: {}'.format(delta_dict,first_run))

		# update the stored settings dict with the new settings
		for k, v in delta_dict.iteritems():
			self.s[k] = v

		# change the logging state 
		new_logging_state = delta_dict.get('keep_logs', '')

		if new_logging_state:
			log('changed logging state')
			logger.logging_switch(new_logging_state)

			for show in self.show_store:

				show.keep_logs = new_logging_state

		# create smartplaylist but not if firstrun
		initiate_smartplaylist = delta_dict.get('maintainsmartplaylist', '')
		
		if not first_run:
			if initiate_smartplaylist == True:

				log('update_smartplaylist called')

				self.update_smartplaylist()

		# updates the randos
		new_rando_list = delta_dict.get('randos', 'Empty')

		if new_rando_list != 'Empty':

			log(new_rando_list, 'processing new_rando_list: ')

			items = [{'object': self, 'args': {'show': show, 'new_rando_list': new_rando_list, 'current_type': show.show_type}} for show in self.show_store]

			T.func_threader(items, 'rando_change', log)


		# updates the trigger_postion_metric
		new_trigger_postion_metric = delta_dict.get('trigger_postion_metric', False)

		if new_trigger_postion_metric:
			try:
				# if the imp doesnt exist then skip this
				self.IMP.trigger_postion_metric = new_trigger_postion_metric
			except:
				pass

	# MAIN method
	def grab_all_shows(self):
		''' gets all the base show info in the library '''
		# returns a dictionary with {show_ID: {showtitle, last_played}}

		log('grab_all_shows reached')

		raw_show_ids = json_query(Q.all_show_ids)

		show_ids = raw_show_ids.get('tvshows', False)

		log(show_ids, 'show ids: ')

		for show in show_ids:
			sid = show.get('tvshowid', '')
			ttl = show.get('title', '')
			lp  = show.get('lastplayed', '')

			self.show_base_info[sid] = {'show_title': ttl, 'last_played': lp }

	# MAIN method
	def establish_shows(self):
		''' creates the show objects if it doesnt already exist,
			if it does exist, then do nothing '''

		log('establish_shows reached')

		items = [{'object': self, 'args': {'showID': k}} for k, v in self.show_base_info.iteritems()]

		T.func_threader(items, 'create_show', log)

	# MAIN method
	def create_show(self, showID):
		''' Creates the show, or merely updates the lastplayed stat if the
			show object already exists '''

		if showID not in self.show_store.keys():
			# show not found in store, so create the show now

			if showID in self.s['randos']:
				show_type = 'randos'
			else:
				show_type = 'normal'

			show_title  = self.show_base_info[showID].get('show_title','')
			last_played = self.show_base_info[showID].get('last_played','')

			if last_played:
				last_played = T.day_conv(last_played)

			log('creating show, showID: {}, \
				show_type: {}, show_title: {}, \
				last_played: {}'.format(showID, show_type, show_title, last_played))

			# this is the part that actually creates the show
			self.show_store[showID] = C.TVShow(showID, show_type, show_title, last_played, self.lazy_queue, self.s['keep_logs'])
		
		else:
			
			# if show found then update when lastplayed
			last_played = self.show_store[showID].get('last_played','')

			log(showID, 'show found, updating last played: ')

			if last_played:
				self.show_store[showID].last_played = T.day_conv(last_played)

	# SHOW method
	def full_library_refresh(self):
		''' initiates a full refresh of all shows '''

		log('full_library_refresh reached')

		# refresh the show list
		self.grab_all_shows()

		# establish any shows that are missing
		self.establish_shows()

		# conducts a refresh of each show
		[show.full_show_refresh() for k, show in self.show_store.iteritems()]

	# SHOW method
	def remove_show(self, showid, update_spl = True):
		''' the show has no episodes, so remove it from show store '''

		log(showid, 'remove_show called: ')

		if showid in self.show_store.keys():

			del self.show_store[showid].eps_store['on_deck_ep']
			del self.show_store[showid].eps_store['temp_ep']

			if update_spl:
				self.update_smartplaylist(showid = showid, remove = True)

			del self.show_store[showid]

			log('remove_show show removed')

	# SHOW method
	def refresh_single(self, showid):
		''' refreshes the data for a single show ''' 

		log(showid, 'refresh_single reached: ')

		self.show_store[showid].partial_refresh()

	# SHOW method
	def manual_watched_change(self, epid):
		''' change the watched status of a single episode '''

		log(epid, 'manual_watched_change reached: ')

		showid = self.reverse_lookup(epid)


		if showid:
			
			log(showid, 'reverse lookup returned: ')

			self.show_store[showid].update_watched_status(epid, True)

	# SHOW method
	def swap_triggered(self, showid):
		''' This process is called when the IMP announces that a show has past its trigger point.
			The boolean self.swapped is changed to the showID. '''				

		log(showid, 'swap triggered, initiated: ')

		self.show_store[showid].swap_over_ep()
		self.swapped = showid
		self.update_smartplaylist(showid)

	# SHOW method
	def rando_change(self, show, new_rando_list, current_type):
		''' Calls the partial refresh on show where
			the show type has changed '''	

		if current_type == 'randos' and show.showID not in new_rando_list:

			show.show_type = 'normal'

			show.partial_refresh()

		elif current_type != 'randos' and show.showID in new_rando_list:

			show.show_type = 'randos'

			show.partial_refresh()

	# SHOW method
	def retrieve_add_ep(self, showid, epid_list):
		''' retrieves one more episode from the supplied show '''

		show = self.show_store[showid]

		new_epid = show.find_next_ep(epid_list)

		response = {'new_epid': new_epid}

		self.comm_queue.put(response)

	# ON PLAY method
	def episode_is_playing(self, allow_prev, showid, epid, duration, resume):
		''' this process is triggered when the player notifies Main when an episode is playing '''

		log('Episode is playing: showid= {}, epid= {}, allowprev= {}'.format(showid, epid, allow_prev))

		self.swapped = False

		# start the IMP monitoring the currently playing episode
		self.IMP.begin_monitoring_episode(showid, duration)

		# create shorthand for the show
		show = self.show_store[showid]

		# update show.lastplayed attribute
		log(show.last_played, 'lastplayed updated: ')
		show.last_played = T.day_conv()

		# check for prior unwatched episodes
		self.prev_check_handler(epid, allow_prev)

		# post notifications of what is playing (DOES NOT WORK OUTSIDE OF RANDOM PLAYER)
		self.post_notification(show)

		# if in LazyTV random playlist, then resume partially watched
		self.resume_partials(resume)

		# tell show to set up the next episode to play and store it in temp_ep
		log(epid, 'tee up requested: ')
		epid_check = show.tee_up_ep(epid)

		# if epid_check returns false, there is no next show
		# record the epid for easy access by the next prompt
		self.temp_next_epid = epid if epid_check else False

	# ON PLAY method
	def movie_is_playing(self, movieid):
		''' If a movie is playing in the random player, check whether playlist is playing, 
			if so then check random resume point '''

		if self.playlist:

			playcount = xbmc.getInfoLabel('VideoPlayer.PlayCount')

			if playcount != '0': #@@@@@ GET PLAYCOUNT OF THE MOVIE, ONLY SEEK IF IT IS MORE THAN 0:

				time = T.runtime_converter(xbmc.getInfoLabel('VideoPlayer.Duration'))

				seek_point = int(100 * (time * 0.75 * ((random.randint(0,100) / 100.0) ** 2)) / time)

				Q.seek['params']['value'] = seek_point

				json_query(Q.seek, True)

	# ON PLAY method
	def post_notification(self, show):

		log('Notification Test; playlist_notifications: {}, self.playlist:: {}'.format(self.s['playlist_notifications'], self.playlist))
		if self.s['playlist_notifications'] and self.playlist:

			log('posting notification: showtitle: {}, season: {}, episode: {}'.format(show.show_title,show.Season,show.Episode))

			xbmc.executebuiltin('Notification(%s,%s S%sE%s,%i)' % (lang(32163),show.show_title,show.Season,show.Episode,5000))

	# ON PLAY method
	def resume_partials(self, resume):
		''' Jumps to a specific point in the episode. '''

		log('Resume Partials Test; resume_partials: {}, self.playlist:: {}'.format(self.s['resume_partials'], self.playlist))
		if self.s['resume_partials'] and self.playlist:

			position = resume.get('position',0)
			total = resume.get('total',0)

			if position:
				# call resume partials only if there is a resume point in the show

				seek_point = int((float(position) / float(total)) *100)
				
				seek['params']['value'] = seek_point

				log('seeking to : {}'.format(seek_point))
				T.json_query(seek, True)

	# ON PLAY method
	def prev_check_handler(self, epid, allow_prev):
		''' handles the check for the previous episode '''

		log('Prev Test; allow_prev: {}, prevcheck_setting: {}, self.playlist: {}'.format(allow_prev, self.s['prevcheck'], not self.playlist))
		if all([allow_prev, self.s['prevcheck'], not self.playlist]):

			log('prev_check_handler reached')

			showid = self.reverse_lookup(epid)

			if not showid:
				log('could not find showid')
				return

			show = self.show_store[showid]

			# retrieves tuple with showtitle, season, episode
			prev_deets = show.look_for_prev_unwatched(epid)

			if not prev_deets:

				log('no prev_deets')
				return

			pepid, showtitle, season, episode = prev_deets

			#pause, wait 500 for the thing to actually start
			xbmc.sleep(500)
			xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Player.PlayPause","params":{"playerid":1,"play":false},"id":1}')

			#show notification
			log('prev_deets, pepid: {}, showtitle: {}, season: {}, episode: {}'.format(pepid, showtitle, season, episode))
			selection = DIALOG.yesno(lang(32160), lang(32161) % (showtitle, season, episode), lang(32162))

			log(selection, 'user selection: ')

			if selection == 0:
				# unpause
				xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Player.PlayPause","params":{"playerid":1,"play":true},"id":1}')
			else:
				# stop and play previous episode
				xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Player.Stop", "params": { "playerid": 1 }, "id": 1}')
				xbmc.sleep(100)
				xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "Player.Open", "params": { "item": { "episodeid": %d }, "options":{ "resume": true }  }, "id": 1 }' % (pepid))

	# ON PLAY Method
	def lazy_playlist_started(self):
		''' Called after being notified by the GUI that the random playlist 
			has been initiated.
			Tells the imp that this is a random player playlist. The imp
			will then monitor for something to not be playing for at least 
			XX seconds before sending back notification that the random
			playlist has ended '''

		self.playlist = True

		self.IMP.begin_monitoring_lazy_playlist()

	# ON PLAY method
	def lazy_playlist_ended(self):
		''' Sets self.playlist = FALSE   '''

		self.playlist = False
	
	# ON STOP method
	def player_has_stopped(self):
		''' Triggered when the player sends notification that a video has ended '''

		log('player has stopped, function reached')

		# stops the IMP episode tracking daemon
		self.IMP.episode_active = False

		# starts the IMP playlist over tracking daemon
		if self.playlist:
			log('request sent to imp to start checking for lazy_playlist end')
			self.IMP.begin_monitoring_lazy_playlist()

		log(self.playlist,'self.playlist: ')
		log(self.s['nextprompt'], 'self.s["nextprompt"]')
		log(self.swapped, 'self.swapped')

		# checks for the next episode if the show has swapped and if it isnt in a playlist
		if all([self.s['nextprompt'], not self.playlist, self.swapped]):

			log('next prompt handler called')

			# call the next prompt handler
			self.next_prompt_handler()

		# revert swapped back to its natural state
		self.swapped        = False
		self.temp_next_epid = False

	# ON STOP method
	def next_prompt_handler(self):
		''' handles the next ep functionality '''

		log('next prompt handler reached')

		show = self.show_store[self.swapped]

		# if the show isnt in the od_episodes, then it must be:
		#		: watched already, so show ODEP
		#		: prior to the ODEP, so show ODEP
		#		: in erro, so show ODEP
		if self.temp_next_epid not in show.od_episodes:

			log('next_prompt_handler: temp epid not in show.od_episodes')

			log(self.temp_next_epid)
			log(show.od_episodes)
			log(self.show_store[self.swapped].eps_store['on_deck_ep'].epid)
			log(self.show_store[self.swapped].eps_store['temp_ep'].epid)

			next_ep = show.eps_store.get('on_deck_ep', False)

		else:

			log('next_prompt_handler: temp epid in show.od_episodes')

			log(self.temp_next_epid)
			log(show.od_episodes)
			log(self.show_store[self.swapped].eps_store['on_deck_ep'].epid)
			log(self.show_store[self.swapped].eps_store['temp_ep'].epid)


			next_ep = show.eps_store.get('temp_ep', False)

		if next_ep:

			log(next_ep, 'next_ep exists')

			pause = False

			#give the chance for the playlist to start the next item
			xbmc.sleep(750)	

			# check if another show is playing, if so then pause it
			if xbmc.getInfoLabel('VideoPlayer.TVShowTitle'):

				log('show title found, paused')

				xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Player.PlayPause","params":{"playerid":1,"play":false},"id":1}')
				pause = True
		
			# variables for the prompt
			nepid 	  = next_ep.epid
			season    = next_ep.Season
			episode   = next_ep.Episode
			showtitle = next_ep.show_title

			# show prompt
			selection = self.next_ep_prompt(showtitle, season, episode)

			log(selection, 'user selection')
			if selection == 1:
				# play next episode
				log(nepid, 'playing next ep: ')

				# clear playlist
				xbmc.executeJSONRPC('{"jsonrpc":"2.0", "method":"Playlist.Clear","params": {"playlistid": 1},"id": 1}')

				# add the episode to a playlist
				Q.add_this_ep['params']['item']['episodeid'] = int(nepid)
				
				json_query(Q.add_this_ep)

				xbmc.sleep(50)

				#begin playlist
				xbmc.Player().play(xbmc.PlayList(1))

			# unpause if paused
			if pause:
				
				log('unpausing')

				xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Player.PlayPause","params":{"playerid":1,"play":true},"id":1}')

	# ON STOP method
	def next_ep_prompt(self, showtitle, season, episode):
		''' Displays the dialog for the next prompt,
			returns 0 or 1 for dont play or play '''

		log('next_prompt dialog method reached, showtitle: {}, season: {}, episode: {}'.format(showtitle, season, episode))
		log(__release__, '__release__: ')
		# setting this to catch error without disrupting UI
		prompt = -1

		# format the season and episode
		SE = str(int(season)) + 'x' + str(int(episode))

		# if default is PLAY
		if self.s['promptdefaultaction'] == 0:
			ylabel = lang(32092) 	#"Play"
			nlabel = lang(32091)	#"Dont Play

		# if default is DONT PLAY
		elif self.s['promptdefaultaction'] == 1:
			ylabel = lang(32091)	#"Dont Play
			nlabel = lang(32092)	#"Play"

		if __release__ == 'Frodo':
			if self.s['promptduration']:
				prompt = DIALOG.select(lang(32164), [lang(32165) % self.s['promptduration'], lang(32166) % (showtitle, SE)], autoclose=int(self.s['promptduration'] * 1000))
			else:
				prompt = DIALOG.select(lang(32164), [lang(32165) % self.s['promptduration'], lang(32166) % (showtitle, SE)])

		else:
			if self.s['promptduration']:
				prompt = DIALOG.yesno(lang(32167) % self.s['promptduration'], lang(32168) % (showtitle, SE), lang(32169), yeslabel = ylabel, nolabel = nlabel, autoclose=int(self.s['promptduration'] * 1000))
			else:
				prompt = DIALOG.yesno(lang(32167) % self.s['promptduration'], lang(32168) % (showtitle, SE), lang(32169), yeslabel = ylabel, nolabel = nlabel)

		log(prompt, 'user prompt: ')

		# if the user exits, then dont play
		if prompt == -1:
			prompt = 0

		# if the default is DONT PLAY then swap the responses
		elif self.s['promptdefaultaction'] == 1:
			if prompt == 0:
				prompt = 1
			else:
				prompt = 0

		log(self.s['promptdefaultaction'], 'default action: ')
		log(prompt, 'final prompt: ')

		return prompt

	# TOOL
	def reverse_lookup(self, epid):
		''' finds the showid given a specific epid,
			the loop will break as soon as it is found '''

		log(epid, 'reverse_lookup reached: ')

		for k, show in self.show_store.iteritems():

				for ep in show.episode_list:

					if ep == epid:

						return k

		return False

	# TOOL
	def check_if_playlist(self):
		''' checks how many items are currently playing '''

		log('check_if_playlist reached')

		#FUNCTION: STILL TO DO

		pll = xbmc.getInfoLabel('VideoPlayer.PlaylistLength')

		self.playlist = True if pll != '1' else False

		log(self.playlist, 'Is playlist? ')

	# JUNK
	def empty_method(self, **kwargs):
		''' escape method '''

		pass

	# TOOL
	def update_smartplaylist(self, showid = False, remove = False):
		''' creates the smartplaylist if no showid is supplied, otherwise 
			it updates the entry for the supplied showid '''

		log('Updating Smartplaylist: showid = {}, remove= {}'.format(str(showid),str(remove)))
		return
		if self.s['maintainsmartplaylist']:

			playlist_file = os.path.join(xbmc.translatePath('special://profile/playlists/video/'),'LazyTV.xsp')

			log(playlist_file, 'playlist_file location: ')

			# tries to read the file, if it cant it creates a new file
			try:
				f = open(playlist_file, 'r')
				all_lines = f.readlines()
				f.close()
			except:
				log('no file found, creating new')
				all_lines = []

			content = []
			line1 = '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?><smartplaylist type="episodes"><name>LazyTV</name><match>one</match>\n'
			linex = '<order direction="ascending">random</order></smartplaylist>'
			rawshowline = '<!--%s--><rule field="filename" operator="is"> <value>%s</value> </rule><!--END-->\n'

			xbmc.sleep(10)

			with open(playlist_file, 'w+') as g:

				found = False

				if not showid:

					content.append(line1)

					for k, show in self.show_store.iteritems():

						showname = show.show_title
						ep = show.eps_store.get('on_deck_ep', False)

						if not ep:
							continue

						filename = str(os.path.basename(ep.File))

						content.append(rawshowline % (showname, filename))	

					content.append(linex)

				else:

					showname = self.show_store[showid].show_title
					ep = self.show_store[showid].eps_store.get('on_deck_ep', False)
					
					if ep:
						filename = os.path.basename(ep.File)
					else:
						filename = False
						found = True

					# this will only occur if the file had contents
					for num, line in enumerate(all_lines):

						# showname found in line, replacing the file
						if ''.join(["<!--",showname,"-->"]) in line:
							if filename and not remove:

								content.append(rawshowline % (showname, filename))

								found = True

						# no entry found and this is the last line, create a new entry and finish off the file
						elif found == False and line == linex and not remove:

							content.append(rawshowline % (showname, filename))
							content.append(line)

						# showname not found, not final line, so just carry it over to the new file
						else:
							content.append(line)

				# writes the new stuff to the file
				guts = ''.join(content)
				g.write(guts)
				log(content, 'finished writing file: ')

	# TOOL
	def pickle_show_store(self):
		''' Saves the show store to the addon Settings. This allows LazyTV 
			to start up very quickly. '''

		log('pickle_show_store reached')

		# pickling to file for testig only
		pickle_file = os.path.join(xbmc.translatePath('special://profile/playlists/video/'),'pickle.p')
		pickle.dump( self.show_store, open( pickle_file, "wb" ) )
		size = os.path.getsize(pickle_file)

		# create the stringIO object
		memIO = StringIO()

		# pickle the show_store into the object
		pickle.dump( self.show_store, memIO )

		# add the object to the settings
		__addon__.setSetting('pickled_show_store', memIO)

		# close out of the stringIO object
		memIO.close()

		log(size, 'show store pickled, file size: ')

	# TOOL
	def unpickle_show_store(self):
		''' Reloads the show_store for quick start-up '''

		log('unpickle_show_store reached')

		# create the stringIO object
		memIO = StringIO()

		# read the setting into the object
		pickled_tink = __setting__('pickled_show_store')

		# if the text isnt blank, then reload the show_store
		if pickled_tink: 
			memIO.write()

			self.show_store = pickle.load(memIO)

		memIO.close()

		log('unpickle_show_store complete')

	# GUI method
	def pass_settings_dict(self):
		''' Puts the settings dictionary in the comm queue
			for the gui '''

		reply = {'pass_settings_dict': self.s}

		self.comm_queue.put(reply)

	# GUI method
	def pass_all_epitems(self):
		''' Gets the on deck episodes from all shows and provides them,
			in a list. '''

		all_epitems = [show.eps_store['on_deck_ep'] for k, show in self.show_store.iteritems()]

		pprint.pprint(xbmcgui.ListItem.__dict__.keys())
		
		reply = {'pass_all_epitems': all_epitems}

		self.comm_queue.put(reply)


if ( __name__ == "__main__" ):

	log(' %s started' % str(__addonversion__))

	LazyTV()
	del LazyTV

	log(' %s stopped' % str(__addonversion__))



#@@@@@@@@@@@@@@@@@@@@@@@@@
#
#	
#	handle detection of playlist, sort out logc and settings
#	create new class for ears and tongue to handle cross process communication
#	create deque speficially for cross process communication
#	pickle show_store to settings, on service start extract pickled list first
#
#
#
#

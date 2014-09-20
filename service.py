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
import multiprocessing.connection
import sys
sys.path.append(xbmc.translatePath(os.path.join(xbmcaddon.Addon().getAddonInfo('path'), 'resources','lib')))

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
logger    = C.lazy_logger(__addon__, __addonid__, keep_logs)
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

		# communication with the LazyMonitor and LazyPlayer and LazyUI
		# is handled using this queue and instructions are passed as ACTIONS
		# multiple items can be included in each ACTION
		# the queue takes a dict with the following structure,
		# { ACTION: DATA, ACTION: DATA, ...}
		self.lazy_queue = Queue.Queue()

		# show_store holds all the TV show objects
		self.show_store = {}

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

		# spawns an instance on the LazyMonitor
		self.LazyMonitor = C.LazyMonitor(queue = self.lazy_queue, log = log)

		# show_base_info holds the id, name, lastplayed of all shows in the db
		# if nothing is found in the library, the existing show info is retained
		self.show_base_info = {}
		self.grab_all_shows()

		# create all shows and load them into the store
		self.full_library_refresh()

		# this is a reverse dictionary to aide in quickly
		# looking up the showid for a particular epid
		self.reverse_lookup = {}
		self.reverse_lookup_mechanism()

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
				'episode_is_playing'    : self.episode_is_playing, # DATA: {allow_prev: v, showid: x, epid: y, duration: z}
				'player_has_stopped'    : self.player_has_stopped,
				'IMP_reports_trigger'   : self.swap_triggered,
				'manual_watched_change' : self.manual_watched_change, # DATA: epid
				'refresh_single_show'   : self.refresh_single, # DATA: self.showID
				'full_library_refresh'	: self.full_library_refresh,
				'update_smartplaylist'	: self.update_smartplaylist, # DATA {showid: False for full create, remove: False by default}
				'remove_show'			: self.remove_show, # DATA {'showid': self.showID}
				}

		# clear the queue, this removes noise from the initial setup
		with self.lazy_queue.mutex:
			self.lazy_queue.queue.clear()

		# create the initial smartplaylist
		self.update_smartplaylist()

		# daemon keeps everything alive and monitors the queue for instructions
		self._dispatch_daemon()


	def pickle_show_store(self):
		''' Saves the show store to a file. This allows LazyTV 
			to start up very quickly. '''

		pass


	def unpickle_show_store(self):
		''' Reloads the show_store for quick start-up '''

		pass


	def remove_show(self, showid):
		''' the show has no episodes, so remove it from show store '''

		if showid in self.show_store.keys():
			del self.show_store[showid]

			self.update_smartplaylist(showid = showid, remove = True)


	def resume_partials(self):

		return

		if self.s['resume_partials'] and self.ep_details['item']['resume']['position'] > 0:
			seek_point = int((float(self.ep_details['item']['resume']['position']) / float(self.ep_details['item']['resume']['total'])) *100)
			seek['params']['value'] = seek_point
			json_query(seek, True)

		elif self.s['moviemid'] and self.ep_details['item']['playcount'] != 0:
			time = runtime_converter(xbmc.getInfoLabel('VideoPlayer.Duration'))
			seek_point = int(100 * (time * 0.75 * ((random.randint(0,100) / 100.0) ** 2)) / time)
			seek['params']['value'] = seek_point
			json_query(seek, True)


	def next_prompt_handler(self):
		''' handles the next ep functionality '''

		log('next prompt handler reached')

		show = self.show_store[self.swapped]

		# if the show isnt in the od_episodes, then it must be:
		#		: watched already, so show ODEP
		#		: prior to the ODEP, so show ODEP
		#		: in erro, so show ODEP
		if self.temp_next_epid not in show.od_episodes:

			log(self.temp_next_epid)
			log(show.od_episodes)
			log(self.show_store[self.swapped].eps_store['on_deck_ep'].epid)
			log(self.show_store[self.swapped].eps_store['temp_ep'].epid)

			next_ep = show.eps_store.get('on_deck_ep', False)

		else:

			log(self.temp_next_epid)
			log(show.od_episodes)
			log(self.show_store[self.swapped].eps_store['on_deck_ep'].epid)
			log(self.show_store[self.swapped].eps_store['temp_ep'].epid)


			next_ep = show.eps_store.get('temp_ep', False)

		if next_ep:

			pause = False

			#give the chance for the playlist to start the next item
			xbmc.sleep(200)	

			# check if another show is playing, if so then pause it
			if xbmc.getInfoLabel('VideoPlayer.TVShowTitle'):

				xbmc.executeJSONRPC(str(Q.pause))
				pause = True
		
			# variables for the prompt
			nepid 	  = next_ep.epid
			season    = next_ep.Season
			episode   = next_ep.Episode
			showtitle = next_ep.show_title

			# show prompt
			selection = self.next_ep_prompt(showtitle, season, episode)


			if selection == 1:
				# play next episode

				# clear playlist
				xbmc.executeJSONRPC(str(Q.clear_playlist))

				# add the episode to a playlist
				Q.add_this_ep['params']['item']['episodeid'] = int(nepid)
				
				json_query(Q.add_this_ep)

				xbmc.sleep(50)

				#begin playlist
				xbmc.Player().play(xbmc.PlayList(1))

			# unpause if paused
			if pause:
				xbmc.executeJSONRPC(str(Q.unpause))


	def next_ep_prompt(self, showtitle, season, episode):
		''' Displays the dialog for the next prompt,
			returns 0 or 1 for dont play or play '''

		log('next_prompt dialog method reached')

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

		# if the user exits, then dont play
		if prompt == -1:
			prompt = 0

		# if the default is DONT PLAY then swap the responses
		elif self.s['promptdefaultaction'] == 0:
			if prompt == 0:
				prompt = 1
			else:
				prompt = 0

		return prompt


	def prev_check_handler(self, epid):
		''' handles the check for the previous episode '''

		# retrieves tuple with showtitle, season, episode
		prev_deets = show.look_for_prev_unwatched(epid)

		if not prev_deets:
			return

		pepid, showtitle, season, episode = prev_deets

		#pause
		xbmc.executeJSONRPC(str(Q.pause))

		#show notification
		selection = DIALOG.yesno(lang(32160), lang(32161) % (showtitle, season, episode), lang(32162))

		if selection == 0:
			# unpause
			xbmc.executeJSONRPC(str(Q.unpause))
		else:
			# stop and play previous episode
			xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Player.Stop", "params": { "playerid": 1 }, "id": 1}')
			xbmc.sleep(100)
			xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "Player.Open", "params": { "item": { "episodeid": %d }, "options":{ "resume": true }  }, "id": 1 }' % (pepid))


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

				instruction = self.lazy_queue.get(False)

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


	def full_library_refresh(self):
		''' initiates a full refresh of all shows '''

		# refresh the show list
		self.grab_all_shows()

		# establish any shows that are missing
		self.establish_shows()

		# conducts a refresh of each show
		[show.full_show_refresh() for k, show in self.show_store.iteritems()]


	def refresh_single(self, showid):
		''' refreshes the data for a single show ''' 

		self.show_store[showid].partial_refresh()


	def manual_watched_change(self, epid):
		''' change the watched status of a single episode '''

		showid = self.reverse_lookup.get(epid, False)

		if showid:

			self.show_store[showid].update_watched_status(epid, True)


	def swap_triggered(self, showid):
		''' This process is called when the IMP announces that a show has past its trigger point.
			The boolean self.swapped is changed to the showID. '''				

		log('swap triggered, initiated')

		self.show_store[showid].swap_over_ep()
		self.swapped = showid
		self.update_smartplaylist(showid)


	def episode_is_playing(self, allow_prev, showid, epid, duration):
		''' this process is triggered when the player notifies Main when an episode is playing '''

		log('Episode is playing: showid= {}, epid= {}, allowprev= {}'.format(showid, epid, allow_prev))

		self.swapped = False

		# start the IMP monitoring the currently playing episode
		self.IMP.begin_monitoring(showid, duration)

		# create shorthand for the show
		show = self.show_store[showid]

		# update show.lastplayed attribute
		show.last_played = T.day_conv()

		# check if what is being played is in a playlist, and if it is whether that is a LazyTV playlist
		# FUNCTION: TODO return self.playlist any([not self.playlist, all([self.playlist, LAZYTV PLAYLIST]))

		# check for prior unwatched episodes
		if all([allow_prev, self.s['prevcheck'], not self.playlist]):

			self.prev_check_handler(epid)

		# post notifications of what is playing
		if self.s['playlist_notifications'] and self.playlist:

			xbmc.executebuiltin('Notification(%s,%s S%sE%s,%i)' % (lang(32163),show.show_title,show.Season,show.Episode_np,5000))

		# if in LazyTV random playlist, then resume partially watched
		# FUNCTION: Resume playlist episodes

		# tell show to set up the next episode to play and store it in temp_ep
		show.tee_up_ep(epid)

		# record the epid for easy access by the next prompt
		self.temp_next_epid = epid


	def player_has_stopped(self):
		''' Triggered when the player sends notification that a video has ended '''

		log('player has stopped, function reached')

		# stops the IMP
		self.IMP.active = False

		log(self.playlist)
		log(self.s['nextprompt_or'])
		log(self.swapped)

		# checks for the next episode if the show has swapped and if it isnt in a playlist
		if all([self.s['nextprompt'], not self.playlist, self.swapped]):

			# call the next prompt handler
			self.next_prompt_handler()

		# revert swapped back to its natural state
		self.swapped        = False
		self.temp_next_epid = False


	def reverse_lookup_mechanism(self, epid = False):
		''' constructs or adds to the reverse_lookup dict,
			if an epid is provided, the loop will break as 
			soon as it is found '''

		for k, show in self.show_store.iteritems():

				for ep in show.episode_list:

					self.reverse_lookup[ep[1]] = k

					if epid:

						return


	def check_if_playlist(self):
		''' checks how many items are currently playing '''

		#FUNCTION: STILL TO DO

		self.playlist = True


	def apply_settings(self, delta_dict = {}, first_run = False):
		''' enacts the settings provided in delta-dict '''

		# update the stored settings dict with the new settings
		for k, v in delta_dict.iteritems():
			self.s[k] = v

		# change the logging state 
		new_logging_state = delta_dict.get('keep_logs', '')

		if new_logging_state:
			logger.logging_switch(new_logging_state)

		# create smartplaylist but not if firstrun
		initiate_smartplaylist = delta_dict.get('maintainsmartplaylist', '')
		
		if not first_run:
			if initiate_smartplaylist == True:

				self.update_smartplaylist()

		# updates the randos
		new_rando_list = delta_dict.get('randos', 'Empty')

		if new_rando_list != 'Empty':

			for show in self.show_store:

				current_type = show.show_type

				if current_type == 'randos' and show.showID not in new_rando_list:

					show.show_type = 'normal'

					show.partial_refresh()

				elif current_type != 'randos' and show.showID in new_rando_list:

					show.show_type = 'randos'

					show.partial_refresh()


	def empty_method(self, **kwargs):
		''' escape method '''

		pass


	def establish_shows(self):
		''' creates the show objects if it doesnt already exist,
			if it does exist, then do nothing '''


		existing_shows = self.show_store.keys()

		for showID, v in self.show_base_info.iteritems():

			if showID not in existing_shows:

				if showID in self.s['randos']:
					show_type = 'randos'
				else:
					show_type = 'normal'

				show_title  = v.get('show_title','')
				last_played = v.get('last_played','')

				if last_played:
					last_played = T.day_conv(last_played)

				self.show_store[showID] = C.TVShow(showID, show_type, show_title, last_played, self.lazy_queue)
			
			else:
				# if show found then update when lastplayed
				last_played = v.get('last_played','')
				
				if last_played:
					self.show_store[showID].last_played = T.day_conv(last_played)


	def grab_all_shows(self):
		''' gets all the base show info in the library '''
		# returns a dictionary with {show_ID: {showtitle, last_played}}

		raw_show_ids = json_query(Q.all_show_ids)

		show_ids = raw_show_ids.get('tvshows', False)

		for show in show_ids:
			sid = show.get('tvshowid', '')
			ttl = show.get('title', '')
			lp  = show.get('lastplayed', '')

			self.show_base_info[sid] = {'show_title': ttl, 'last_played': lp }


	def update_smartplaylist(self, showid = False, remove = False):
		''' creates the smartplaylist if no showid is supplied, otherwise 
			it updates the entry for the supplied showid '''

		log('Updating Smartplaylist: showid = {}, remove= {}'.format(str(showid),str(remove)))

		if self.s['maintainsmartplaylist']:

			playlist_file = os.path.join(xbmc.translatePath('special://profile/playlists/video/'),'LazyTV.xsp')

			# tries to read the file, if it cant it creates a new file
			try:
				f = open(playlist_file, 'r')
				all_lines = f.readlines()
				f.close()
			except:
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


if ( __name__ == "__main__" ):

	log(' %s started' % str(__addonversion__))

	LazyTV()

	log(' %s stopped' % str(__addonversion__))



#@@@@@@@@@@@@@@@@@@@@@@@@@
#
#	
#	handle detection of playlist, sort out logc and settings
#	handle if the show being watched isnt the ondeck one
#	
#

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
#@@@@@@@@@@ y.  add refresh option or
#@@@@@@@@@@ y.  handle manual updates for Frodo
#@@@@@@@@@@
#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@'''


import xbmc
import xbmcgui
import xbmcaddon
import os
import time
import datetime
import ast
import json
import re
import random

# This is a throwaway variable to deal with a python bug
try:
	throwaway = datetime.datetime.strptime('20110101','%Y%m%d')
except:
	pass

__addon__              = xbmcaddon.Addon()
__addonid__            = __addon__.getAddonInfo('id')
__addonversion__       = __addon__.getAddonInfo('version')
__scriptPath__         = __addon__.getAddonInfo('path')
__profile__            = xbmc.translatePath(__addon__.getAddonInfo('profile'))
__setting__            = __addon__.getSetting
start_time             = time.time()
base_time              = time.time()
WINDOW                 = xbmcgui.Window(10000)
DIALOG = xbmcgui.Dialog()
keep_logs              = True if __setting__('logging') == 'true' else False
playlist_notifications = True if __setting__("notify")  == 'true' else False
resume_partials        = True if __setting__('resume_partials') == 'true' else False
nextprompt             = True if __setting__('nextprompt') == 'true' else False
promptduration         = int(__setting__('promptduration'))
moviemid         = True if __setting__('moviemid') == 'true' else False

versstr = xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "Application.GetProperties", "params": {"properties": ["version", "name"]}, "id": 1 }')
vers = ast.literal_eval(versstr)
if 'result' in vers and 'version' in vers['result'] and (int(vers['result']['version']['major']) > 12 or int(vers['result']['version']['major']) == 12 and int(vers['result']['version']['minor']) > 8):
	__release__            = "Gotham"
else:
	__release__            = "Frodo"

whats_playing          = {"jsonrpc": "2.0","method": "Player.GetItem","params": {"properties": ["showtitle","tvshowid","episode", "season", "playcount", "resume"],"playerid": 1},"id": "1"}
now_playing_details    = {"jsonrpc": "2.0","method": "VideoLibrary.GetEpisodeDetails","params": {"properties": ["playcount", "tvshowid"],"episodeid": "1"},"id": "1"}
ep_to_show_query       = {"jsonrpc": "2.0","method": "VideoLibrary.GetEpisodeDetails","params": {"properties": ["lastplayed","tvshowid"],"episodeid": "1"},"id": "1"}
prompt_query           = {"jsonrpc": "2.0","method": "VideoLibrary.GetEpisodeDetails","params": {"properties": ["season","episode","showtitle","tvshowid"],"episodeid": "1"},"id": "1"}
show_request           = {"jsonrpc": "2.0","method": "VideoLibrary.GetTVShows","params": {"filter": {"field": "playcount","operator": "is","value": "0"},"properties": ["genre","title","playcount","mpaa","watchedepisodes","episode","thumbnail"]},"id": "1"}
show_request_lw        = {"jsonrpc": "2.0","method": "VideoLibrary.GetTVShows","params": {"filter": {"field": "playcount", "operator": "is", "value": "0" },"properties": ["lastplayed"], "sort":{"order": "descending", "method":"lastplayed"} },"id": "1" }
eps_query              = {"jsonrpc": "2.0","method": "VideoLibrary.GetEpisodes","params": {"properties": ["season","episode","runtime","resume","playcount","tvshowid","lastplayed","file"],"tvshowid": "1"},"id": "1"}
ep_details_query       = {"jsonrpc": "2.0","method": "VideoLibrary.GetEpisodeDetails","params": {"properties": ["title","playcount","plot","season","episode","showtitle","file","lastplayed","rating","resume","art","streamdetails","firstaired","runtime","tvshowid"],"episodeid": 1},"id": "1"}
seek                   = {"jsonrpc": "2.0","id": 1, "method": "Player.Seek","params": {"playerid": 1, "value": 0 }}

def log(message, label = '', reset = False):
	if keep_logs:
		global start_time
		global base_time
		new_time     = time.time()
		gap_time     = "%5f" % (new_time - start_time)
		start_time   = new_time
		total_gap    = "%5f" % (new_time - base_time)
		logmsg       = '%s : %s :: %s ::: %s - %s ' % (__addonid__, total_gap, gap_time, label, message)
		xbmc.log(msg = logmsg)
		base_time    = start_time if reset else base_time

log(__release__)
log(xbmcaddon.Addon('xbmc.addon').getAddonInfo('version'))



def json_query(query, ret):
	try:
		xbmc_request = json.dumps(query)
		result = xbmc.executeJSONRPC(xbmc_request)
		result = unicode(result, 'utf-8', errors='ignore')
		if ret:
			return json.loads(result)['result']
		else:
			return json.loads(result)
	except:
		xbmc_request = json.dumps(query)
		result = xbmc.executeJSONRPC(xbmc_request)
		result = unicode(result, 'utf-8', errors='ignore')
		log(json.loads(result))

			#return {}

def runtime_converter(time_string):
	if time_string == '':
		return 0
	else:
		x = time_string.count(':')

		if x ==  0:
			return int(time_string)
		elif x == 2:
			h, m, s = time_string.split(':')
			return int(h) * 3600 + int(m) * 60 + int(s)
		elif x == 1:
			m, s = time_string.split(':')
			return int(m) * 60 + int(s)
		else:
			return 0

def fix_SE(string):
	if len(str(string)) == 1:
		return '0' + str(string)
	else:
		return str(string)

class LazyPlayer(xbmc.Player):
	def __init__(self, *args, **kwargs):
		xbmc.Player.__init__(self)
		LazyPlayer.np_next = False
		LazyPlayer.pl_running = 'null'
		LazyPlayer.playing_showid = False
		LazyPlayer.playing_epid = False
		LazyPlayer.npodlist = []
		LazyPlayer.nextprompt_trigger = False

	def onPlayBackStarted(self):
		log('Playbackstarted',reset=True)

		Main.target = False

		#check if an episode is playing
		self.ep_details = json_query(whats_playing, True)

		self.pl_running = WINDOW.getProperty("%s.playlist_running"	% ('LazyTV'))

		if 'item' in self.ep_details and 'type' in self.ep_details['item']:

			if self.ep_details['item']['type'] == 'episode':

				if self.pl_running == 'true' and playlist_notifications:

					episode_np = fix_SE(self.ep_details['item']['episode'])
					season_np = fix_SE(self.ep_details['item']['season'])
					showtitle = self.ep_details['item']['showtitle']

					xbmc.executebuiltin('Notification("Now Playing",%s S%sE%s,%i)' % (showtitle,season_np,episode_np,5000))

				if self.pl_running == 'true' and resume_partials:

					res_point = self.ep_details['item']['resume']
					if res_point['position'] > 0:

						seek_point = int((float(res_point['position']) / float(res_point['total'])) *100)
						seek['params']['value'] = seek_point
						json_query(seek, True)

				# this prompts Main daemon to set up the swap and prepare the prompt
				LazyPlayer.playing_epid = int(self.ep_details['item']['id'])
				LazyPlayer.playing_showid = self.ep_details['item']['tvshowid']
				log('LazyPlayer supplied showid = ' + str(LazyPlayer.playing_showid))
				log('LazyPlayer supplied epid = '+ str(LazyPlayer.playing_epid))


			elif self.ep_details['item']['type'] == 'movie' and self.pl_running == 'true' :

				if playlist_notifications:

					xbmc.executebuiltin('Notification("Now Playing",%s,%i)' % (self.ep_details['item']['label'],5000))

				if resume_partials and self.ep_details['item']['resume']['position'] > 0:
					seek_point = int((float(self.ep_details['item']['resume']['position']) / float(self.ep_details['item']['resume']['total'])) *100)
					seek['params']['value'] = seek_point
					json_query(seek, True)

				elif moviemid and self.ep_details['item']['playcount'] != 0:
					log('mid')
					time = runtime_converter(xbmc.getInfoLabel('VideoPlayer.Duration'))
					log(time)
					seek_point = int(100 * (time * 0.75 * ((random.randint(0,100) / 100.0) ** 2)) / time)
					log(seek_point)
					seek['params']['value'] = seek_point
					json_query(seek, True)

		log('Playbackstarted_End')


	def onPlayBackStopped(self):
		self.onPlayBackEnded()

	def onPlayBackEnded(self):
		log('Playbackended', reset =True)

		LazyPlayer.playing_epid = False

		xbmc.sleep(500)		#give the chance for the playlist to start the next item

		self.now_name = xbmc.getInfoLabel('VideoPlayer.TVShowTitle')
		if self.now_name == '':
			if self.pl_running == 'true':
				WINDOW.setProperty("LazyTV.playlist_running", 'false')

			if LazyPlayer.nextprompt_trigger:
				LazyPlayer.nextprompt_trigger = False
				SE = "S" + fix_SE(int(Main.nextprompt_info['season'])) + 'E' + fix_SE(int(Main.nextprompt_info['episode']))

				if __release__ == 'Frodo':
					if promptduration:
						prompt = DIALOG.select("LazyTV -the next unwatched episode is in your library.", ["No, thank you. (Autoclosing in 10 seconds)","Yes, start %s %s now." % (Main.nextprompt_info['showtitle'], SE)], autoclose=promptduration * 1000)
					else:
						prompt = DIALOG.select("LazyTV -the next unwatched episode is in your library.", ["No, thank you. (Autoclosing in 10 seconds)","Yes, start %s %s now." % (Main.nextprompt_info['showtitle'], SE)])
					if prompt == -1:
						prompt = 0
					log(prompt)
				elif __release__ == 'Gotham':
					if promptduration:
						prompt = DIALOG.yesno('LazyTV   (auto-closing in %s seconds)' % promptduration, "The next unwatched episode of %s is in your library." % Main.nextprompt_info['showtitle'], "Would you like to watch %s now?" % SE, autoclose=promptduration * 1000)
					else:
						prompt = DIALOG.yesno('LazyTV   (auto-closing in %s seconds)' % promptduration, "The next unwatched episode of %s is in your library." % Main.nextprompt_info['showtitle'], "Would you like to watch %s now?" % SE)
				else:
					prompt = False

				if prompt:
					#xbmc.executeJSONRPC('{"jsonrpc": "2.0","id": 1, "method": "Playlist.Clear",				"params": {"playlistid": 1}}')
					xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "Player.Open", "params": { "item": { "episodeid": %d }, "options":{ "resume": true }  }, "id": 1 }' % Main.nextprompt_info['episodeid'])



			Main.nextprompt_info = {}

		log('Playbackended_End')




class LazyMonitor(xbmc.Monitor):

	def __init__(self, *args, **kwargs):
		xbmc.Monitor.__init__(self)


	def onSettingsChanged(self):
		#update the settings
		grab_settings()

	def onDatabaseUpdated(self, database):
		if database == 'video':
			log('updating due to database notification')
			# update the entire list again, this is to ensure we have picked up any new shows.
			Main.onLibUpdate = True


	def onNotification(self, sender, method, data):
		#this only works for GOTHAM

		skip = False
		try:
			self.ndata = ast.literal_eval(data)
		except:
			skip = True
		if skip == True:
			pass
		elif method == 'VideoLibrary.OnUpdate':
			# Method 		VideoLibrary.OnUpdate
			# data 			{"item":{"id":1,"type":"episode"},"playcount":4}
			if 'item' in self.ndata:
				if 'playcount' in self.ndata:
					if 'type' in self.ndata['item']:
						if self.ndata['item']['type'] == 'episode':
							if self.ndata['playcount'] == 1:
								log('manual change to watched status, data = ' + str(self.ndata))
								ep_to_show_query['params']['episodeid'] = self.ndata['item']['id']
								Main.monitor_override = True
								LazyPlayer.playing_epid = self.ndata['item']['id']
								LazyPlayer.playing_showid = json_query(ep_to_show_query, True)['episodedetails']['tvshowid']
								log('monitor supplied showid - ' + str(LazyPlayer.playing_showid))
								log('monitor supplied epid - ' + str(LazyPlayer.playing_epid))

'''@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@@@@	how to distinguish between notification due to manual change and auto change
@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@'''

class Main(object):
	def __init__(self, *args, **kwargs):
		log('monitor instantiated', reset = True)

		self.initial_limit      = 10
		self.count              = 0
		Main.target             = False
		Main.nextprompt_info = {}
		Main.onLibUpdate = False
		Main.monitor_override = False
		self.nepl               = []									# the list of currently stored episodes

		self.initialisation()

		log('daemon started')
		self._daemon()			#_daemon keeps the monitor alive

	def initialisation(self):
		log('variable_init_started')
		self.Player  = LazyPlayer()							# used to post notifications on episode change
		self.Monitor = LazyMonitor(self)
		self.retrieve_all_show_ids()									# queries to get all show IDs
		WINDOW.setProperty("%s.%s" % ('LazyTV', 'daemon_message') , "null")
		WINDOW.setProperty("%s.playlist_running"	% ('LazyTV'), 'null')
		WINDOW.clearProperty('LazyTV_service_running') 			# Set a window property that let's other scripts know we are running (window properties are cleared on XBMC start)
		xbmc.sleep(110) 										#give any other instance a chance to notice that it must kill itself
		WINDOW.setProperty('LazyTV_service_running' , 'true')
		self.get_eps(showids = self.all_shows_list)				#gets the beginning list of unwatched shows
		xbmc.sleep(1000) 		# wait 5 seconds before filling the full list
		self.get_eps(showids = self.all_shows_list)
		log('variable_init_End')



	def _daemon(self):
		while not xbmc.abortRequested and WINDOW.getProperty('LazyTV_service_running') == 'true':
			xbmc.sleep(100)
			self._daemon_check()

	def _daemon_check(self):

		if Main.onLibUpdate:
			Main.onLibUpdate = False
			self.retrieve_all_show_ids()
			self.get_eps(showids = self.all_shows_list)

		# this will only show up when the Player detects a TV episode is playing
		if LazyPlayer.playing_showid:
			log('message recieved, showid = ' + str(LazyPlayer.playing_showid))
			self.sp_next = LazyPlayer.playing_showid
			# set TEMP episode
			retod = WINDOW.getProperty("%s.%s.odlist" % ('LazyTV', self.sp_next))
			log('odlist = ' + str(retod))
			self.npodlist = ast.literal_eval(retod)
			if self.npodlist:
				storedepid = int(WINDOW.getProperty("LazyTV.%s.EpisodeID" % self.sp_next))
				log('odlist exists, supplied epid = ' + str(LazyPlayer.playing_epid) + ' , vs stored ep = ' + str(storedepid))
				if LazyPlayer.playing_epid == storedepid: #if the ep is the current nextep
					log('supplied epid matches stored epid')
					self.np_next = self.npodlist[0]
					newod = [int(x) for x in self.npodlist[1:]]
					self.store_next_ep(self.np_next,'temp', newod )

					if Main.monitor_override:
						log('monitor override, swap called')
						Main.monitor_override   = False
						LazyPlayer.playing_epid = False
						Main.target             = False
						self.np_next            = False
						self.swap_over(self.sp_next)

				elif LazyPlayer.playing_epid not in self.npodlist:
					log('supplied epid not in odlist')
					self.np_next              = False
					LazyPlayer.playing_showid = False
					LazyPlayer.playing_epid   = False
				else:
					cp = self.npodlist.index(LazyPlayer.playing_epid)
					log('supplied epid in odlist at position = ' + str(cp))
					if cp != len(self.npodlist) - 1:
						self.np_next = self.npodlist[cp + 1]		#if the episode is in the list then take the next item and store in temp
						newod = [int(x) for x in self.npodlist[cp:]]
						self.store_next_ep(self.np_next,'temp', newod )
						log('supplied epid not last in list, retrieved new ep = ' + str(self.np_next))
						log('new odlist = ' + str(newod))

						if Main.monitor_override:
							log('monitor override, swap called')
							Main.monitor_override   = False
							LazyPlayer.playing_epid = False
							Main.target             = False
							self.np_next            = False
							self.swap_over(self.sp_next)

					else:
						log('supplied epid in last position in odlist, flag to remove from nepl')
						self.np_next = 'eject' 		#if the episode is the last in the list then send the message to remove the showid from nepl

			log('next ep to load = ' + str(self.np_next))
			# set NEXTPROMPT if require
			if nextprompt and self.np_next and self.np_next != 'eject':
				prompt_query['params']['episodeid'] = int(self.np_next)
				cp_details = json_query(prompt_query, True)
				log(cp_details)
				if 'episodedetails' in cp_details:
					Main.nextprompt_info = cp_details['episodedetails']

			# set the TARGET time, every tv show will have a target, some may take longer to start up
			tick = 0
			while not Main.target and tick < 20:
				Main.target = runtime_converter(xbmc.getInfoLabel('VideoPlayer.Duration')) * 0.9
				tick += 1
				xbmc.sleep(250)
			log('tick = ' + str(tick))
			log(Main.target, label='target')

			# resets the ids so this first section doesnt run again until some thing new is playing
			LazyPlayer.playing_showid = False
			# only allow the monitor override to run once
			Main.monitor_override     = False


		# check the position of the played item every 5 seconds, if it is beyond the Main.target position then trigger the pre-stop update
		if Main.target:

			self.count = (self.count + 1) % 50

			if self.count == 0: 	#check the position of the playing item every 5 seconds, if it is past the Main.target then run the swap

				if runtime_converter(xbmc.getInfoLabel('VideoPlayer.Time')) > Main.target:
					log('Main.target exceeded')
					log(self.nextprompt_info)
					if self.np_next == 'eject':
						self.remove_from_nepl(self.sp_next)
						self.sp_next = False

					if self.sp_next:
						log('swap occurred')
						self.swap_over(self.sp_next)

					if nextprompt and self.nextprompt_info:
						log('trigger set')
						LazyPlayer.nextprompt_trigger = True

					self.sp_next          = False
					self.np_next          = False
					Main.target           = False
					Main.monitor_override = False


	def remove_from_nepl(self,showid):
		if showid in self.nepl:
			self.nepl.remove(showid)
			WINDOW.setProperty("%s.nepl" % 'LazyTV', str(self.nepl))


	def retrieve_all_show_ids(self):
		log('retrieve_all_shows_started')

		self.result = json_query(show_request, True)
		if 'tvshows' not in self.result:
			self.all_shows_list = []
		else:
			self.all_shows_list = [id['tvshowid'] for id in self.result['tvshows']]
		log('retrieve_all_shows_End')


	def get_eps(self, showids = []):
		log('get_eps_started', reset =True)
		kcount = 0
		# called whenever the Next_Eps stored in 10000 need to be updated
		# determines the next ep for the showids it is sent and saves the info to 10000

		#turns single show id into a list
		self.showids    = showids if isinstance(showids, list) else [showids]

		self.lshowsR = json_query(show_request_lw, True)		#gets showids and last watched

		if 'tvshows' not in self.lshowsR:						#if 'tvshows' isnt in the result, have the list be empty so we return without doing anything
			self.show_lw = []
		else:


			self.show_lw = [[self.day_conv(x['lastplayed']) if x['lastplayed'] else 0, x['tvshowid']] for x in self.lshowsR['tvshows'] if x['tvshowid'] in self.showids]

		for show in self.show_lw:				#process the list of shows
			my_showid = show[1]
			eps_query['params']['tvshowid'] = my_showid			# creates query
			self.ep = json_query(eps_query, True)				# query grabs the TV show episodes

			if 'episodes' not in self.ep: 						#ignore show if show has no episodes
				continue
			else:
				self.eps = self.ep['episodes']

			self.last_watched    = show[0]
			played_eps           = []
			unplayed_eps_all     = []
			unplayed_eps         = []
			Season               = 1 	# these are set to 1x1 in order to ignore specials
			Episode              = 1
			watched_showcount    = 0
			self.count_ondeckeps = 0 	# will be the total number of ondeck episodes
			on_deck_epid         = ''

			_append = unplayed_eps_all.append 		#reference to avoid reevaluation on each loop

			# runs through the list and finds the watched episode with the highest season and episode numbers, and creates a list of unwatched episodes
			for ep in self.eps:
				if ep['playcount'] != 0:
					watched_showcount += 1
					if (ep['season'] == Season and ep['episode'] > Episode) or ep['season'] > Season:
						Season = ep['season']
						Episode = ep['episode']
				else:
					_append(ep)
			unplayed_eps = [x for x in unplayed_eps_all if x['season'] > Season or (x['season'] == Season and x['episode'] > Episode)]

			self.count_eps   = len(self.eps)						# the total number of episodes
			self.count_weps  = len(played_eps)						# the total number of watched episodes
			self.count_uweps = self.count_eps - self.count_weps 	# the total number of unwatched episodes


			# REPLACE THIS WITH A CHECK FOR UNWATCHED SHOWS IN QUERY
			if self.count_uweps == 0: 						# ignores show if there are no unwatched episodes
				continue


			#sorts the list of unwatched shows by lowest season and lowest episode, filters the list to remove empty strings
			ordered_eps = sorted(unplayed_eps, key = lambda unplayed_eps: (unplayed_eps['season'], unplayed_eps['episode']))
			ordered_eps = filter(None, ordered_eps)

			if not ordered_eps:							# ignores show if there is no on-deck episode
				if my_showid in self.nepl:					# remove the show from nepl
					self.remove_from_nepl(my_showid)
				continue

			# get the id for the next show and load the list of episode ids into ondecklist
			on_deck_epid        = ordered_eps[0]['episodeid']
			if len(ordered_eps) > 1:
				on_deck_list = [x['episodeid'] for x in ordered_eps[1:]]
			else:
				on_deck_list = []

			self.store_next_ep(on_deck_epid, my_showid, on_deck_list)		#load the data into 10000 using the showID as the ID

			if my_showid not in self.nepl:
				self.nepl.append(my_showid)		# store the showID in NEPL so DEFAULT can retrieve it
			kcount += 1
			if kcount >= self.initial_limit:		# restricts the first run to the initial limit
				self.initial_limit = 1000000000
				break

		#update the stored nepl
		WINDOW.setProperty("%s.nepl" % 'LazyTV', str(self.nepl))

		log('get_eps_Ended')


	def store_next_ep(self,episodeid,tvshowid, ondecklist):
		#stores the episode info into 10000
		try:
			TVShowID_ = int(tvshowid)
		except:
			TVShowID_ = tvshowid

		if not xbmc.abortRequested:
			ep_details_query['params']['episodeid'] = episodeid				# creates query
			ep_details = json_query(ep_details_query, True)					# query grabs all the episode details

			if ep_details.has_key('episodedetails'):						# continue only if there are details
				ep_details = ep_details['episodedetails']
				episode    = ("%.2d" % float(ep_details['episode']))
				season     = "%.2d" % float(ep_details['season'])
				episodeno  = "s%se%s" %(season,episode)
				rating     = str(round(float(ep_details['rating']),1))

				if (ep_details['resume']['position'] and ep_details['resume']['total']) > 0:
					resume = "true"
					played = '%s%%'%int((float(ep_details['resume']['position']) / float(ep_details['resume']['total'])) * 100)
				else:
					resume = "false"
					played = '0%'

				if ep_details['playcount'] >= 1:
					watched = "true"
				else:
					watched = "false"

				#if not self.PLOT_ENABLE and watched == "false":
				if watched == "false":
					plot = "* Plot hidden to avoid spoilers. *"
				else:
					plot = ep_details['plot']

				plot = ''
				art = ep_details['art']
				path = self.media_path(ep_details['file'])

				play = 'XBMC.RunScript(' + __addonid__ + ',episodeid=' + str(ep_details.get('episodeid')) + ')'

				streaminfo = self.media_streamdetails(ep_details['file'].encode('utf-8').lower(),ep_details['streamdetails'])

				#WINDOW.setProperty("%s.%s.DBID"                	% ('LazyTV', TVShowID_), str(ep_details.get('episodeid')))
				WINDOW.setProperty("%s.%s.Title"               	% ('LazyTV', TVShowID_), ep_details['title'])
				WINDOW.setProperty("%s.%s.Episode"             	% ('LazyTV', TVShowID_), episode)
				WINDOW.setProperty("%s.%s.EpisodeNo"           	% ('LazyTV', TVShowID_), episodeno)
				WINDOW.setProperty("%s.%s.Season"              	% ('LazyTV', TVShowID_), season)
				#WINDOW.setProperty("%s.%s.Plot"                	% ('LazyTV', TVShowID_), plot)
				WINDOW.setProperty("%s.%s.TVshowTitle"         	% ('LazyTV', TVShowID_), ep_details['showtitle'])
				#WINDOW.setProperty("%s.%s.Rating"              	% ('LazyTV', TVShowID_), rating)
				WINDOW.setProperty("%s.%s.Runtime"             	% ('LazyTV', TVShowID_), str(int((ep_details['runtime'] / 60) + 0.5)))
				#WINDOW.setProperty("%s.%s.Premiered"           	% ('LazyTV', TVShowID_), ep_details['firstaired'])
				WINDOW.setProperty("%s.%s.Art(thumb)"          	% ('LazyTV', TVShowID_), art.get('thumb',''))
				WINDOW.setProperty("%s.%s.Art(tvshow.fanart)"  	% ('LazyTV', TVShowID_), art.get('tvshow.fanart',''))
				WINDOW.setProperty("%s.%s.Art(tvshow.poster)"  	% ('LazyTV', TVShowID_), art.get('tvshow.poster',''))
				WINDOW.setProperty("%s.%s.Art(tvshow.banner)"  	% ('LazyTV', TVShowID_), art.get('tvshow.banner',''))
				WINDOW.setProperty("%s.%s.Art(tvshow.clearlogo)"	% ('LazyTV', TVShowID_), art.get('tvshow.clearlogo',''))
				WINDOW.setProperty("%s.%s.Art(tvshow.clearart)" 	% ('LazyTV', TVShowID_), art.get('tvshow.clearart',''))
				WINDOW.setProperty("%s.%s.Art(tvshow.landscape)"	% ('LazyTV', TVShowID_), art.get('tvshow.landscape',''))
				WINDOW.setProperty("%s.%s.Art(tvshow.characterart)"% ('LazyTV', TVShowID_), art.get('tvshow.characterart',''))
				WINDOW.setProperty("%s.%s.Resume"              	% ('LazyTV', TVShowID_), resume)
				WINDOW.setProperty("%s.%s.PercentPlayed"       	% ('LazyTV', TVShowID_), played)
				#WINDOW.setProperty("%s.%s.Watched"             	% ('LazyTV', TVShowID_), watched)
				WINDOW.setProperty("%s.%s.File"                	% ('LazyTV', TVShowID_), ep_details['file'])
				WINDOW.setProperty("%s.%s.Path"                	% ('LazyTV', TVShowID_), path)
				WINDOW.setProperty("%s.%s.Play"                	% ('LazyTV', TVShowID_), play)
				#WINDOW.setProperty("%s.%s.VideoCodec"          	% ('LazyTV', TVShowID_), streaminfo['videocodec'])
				#WINDOW.setProperty("%s.%s.VideoResolution"     	% ('LazyTV', TVShowID_), streaminfo['videoresolution'])
				#WINDOW.setProperty("%s.%s.VideoAspect"         	% ('LazyTV', TVShowID_), streaminfo['videoaspect'])
				#WINDOW.setProperty("%s.%s.AudioCodec"          	% ('LazyTV', TVShowID_), streaminfo['audiocodec'])
				#WINDOW.setProperty("%s.%s.AudioChannels"       	% ('LazyTV', TVShowID_), str(streaminfo['audiochannels']))
				WINDOW.setProperty("%s.%s.CountEps"       			% ('LazyTV', TVShowID_), str(self.count_eps))
				WINDOW.setProperty("%s.%s.CountWatchedEps"       	% ('LazyTV', TVShowID_), str(self.count_weps))
				WINDOW.setProperty("%s.%s.CountUnwatchedEps"       % ('LazyTV', TVShowID_), str(self.count_uweps))
				WINDOW.setProperty("%s.%s.CountonDeckEps"       	% ('LazyTV', TVShowID_), str(self.count_ondeckeps))
				WINDOW.setProperty("%s.%s.EpisodeID"       		% ('LazyTV', TVShowID_), str(episodeid))
				WINDOW.setProperty("%s.%s.odlist"          		% ('LazyTV', TVShowID_), str(ondecklist))

			del ep_details


	def swap_over(self, TVShowID_):
		log('swapover_started')

		#WINDOW.setProperty("%s.%s.DBID"                   % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.DBID"                   % ('LazyTV', 'temp')))
		WINDOW.setProperty("%s.%s.Title"                   % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.Title"                   % ('LazyTV', 'temp')))
		WINDOW.setProperty("%s.%s.Episode"                 % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.Episode"                   % ('LazyTV', 'temp')))
		WINDOW.setProperty("%s.%s.EpisodeNo"               % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.EpisodeNo"                   % ('LazyTV', 'temp')))
		WINDOW.setProperty("%s.%s.Season"                  % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.Season"                   % ('LazyTV', 'temp')))
		#WINDOW.setProperty("%s.%s.Plot"                   % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.Plot"                   % ('LazyTV', 'temp')))
		WINDOW.setProperty("%s.%s.TVshowTitle"             % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.TVshowTitle"                   % ('LazyTV', 'temp')))
		#WINDOW.setProperty("%s.%s.Rating"                 % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.Rating"                   % ('LazyTV', 'temp')))
		WINDOW.setProperty("%s.%s.Runtime"                 % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.Runtime"                   % ('LazyTV', 'temp')))
		#WINDOW.setProperty("%s.%s.Premiered"              % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.Premiered"                   % ('LazyTV', 'temp')))
		WINDOW.setProperty("%s.%s.Art(thumb)"              % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.Art(thumb)"                   % ('LazyTV', 'temp')))
		WINDOW.setProperty("%s.%s.Art(tvshow.fanart)"      % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.Art(tvshow.fanart)"                   % ('LazyTV', 'temp')))
		WINDOW.setProperty("%s.%s.Art(tvshow.poster)"      % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.Art(tvshow.poster)"                   % ('LazyTV', 'temp')))
		WINDOW.setProperty("%s.%s.Art(tvshow.banner)"      % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.Art(tvshow.banner)"                   % ('LazyTV', 'temp')))
		WINDOW.setProperty("%s.%s.Art(tvshow.clearlogo)"   % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.Art(tvshow.clearlogo)"                   % ('LazyTV', 'temp')))
		WINDOW.setProperty("%s.%s.Art(tvshow.clearart)"    % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.Art(tvshow.clearart)"                   % ('LazyTV', 'temp')))
		WINDOW.setProperty("%s.%s.Art(tvshow.landscape)"   % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.Art(tvshow.landscape)"                   % ('LazyTV', 'temp')))
		WINDOW.setProperty("%s.%s.Art(tvshow.characterart)"% ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.Art(tvshow.characterart)"                   % ('LazyTV', 'temp')))
		WINDOW.setProperty("%s.%s.Resume"                  % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.Resume"                   % ('LazyTV', 'temp')))
		WINDOW.setProperty("%s.%s.PercentPlayed"           % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.PercentPlayed"                   % ('LazyTV', 'temp')))
		#WINDOW.setProperty("%s.%s.Watched"                % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.watched"                   % ('LazyTV', 'temp')))
		WINDOW.setProperty("%s.%s.File"                    % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.File"                   % ('LazyTV', 'temp')))
		WINDOW.setProperty("%s.%s.Path"                    % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.Path"                   % ('LazyTV', 'temp')))
		WINDOW.setProperty("%s.%s.Play"                    % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.Play"                   % ('LazyTV', 'temp')))
		#WINDOW.setProperty("%s.%s.VideoCodec"             % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.VideoCodec"                   % ('LazyTV', 'temp')))
		#WINDOW.setProperty("%s.%s.VideoResolution"        % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.VideoResolution"                   % ('LazyTV', 'temp')))
		#WINDOW.setProperty("%s.%s.VideoAspect"            % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.VideoAspect"                   % ('LazyTV', 'temp')))
		#WINDOW.setProperty("%s.%s.AudioCodec"             % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.AudioCodec"                   % ('LazyTV', 'temp')))
		#WINDOW.setProperty("%s.%s.AudioChannels"          % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.AudioChannels"                   % ('LazyTV', 'temp')))
		WINDOW.setProperty("%s.%s.CountEps"                % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.CountEps"                   % ('LazyTV', 'temp')))
		WINDOW.setProperty("%s.%s.CountWatchedEps"         % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.CountWatchedEps"                   % ('LazyTV', 'temp')))
		WINDOW.setProperty("%s.%s.CountUnwatchedEps"       % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.CountUnwatchedEps"                   % ('LazyTV', 'temp')))
		WINDOW.setProperty("%s.%s.CountonDeckEps"          % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.CountonDeckEps"                   % ('LazyTV', 'temp')))
		WINDOW.setProperty("%s.%s.EpisodeID"               % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.EpisodeID"                   % ('LazyTV', 'temp')))
		WINDOW.setProperty("%s.%s.odlist"                  % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.odlist"                   % ('LazyTV', 'temp')))
		log('swapover_End')


	def test_output(self):
		for x in self.nepl:
			log(WINDOW.getProperty("%s.%s.TVshowTitle" % ('LazyTV', x)) + ' :-: ' +WINDOW.getProperty("%s.%s.EpisodeNo" % ('LazyTV', x)))


	def day_conv(self, date_string):
		op_format = '%Y-%m-%d %H:%M:%S'
		Y, M, D, h, mn, s, ux, uy, uz        = time.strptime(date_string, op_format)
		lw_max    = datetime.datetime(Y, M, D, h ,mn, s)
		date_num  = time.mktime(lw_max.timetuple())
		return date_num


	def media_path(self, path):
		# Check for stacked movies
		try:
			path = os.path.split(path)[0].rsplit(' , ', 1)[1].replace(",,",",")
		except:
			path = os.path.split(path)[0]
		# Fixes problems with rared movies and multipath
		if path.startswith("rar://"):
			path = [os.path.split(urllib.url2pathname(path.replace("rar://","")))[0]]
		elif path.startswith("multipath://"):
			temp_path = path.replace("multipath://","").split('%2f/')
			path = []
			for item in temp_path:
				path.append(urllib.url2pathname(item))
		else:
			path = [path]
		return path[0]


	def media_streamdetails(self, filename, streamdetails):
		info = {}
		video = streamdetails['video']
		audio = streamdetails['audio']
		if '3d' in filename:
			info['videoresolution'] = '3d'
		elif video:
			videowidth = video[0]['width']
			videoheight = video[0]['height']
			if (video[0]['width'] <= 720 and video[0]['height'] <= 480):
				info['videoresolution'] = "480"
			elif (video[0]['width'] <= 768 and video[0]['height'] <= 576):
				info['videoresolution'] = "576"
			elif (video[0]['width'] <= 960 and video[0]['height'] <= 544):
				info['videoresolution'] = "540"
			elif (video[0]['width'] <= 1280 and video[0]['height'] <= 720):
				info['videoresolution'] = "720"
			elif (video[0]['width'] >= 1281 or video[0]['height'] >= 721):
				info['videoresolution'] = "1080"
			else:
				info['videoresolution'] = ""
		elif (('dvd') in filename and not ('hddvd' or 'hd-dvd') in filename) or (filename.endswith('.vob' or '.ifo')):
			info['videoresolution'] = '576'
		elif (('bluray' or 'blu-ray' or 'brrip' or 'bdrip' or 'hddvd' or 'hd-dvd') in filename):
			info['videoresolution'] = '1080'
		else:
			info['videoresolution'] = '1080'
		if video:
			info['videocodec'] = video[0]['codec']
			if (video[0]['aspect'] < 1.4859):
				info['videoaspect'] = "1.33"
			elif (video[0]['aspect'] < 1.7190):
				info['videoaspect'] = "1.66"
			elif (video[0]['aspect'] < 1.8147):
				info['videoaspect'] = "1.78"
			elif (video[0]['aspect'] < 2.0174):
				info['videoaspect'] = "1.85"
			elif (video[0]['aspect'] < 2.2738):
				info['videoaspect'] = "2.20"
			else:
				info['videoaspect'] = "2.35"
		else:
			info['videocodec'] = ''
			info['videoaspect'] = ''
		if audio:
			info['audiocodec'] = audio[0]['codec']
			info['audiochannels'] = audio[0]['channels']
		else:
			info['audiocodec'] = ''
			info['audiochannels'] = ''
		return info

def grab_settings():
	playlist_notifications = True if __setting__("notify")  == 'true' else False
	resume_partials        = True if __setting__('resume_partials') == 'true' else False
	keep_logs              = True if __setting__('logging') == 'true' else False
	nextprompt             = True if __setting__('nextprompt') == 'true' else False
	promptduration         = int(__setting__('promptduration'))
	log('settings grabbed')

if ( __name__ == "__main__" ):
	xbmc.sleep(000) #testing delay for clean system
	log(' %s started' % __addonversion__)

	grab_settings()											# gets the settings for the Addon

	Main()

	del Main
	del LazyMonitor
	del LazyPlayer

	log(' %s stopped' % __addonversion__)



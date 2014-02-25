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
#@@@@@@@@@@ y.  - make sure the addon works for double episodes and split episodes*
#@@@@@@@@@@ - allow more options for ordering  -------------------------------------------------------------------TEST
#@@@@@@@@@@ - include random episode show list  ------------------------------------------------------------------TEST
#@@@@@@@@@@ - include random "repeat" episode from played Shows
#@@@@@@@@@@ - optional function that will tell you when you are  -----------------------------------------------------
				watching an episode that has an unplayed episode just before it  ---------------------------------TEST
#@@@@@@@@@@ - multiple language support*
#@@@@@@@@@@ - automatic extension of the random playlist so it only exits when you press Stop
#@@@@@@@@@@
#@@@@@@@@@@		TEST WITH LAST EPISODES
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
__addonversion__       = tuple([int(x) for x in __addon__.getAddonInfo('version').split('.')])
__scriptPath__         = __addon__.getAddonInfo('path')
__profile__            = xbmc.translatePath(__addon__.getAddonInfo('profile'))
__setting__            = __addon__.getSetting
lang                   = __addon__.getLocalizedString
start_time             = time.time()
base_time              = time.time()
WINDOW                 = xbmcgui.Window(10000)
DIALOG                 = xbmcgui.Dialog()

WINDOW.setProperty("LazyTV.Version", str(__addonversion__))
WINDOW.setProperty("LazyTV.ServicePath", str(__scriptPath__))

keep_logs              = True if __setting__('logging') == 'true' else False
playlist_notifications = True if __setting__("notify")  == 'true' else False
resume_partials        = True if __setting__('resume_partials') == 'true' else False
nextprompt             = True if __setting__('nextprompt') == 'true' else False
prevcheck              = True if __setting__('prevcheck') == 'true' else False
promptduration         = int(__setting__('promptduration'))
moviemid               = True if __setting__('moviemid') == 'true' else False
first_run              = True if __setting__('first_run') == 'true' else False

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


# get the current version of XBMC
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
plf                    = {"jsonrpc": "2.0","id": 1, "method": "Files.GetDirectory", "params": {"directory": "special://profile/playlists/video/", "media": "video"}}


log('Running: ' + str(__release__))

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

def stringlist_to_reallist(string):
	# this is needed because ast.literal_eval gives me EOF errors for no obvious reason
	real_string = string.replace("[","").replace("]","").replace(" ","").split(",")
	return real_string

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


def convert_pl_to_showlist(selected_pl, pltype):
	# derive filtered_showids from smart playlist
	filename = os.path.split(selected_pl)[1]
	clean_path = 'special://profile/playlists/video/' + filename

	#retrieve the shows in the supplied playlist, save their ids to a list
	plf['params']['directory'] = clean_path
	playlist_contents = json_query(plf, True)

	if 'files' not in playlist_contents:
		filtered_showids = []
	else:
		if not playlist_contents['files']:
			filtered_showids = []
		else:
			for x in playlist_contents['files']:
				if pltype == 'tv':
					filtered_showids = [x['id'] for x in playlist_contents['files'] if x['type'] == 'tvshow']
					log(filtered_showids, 'showids in playlist')
					if not filtered_showids:
						filtered_showids= []
				elif pltype == 'mv':
					filtered_showids = [x['id'] for x in playlist_contents['files'] if x['type'] == 'movie']

	#returns the list of all and filtered shows and episodes
	return filtered_showids



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

		# grab odlist
		# check if curent show is in odlist
		# if it is then pause and post notification, include S0xE0x of first available
		# if notification is Yes Watch then unpause (this should be default action)
		# if notification is No, then go to the TV show page
		# of if they prefer, start playing that OnDeck episode

		self.pl_running = WINDOW.getProperty("%s.playlist_running"	% ('LazyTV'))

		if 'item' in self.ep_details and 'type' in self.ep_details['item']:

			if self.ep_details['item']['type'] == 'episode':

				episode_np = fix_SE(self.ep_details['item']['episode'])
				season_np = fix_SE(self.ep_details['item']['season'])
				showtitle = self.ep_details['item']['showtitle']
				show_npid = int(self.ep_details['item']['tvshowid'])
				ep_npid = int(self.ep_details['item']['id'])

				log(prevcheck, label='prevcheck')
				if prevcheck and show_npid not in randos and self.pl_running != 'true':
					odlist = ast.literal_eval(WINDOW.getProperty("%s.%s.odlist" % ('LazyTV', show_npid)))
					stored_epid = int(WINDOW.getProperty("%s.%s.EpisodeID" % ('LazyTV', show_npid)))
					stored_seas = fix_SE(int(WINDOW.getProperty("%s.%s.Season" % ('LazyTV', show_npid))))
					stored_epis = fix_SE(int(WINDOW.getProperty("%s.%s.Episode" % ('LazyTV', show_npid))))
					if ep_npid in odlist and stored_epid:
						#pause
						xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Player.PlayPause","params":{"playerid":1,"play":false},"id":1}')

						#show notification
						usr_note = DIALOG.yesno(lang(32160), lang(32161) % (showtitle,stored_seas, stored_epis), lang(32162))
						log(usr_note)

						if usr_note == 0:
							#unpause
							xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Player.PlayPause","params":{"playerid":1,"play":true},"id":1}')
						else:
							xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Player.Stop", "params": { "playerid": 1 }, "id": 1}')
							xbmc.sleep(100)
							xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "Player.Open", "params": { "item": { "episodeid": %d }, "options":{ "resume": true }  }, "id": 1 }' % (stored_epid))

				if self.pl_running == 'true' and playlist_notifications:

					xbmc.executebuiltin('Notification(%s,%s S%sE%s,%i)' % (lang(32163),showtitle,season_np,episode_np,5000))

				if self.pl_running == 'true' and resume_partials:

					res_point = self.ep_details['item']['resume']
					if res_point['position'] > 0:

						seek_point = int((float(res_point['position']) / float(res_point['total'])) *100)
						seek['params']['value'] = seek_point
						json_query(seek, True)

				# this prompts Main daemon to set up the swap and prepare the prompt
				LazyPlayer.playing_epid = ep_npid
				LazyPlayer.playing_showid = show_npid
				log('LazyPlayer supplied showid = ' + str(LazyPlayer.playing_showid))
				log('LazyPlayer supplied epid = '+ str(LazyPlayer.playing_epid))


			elif self.ep_details['item']['type'] == 'movie' and self.pl_running == 'true' :

				if playlist_notifications:

					xbmc.executebuiltin('Notification(%s,%s,%i)' % (lang(32163),self.ep_details['item']['label'],5000))

				if resume_partials and self.ep_details['item']['resume']['position'] > 0:
					seek_point = int((float(self.ep_details['item']['resume']['position']) / float(self.ep_details['item']['resume']['total'])) *100)
					seek['params']['value'] = seek_point
					json_query(seek, True)

				elif moviemid and self.ep_details['item']['playcount'] != 0:
					time = runtime_converter(xbmc.getInfoLabel('VideoPlayer.Duration'))
					seek_point = int(100 * (time * 0.75 * ((random.randint(0,100) / 100.0) ** 2)) / time)
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
						prompt = DIALOG.select(lang(32164), [lang(32165),lang(32166) % (Main.nextprompt_info['showtitle'], SE)], autoclose=promptduration * 1000)
					else:
						prompt = DIALOG.select(lang(32164) [lang(32165), lang(32166) % (Main.nextprompt_info['showtitle'], SE)])
					if prompt == -1:
						prompt = 0
					log(prompt)
				elif __release__ == 'Gotham':
					if promptduration:
						prompt = DIALOG.yesno(lang(32167) % promptduration, lang(32168) % (Main.nextprompt_info['showtitle'], SE), lang(32169), autoclose=promptduration * 1000)
					else:
						prompt = DIALOG.yesno(lang(32167) % promptduration, lang(32168) % (Main.nextprompt_info['showtitle'], SE), lang(32169))
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


class Main(object):
	def __init__(self, *args, **kwargs):
		log('monitor instantiated', reset = True)
		
		self.initial_limit    = 10
		self.count            = 0
		Main.target           = False
		Main.nextprompt_info  = {}
		Main.onLibUpdate      = False
		Main.monitor_override = False
		self.nepl             = []
		self.eject            = False
		self.randy_flag       = False							# the list of currently stored episodes

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
		
		xbmc.sleep(110) 	#give any other instance a chance to notice that it must kill itself
											
		WINDOW.setProperty('LazyTV_service_running' , 'true')

		self.get_eps(showids = self.all_shows_list)				#gets the beginning list of unwatched shows
		
		xbmc.sleep(1000) 		# wait 1 seconds before filling the full list
		
		self.get_eps(showids = self.all_shows_list)

		log('variable_init_End')



	def _daemon(self):
		while not xbmc.abortRequested and WINDOW.getProperty('LazyTV_service_running') == 'true':
			xbmc.sleep(100)
			self._daemon_check()

	def _daemon_check(self):

		self.np_next = False

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
			tmp_wep = int(WINDOW.getProperty("%s.%s.CountWatchedEps"         % ('LazyTV', self.sp_next)).replace("''",'0'))  + 1
			tmp_uwep = max(0, int(WINDOW.getProperty("%s.%s.CountUnwatchedEps"      % ('LazyTV', self.sp_next)).replace("''",'0')) -1)

			log('odlist = ' + str(retod))

			self.npodlist = ast.literal_eval(retod)

			if self.npodlist:

				'''			REMEMBER: RANDOS STAY IN ODLIST UNTIL WATCHED			'''

				if LazyPlayer.playing_showid in randos:

					if LazyPlayer.playing_epid not in self.npodlist:
						log('rando not in odlist')

						self.np_next = False

					else:
						log('rando in odlist')

						self.randy_flag = True
						random.shuffle(self.npodlist)
						self.np_next    = self.npodlist[0]
						self.npodlist.remove(LazyPlayer.playing_epid)
						newod           = self.npodlist
						self.store_next_ep(self.np_next,'temp', newod, tmp_wep, tmp_wep)

					LazyPlayer.playing_epid   = False
					LazyPlayer.playing_showid = False

					if Main.monitor_override:
						log('monitor override, swap called')

						Main.monitor_override   = False
						LazyPlayer.playing_epid = False
						Main.target             = False
						self.np_next            = False

						self.swap_over(self.sp_next)

				else:
					storedepid = int(WINDOW.getProperty("LazyTV.%s.EpisodeID" % self.sp_next))
					log('odlist exists, supplied epid = ' + str(LazyPlayer.playing_epid) + ' , vs stored ep = ' + str(storedepid))

					if LazyPlayer.playing_epid == storedepid: #if the ep is the current nextep
						log('supplied epid matches stored epid')

						self.np_next = self.npodlist[0]
						newod        = [int(x) for x in self.npodlist[1:]]

						self.store_next_ep(self.np_next,'temp', newod, tmp_wep, tmp_wep)

						log('ep to load = ' + str(self.np_next))
						log('new odlist = ' + str(newod))

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
							newod        = [int(x) for x in self.npodlist[cp + 1:]]

							self.store_next_ep(self.np_next,'temp', newod, tmp_wep, tmp_wep )

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
							self.eject = True 		#if the episode is the last in the list then send the message to remove the showid from nepl

			if self.np_next:
				log('next ep to load = ' + str(self.np_next))

			# set NEXTPROMPT if required

			if nextprompt and self.np_next and not self.eject and not self.randy_flag:

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

			log(label='tick = ',message=str(tick))
			log(message=Main.target, label='target')

			# resets the ids so this first section doesnt run again until some thing new is playing
			LazyPlayer.playing_showid = False

			# only allow the monitor override to run once
			Main.monitor_override     = False

			# only allow the randy flag to run once, this avoids previous episode notification for randos
			self.randy_flag = False


		# check the position of the played item every 5 seconds, if it is beyond the Main.target position then trigger the pre-stop update
		if Main.target:

			self.count = (self.count + 1) % 50

			if self.count == 0: 	#check the position of the playing item every 5 seconds, if it is past the Main.target then run the swap

				if runtime_converter(xbmc.getInfoLabel('VideoPlayer.Time')) > Main.target:

					log('Main.target exceeded')
					log(self.nextprompt_info)

					if self.eject:
						self.remove_from_nepl(self.sp_next)
						self.sp_next = False
						self.eject = False

					if self.sp_next:
						self.swap_over(self.sp_next)
						log('swap occurred')

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


	def reshuffle_randos(self, randos=[]):
		# this reshuffles the randos, it leaves the rando in the odlist
		# it can accept a list of randos or individual ones
		# this can only be called at the start of the random play or list view ADDON
		# because if it happens after the rando is displayed
		# the playingID wont match the stored ID

		for rando in randos:

			# get odlist
			tmp_od = ast.literal_eval(WINDOW.getProperty("LazyTVs.%s.odlist" % rando))
			tmp_ep = int(WINDOW.getProperty("LazyTVs.%s.EpisodeID" % rando))
			tmp_wep = WINDOW.getProperty("%s.%s.CountWatchedEps"         % ('LazyTV', rando)).replace("''",'0')
			tmp_uwep = WINDOW.getProperty("%s.%s.CountUnwatchedEps"         % ('LazyTV', rando)).replace("''",'0')

			if not tmp_od:
				continue

			# choose new rando
			randy = random.shuffle(tmp_od)[0]

			# add the current ep back into rotation
			tmp_od.append(tmp_ep)

			# get ep details and load it up
			store_next_ep(randy, rando, tmp_od, tmp_uwep, tmp_wep)




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
			self.show_lw = [x['tvshowid'] for x in self.lshowsR['tvshows'] if x['tvshowid'] in self.showids]
		log('self.show_lw = ' + str(self.show_lw))

		for my_showid in self.show_lw:				#process the list of shows

			eps_query['params']['tvshowid'] = my_showid			# creates query
			self.ep = json_query(eps_query, True)				# query grabs the TV show episodes

			if 'episodes' not in self.ep: 						#ignore show if show has no episodes
				continue
			else:
				self.eps = self.ep['episodes']

			played_eps           = []
			all_unplayed     = []
			ondeck_eps         = []
			Season               = 1 	# these are set to 1x1 in order to ignore specials
			Episode              = 0
			watched_showcount    = 0
			self.count_ondeckeps = 0 	# will be the total number of ondeck episodes
			on_deck_epid         = ''

			_append = all_unplayed.append 		#reference to avoid reevaluation on each loop

			# runs through the list and finds the watched episode with the highest season and episode numbers, and creates a list of unwatched episodes
			for ep in self.eps:
				if ep['playcount'] != 0:
					watched_showcount += 1
					if (ep['season'] == Season and ep['episode'] > Episode) or ep['season'] > Season:
						Season = ep['season']
						Episode = ep['episode']
				else:
					_append(ep)

			# remove duplicate files, this removes the second ep in double episodes
			files = []
			tmpvar = all_unplayed
			for ep in tmpvar:
				if ep['file'] in files:
					ondeck_eps.remove(ep)
				else:
					files.append(ep['file'])
			del files
			del tmpvar


			# this is the handler for random shows, basically, if the show is in the rando list, then unwatched all shows are considered on deck
			# this section will now provide both an ondeck list and an offdeck list
			ondeck_eps = [x for x in all_unplayed if x['season'] > Season or (x['season'] == Season and x['episode'] > Episode)]
			offdeck_eps = [x for x in all_unplayed if x not in ondeck_eps]

			self.count_eps   = len(self.eps)						# the total number of episodes
			self.count_weps  = watched_showcount					# the total number of watched episodes
			self.count_uweps = self.count_eps - self.count_weps 	# the total number of unwatched episodes

			# sorts the list of unwatched shows by lowest season and lowest episode, filters the list to remove empty strings
			# addon handles shuffling for randos
			if ondeck_eps:
				ordered_eps = sorted(ondeck_eps, key = lambda ondeck_eps: (ondeck_eps['season'], ondeck_eps['episode']))
				ordered_eps = filter(None, ordered_eps)

			if not ordered_eps and not offdeck_eps:			# ignores show if there is no on-deck or offdeck episodes
				if my_showid in self.nepl:					# remove the show from nepl
					self.remove_from_nepl(my_showid)
				continue

			# get the id for the next show and load the list of episode ids into ondecklist
			on_deck_epid        = ordered_eps[0]['episodeid']



			'''@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
			@@@@@@@
			@@@@@@@		move the handling of rando selection to the ADDON>?
			@@@@@@@
			@@@@@@@
			@@@@'''

			# another handler for randos, as they have to stay in the odlist
			if my_showid in randos:

				if len(ordered_eps) > 1:
					on_deck_list = [x['episodeid'] for x in ordered_eps]
				else:
					on_deck_list = []

			else:

				if len(ordered_eps) > 1:
					on_deck_list = [x['episodeid'] for x in ordered_eps[1:]]
				else:
					on_deck_list = []

			self.store_next_ep(on_deck_epid, my_showid, on_deck_list, self.count_uweps, self.count_weps)		#load the data into 10000 using the showID as the ID

			if my_showid not in self.nepl:
				self.nepl.append(my_showid)		# store the showID in NEPL so DEFAULT can retrieve it

			kcount += 1
			if kcount >= self.initial_limit:		# restricts the first run to the initial limit
				self.initial_limit = 1000000000
				break

		#update the stored nepl
		WINDOW.setProperty("%s.nepl" % 'LazyTV', str(self.nepl))

		log('get_eps_Ended')


	def store_next_ep(self,episodeid,tvshowid, ondecklist, uwep=0,wep=0):

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

				art = ep_details['art']

				#if ep_details['playcount'] >= 1:
				#	watched = "true"
				#else:
				#	watched = "false"

				#if not self.PLOT_ENABLE and watched == "false":
				#if watched == "false":
				#	plot = "* Plot hidden to avoid spoilers. *"
				#else:
				#	plot = ep_details['plot']

				#plot = ''
				
				#path = self.media_path(ep_details['file'])

				#play = 'XBMC.RunScript(' + __addonid__ + ',episodeid=' + str(ep_details.get('episodeid')) + ')'

				#streaminfo = self.media_streamdetails(ep_details['file'].encode('utf-8').lower(),ep_details['streamdetails'])

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
				#WINDOW.setProperty("%s.%s.Art(tvshow.fanart)"  	% ('LazyTV', TVShowID_), art.get('tvshow.fanart',''))
				WINDOW.setProperty("%s.%s.Art(tvshow.poster)"  	% ('LazyTV', TVShowID_), art.get('tvshow.poster',''))
				#WINDOW.setProperty("%s.%s.Art(tvshow.banner)"  	% ('LazyTV', TVShowID_), art.get('tvshow.banner',''))
				#WINDOW.setProperty("%s.%s.Art(tvshow.clearlogo)"	% ('LazyTV', TVShowID_), art.get('tvshow.clearlogo',''))
				#WINDOW.setProperty("%s.%s.Art(tvshow.clearart)" 	% ('LazyTV', TVShowID_), art.get('tvshow.clearart',''))
				#WINDOW.setProperty("%s.%s.Art(tvshow.landscape)"	% ('LazyTV', TVShowID_), art.get('tvshow.landscape',''))
				#WINDOW.setProperty("%s.%s.Art(tvshow.characterart)"% ('LazyTV', TVShowID_), art.get('tvshow.characterart',''))
				WINDOW.setProperty("%s.%s.Resume"              	% ('LazyTV', TVShowID_), resume)
				WINDOW.setProperty("%s.%s.PercentPlayed"       	% ('LazyTV', TVShowID_), played)
				#WINDOW.setProperty("%s.%s.Watched"             	% ('LazyTV', TVShowID_), watched)
				WINDOW.setProperty("%s.%s.File"                	% ('LazyTV', TVShowID_), ep_details['file'])
				#WINDOW.setProperty("%s.%s.Path"                	% ('LazyTV', TVShowID_), path)
				#WINDOW.setProperty("%s.%s.Play"                	% ('LazyTV', TVShowID_), play)
				#WINDOW.setProperty("%s.%s.VideoCodec"          	% ('LazyTV', TVShowID_), streaminfo['videocodec'])
				#WINDOW.setProperty("%s.%s.VideoResolution"     	% ('LazyTV', TVShowID_), streaminfo['videoresolution'])
				#WINDOW.setProperty("%s.%s.VideoAspect"         	% ('LazyTV', TVShowID_), streaminfo['videoaspect'])
				#WINDOW.setProperty("%s.%s.AudioCodec"          	% ('LazyTV', TVShowID_), streaminfo['audiocodec'])
				#WINDOW.setProperty("%s.%s.AudioChannels"       	% ('LazyTV', TVShowID_), str(streaminfo['audiochannels']))
				WINDOW.setProperty("%s.%s.CountWatchedEps"       	% ('LazyTV', TVShowID_), str(wep))
				WINDOW.setProperty("%s.%s.CountUnwatchedEps"       % ('LazyTV', TVShowID_), str(uwep))
				WINDOW.setProperty("%s.%s.CountonDeckEps"       	% ('LazyTV', TVShowID_), str(len(ondecklist)))
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
		#WINDOW.setProperty("%s.%s.Art(tvshow.fanart)"      % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.Art(tvshow.fanart)"                   % ('LazyTV', 'temp')))
		WINDOW.setProperty("%s.%s.Art(tvshow.poster)"      % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.Art(tvshow.poster)"                   % ('LazyTV', 'temp')))
		#WINDOW.setProperty("%s.%s.Art(tvshow.banner)"      % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.Art(tvshow.banner)"                   % ('LazyTV', 'temp')))
		#WINDOW.setProperty("%s.%s.Art(tvshow.clearlogo)"   % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.Art(tvshow.clearlogo)"                   % ('LazyTV', 'temp')))
		#WINDOW.setProperty("%s.%s.Art(tvshow.clearart)"    % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.Art(tvshow.clearart)"                   % ('LazyTV', 'temp')))
		#WINDOW.setProperty("%s.%s.Art(tvshow.landscape)"   % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.Art(tvshow.landscape)"                   % ('LazyTV', 'temp')))
		#WINDOW.setProperty("%s.%s.Art(tvshow.characterart)"% ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.Art(tvshow.characterart)"                   % ('LazyTV', 'temp')))
		WINDOW.setProperty("%s.%s.Resume"                  % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.Resume"                   % ('LazyTV', 'temp')))
		WINDOW.setProperty("%s.%s.PercentPlayed"           % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.PercentPlayed"                   % ('LazyTV', 'temp')))
		#WINDOW.setProperty("%s.%s.Watched"                % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.watched"                   % ('LazyTV', 'temp')))
		WINDOW.setProperty("%s.%s.File"                    % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.File"                   % ('LazyTV', 'temp')))
		#WINDOW.setProperty("%s.%s.Path"                    % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.Path"                   % ('LazyTV', 'temp')))
		#WINDOW.setProperty("%s.%s.Play"                    % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.Play"                   % ('LazyTV', 'temp')))
		#WINDOW.setProperty("%s.%s.VideoCodec"             % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.VideoCodec"                   % ('LazyTV', 'temp')))
		#WINDOW.setProperty("%s.%s.VideoResolution"        % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.VideoResolution"                   % ('LazyTV', 'temp')))
		#WINDOW.setProperty("%s.%s.VideoAspect"            % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.VideoAspect"                   % ('LazyTV', 'temp')))
		#WINDOW.setProperty("%s.%s.AudioCodec"             % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.AudioCodec"                   % ('LazyTV', 'temp')))
		#WINDOW.setProperty("%s.%s.AudioChannels"          % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.AudioChannels"                   % ('LazyTV', 'temp')))
		WINDOW.setProperty("%s.%s.CountWatchedEps"         % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.CountWatchedEps"                   % ('LazyTV', 'temp')))
		WINDOW.setProperty("%s.%s.CountUnwatchedEps"       % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.CountUnwatchedEps"                   % ('LazyTV', 'temp')))
		WINDOW.setProperty("%s.%s.CountonDeckEps"          % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.CountonDeckEps"                   % ('LazyTV', 'temp')))
		WINDOW.setProperty("%s.%s.EpisodeID"               % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.EpisodeID"                   % ('LazyTV', 'temp')))
		WINDOW.setProperty("%s.%s.odlist"                  % ('LazyTV', TVShowID_), WINDOW.getProperty("%s.%s.odlist"                   % ('LazyTV', 'temp')))
		log('swapover_End')


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
	global playlist_notifications
	global resume_partials
	global keep_logs
	global nextprompt
	global promptduration
	global randos
	global prevcheck

	playlist_notifications = True if __setting__("notify")  == 'true' else False
	resume_partials        = True if __setting__('resume_partials') == 'true' else False
	keep_logs              = True if __setting__('logging') == 'true' else False
	nextprompt             = True if __setting__('nextprompt') == 'true' else False
	promptduration         = int(__setting__('promptduration'))
	prevcheck              = True if __setting__('prevcheck') == 'true' else False
	try:
		randos             = ast.literal_eval(__setting__('randos'))
	except:
		randos = []
	WINDOW.setProperty("LazyTV.randos", str(randos))

	'''
	@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
	@@@@@@@@
	@@@@@@@@	insert method to check previous rando list, and if anything is changed to send those shows for get_eps full updates
	@@@@@@@@
	@@@@@@@@	maybe have both lists produced and let the Addon decide which to use? This will actually be needed for the 'Complete the Series' option 
	@@@@@@@@	which is the option to watch a random unwatched episode of completed series 
	@@@@@'''

	log('randos = ' + str(randos))

	log('settings grabbed')

if ( __name__ == "__main__" ):
	xbmc.sleep(000) #testing delay for clean system
	log(' %s started' % str(__addonversion__))

	grab_settings()											# gets the settings for the Addon

	Main()

	del Main
	del LazyMonitor
	del LazyPlayer

	log(' %s stopped' % str(__addonversion__))



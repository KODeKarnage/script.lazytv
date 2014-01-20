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
#@@@@@@@@@@ 6.  option to choose to watch next episode on finish of last (the next episode is available...)
#@@@@@@@@@@ 9.  option onNotify for Frodo (needs http enabled)
#@@@@@@@@@@ 10. take the stored_data work from default put into Service
#@@@@@@@@@@ 11. add check to see if service is running, or if there are any shows loaded
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

# This is a throwaway variable to deal with a python bug
try:
	throwaway = datetime.datetime.strptime('20110101','%Y%m%d')
except:
	pass


__addon__        = xbmcaddon.Addon()
__addonid__      = __addon__.getAddonInfo('id')
__addonversion__ = __addon__.getAddonInfo('version')
__scriptPath__   = __addon__.getAddonInfo('path')
__profile__      = xbmc.translatePath(__addon__.getAddonInfo('profile'))
__setting__      = __addon__.getSetting
start_time       = time.time()
base_time        = time.time()
__release__      = "Frodo" if xbmcaddon.Addon('xbmc.addon').getAddonInfo('version') == (12,0,0) else "Gotham"
__release__      = "Frodo"

keep_logs        = True if __setting__('logging') == 'true' else False

whats_playing       = {"jsonrpc": "2.0","method": "Player.GetItem","params": {"properties": ["tvshowid","episode", "season", "playcount"],"playerid": 1},"id": "1"}
now_playing_details = {"jsonrpc": "2.0","method": "VideoLibrary.GetEpisodeDetails","params": {"properties": ["playcount", "tvshowid"],"episodeid": "1"},"id": "1"}
ep_to_show_query    = {"jsonrpc": "2.0","method": "VideoLibrary.GetEpisodeDetails","params": {"properties": ["lastplayed","tvshowid"],"episodeid": "1"},"id": "1"}
show_request        = {"jsonrpc": "2.0","method": "VideoLibrary.GetTVShows","params": {"filter": {"field": "playcount","operator": "is","value": "0"},"properties": ["genre","title","playcount","mpaa","watchedepisodes","episode","thumbnail"]},"id": "1"}
show_request_lw     = {"jsonrpc": "2.0","method": "VideoLibrary.GetTVShows","params": {"filter": {"field": "playcount", "operator": "is", "value": "0" },"properties": ["lastplayed"], "sort":{"order": "descending", "method":"lastplayed"} },"id": "1" }
eps_query           = {"jsonrpc": "2.0","method": "VideoLibrary.GetEpisodes","params": {"properties": ["season","episode","runtime","resume","playcount","tvshowid","lastplayed","file"],"tvshowid": "1"},"id": "1"}
ep_details_query    = {"jsonrpc": "2.0","method": "VideoLibrary.GetEpisodeDetails","params": {"properties": ["title","playcount","plot","season","episode","showtitle","file","lastplayed","rating","resume","art","streamdetails","firstaired","runtime","tvshowid"],"episodeid": 1},"id": "1"}

def log(message):
	if keep_logs:
		global start_time
		global base_time
		new_time     = time.time()
		gap_time     = "%5f" % (new_time - start_time)
		start_time   = new_time
		total_gap    = "%5f" % (new_time - base_time)
		logmsg       = '%s : %s :: %s ::: %s ' % (__addonid__, total_gap, gap_time, message)
		xbmc.log(msg = logmsg)

log(__release__)

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
	l = time_string.split(':')
	x = len(time_string)
	if x > 5:
		return int(l[0]) * 3600 + int(l[1]) * 60 + int(l[2])
	elif x > 2:
		return int(l[0]) * 60 + int(l[1])
	else:
		return int(l[0])


class LazyPlayer(xbmc.Player):
	def __init__(self, *args, **kwargs):
		xbmc.Player.__init__(self)
		self.WINDOW   = xbmcgui.Window(10000)							# where the show info will be stored

	def onPlayBackStarted(self):

		# Functions to place here
		# 1. if notification is wanted then show notification but only if item is a tv show
		# 2. check whether the item is a tv episode and if it is then send it to the daemon

		log('plyback started')

		self.nowplaying_showid = 'nothing playing'
		self.WINDOW.setProperty("%s.%s" % ('LazyTV', 'daemon_acknowledges') , 'null')
		self.WINDOW.setProperty("%s.%s" % ('LazyTV', 'trigger'), 'null')

		self.ep_details = json_query(whats_playing, True)

		if 'item' in self.ep_details and 'type' in self.ep_details['item'] and self.ep_details['item']['type'] == 'episode':

			self.nowplaying_showid = self.ep_details['item']['tvshowid'] 			# get the showid of the playing episode
			self.nowplaying_playcount = self.ep_details['item']['playcount'] 			# get the showid of the playing episode

			episode_np = self.ep_details['item']['episode']
			season_np = self.ep_details['item']['season']

			#check whether the episode that is playing is the OnDeck episode
			if int(self.WINDOW.getProperty("%s.%s.Episode" % ('LazyTV', self.nowplaying_showid)))  == episode_np:

				if int(self.WINDOW.getProperty("%s.%s.Season" % ('LazyTV', self.nowplaying_showid)))  == season_np:

					self.WINDOW.setProperty("%s.%s" % ('LazyTV', 'hey_an_episode_is_playing'),str(self.nowplaying_showid))



	def onPlayBackEnded(self):
		self.onPlayBackStopped()

	'''
	#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
	#@@@@@@@@@@
	#@@@@@@@@@@ -=- once playback starts, check if episode, if it is then proceed
	#@@@@@@@@@@ -=- check if episode has NEXT_EP, if it does then proceed
	#@@@@@@@@@@ -=- get information for NEXT_EP and store
	#@@@@@@@@@@ -=- get runtime for current ep, calculate 5pct to end
	#@@@@@@@@@@ -=- have the daemon check the current position, if it is within 5pct of the end then make change to nepl and store NEXT_EP data
	#@@@@@@@@@@ -=- add notification that the EP has been updated, this can be removed onPlaybackStopped or onPlayback started
	#@@@@@@@@@@
	#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@'''



	def onPlayBackStopped(self):
		log("playbackstopped")

		if self.nowplaying_showid != 'nothing playing': #if an ONDECK episode was playing and is now stopped

			#every half second up to 5 seconds total, check if episode has been switched to watched, if it has pull the trigger
			now_playing_details['params']['episodeid'] = int(self.WINDOW.getProperty("%s.%s.EpisodeID" % ('LazyTV', self.nowplaying_showid)))

			self.count = 0

			while self.nowplaying_showid != 'nothing playing' and self.count < 10:
				xbmc.sleep(500)
				now_playing = json_query(now_playing_details, True)

				if 'episodedetails' in now_playing and 'playcount' in now_playing['episodedetails']:
					if int(self.nowplaying_playcount) < int(now_playing['episodedetails']['playcount']):

						self.WINDOW.setProperty("%s.%s" % ('LazyTV', 'process_this'), str(self.nowplaying_showid))

						self.nowplaying_showid = 'nothing playing'

				self.count += 1

			self.nowplaying_showid = 'nothing playing'
			self.WINDOW.setProperty("%s.%s" % ('LazyTV', 'hey_an_episode_is_playing'),"null")
			self.WINDOW.setProperty("%s.%s" % ('LazyTV', 'daemon_acknowledges') , "null")
			self.WINDOW.setProperty("%s.%s" % ('LazyTV', 'trigger'), 'null')




class LazyMonitor(xbmc.Monitor):
	def __init__(self, *args, **kwargs):

		log('monitor instantiated')
		self.initialisation_variables()

		# Set a window property that let's other scripts know we are running (window properties are cleared on XBMC start)
		self.WINDOW.clearProperty('%s_service_running' % __addon__)

		#give any other instance a chance to notice that it must kill itself
		self.WINDOW.setProperty('%s_service_running' % __addon__, 'true')

		#temp notification for testing
		xbmc.executebuiltin('Notification("LazyTV Service has started",20000)')
		xbmc.log(msg=self.WINDOW.getProperty('%s_service_running' % __addon__))

		log('settings loaded')

		#gets the beginning list of unwatched shows
		self.get_eps(showids = self.all_shows_list)

		xbmc.sleep(5000) 		# wait 5 seconds before filling the full list
		self.get_eps(showids = self.all_shows_list)

		log('daemon started')
		self._daemon()			#_daemon keeps the monitor alive


	def initialisation_variables(self):
		self.WINDOW   = xbmcgui.Window(10000)							# where the show info will be stored
		self.lzplayer = LazyPlayer()									# used to post notifications on episode change
		self.grab_settings()											# gets the settings for the Addon
		self.retrieve_all_show_ids()									# queries to get all show IDs
		self.nepl = []													# the list of currently stored episodes
		self.initial_limit = 10
		self.players_showid = 'nothing playing'
		self.WINDOW.setProperty("%s.%s" % ('LazyTV', 'hey_an_episode_is_playing'),"null")
		self.WINDOW.setProperty("%s.%s" % ('LazyTV', 'daemon_acknowledges') , "null")
		self.WINDOW.setProperty("%s.%s" % ('LazyTV', 'trigger'), 'null')
		self.WINDOW.setProperty("%s.%s" % ('LazyTV', 'process_this'), 'null')


	def grab_settings(self):
		self.useSPL        = True if __setting__("populate_by") == 'true' else False
		self.multiples     = True if __setting__("multipleshows") == 'true' else False
		self.premieres     = True if __setting__("premieres")  == 'true' else False
		self.resume        = True if __setting__("resume_partials")  == 'true' else False
		self.notifications = True if __setting__("notify")  == 'true' else False
		self.firstrun      = True if __setting__("first_run")  == 'true' else False
		self.pl_length     = int(__setting__("length"))
		self.primary       = __setting__("primary_function")
		self.sortby        = __setting__("sort_list_by")
		self.users_spl     = __setting__('users_spl')


	def _daemon(self):
		log('is running ' + str(self.WINDOW.getProperty('%s_service_running' % __addon__)))

		count = 0

		while not xbmc.abortRequested and self.WINDOW.getProperty('%s_service_running' % __addon__) == 'true':
			xbmc.sleep(100)

			workwork = self.WINDOW.getProperty("%s.%s" % ('LazyTV', 'process_this'))
			if workwork != 'null':
				self.WINDOW.setProperty("%s.%s" % ('LazyTV', 'process_this'), 'null')
				self.get_eps(workwork)

			pass1 = self.WINDOW.getProperty("%s.%s" % ('LazyTV', 'hey_an_episode_is_playing'))

			if pass1 != 'null':
				self.WINDOW.setProperty("%s.%s" % ('LazyTV', 'hey_an_episode_is_playing') , 'null')
				list_of_next_eps = self.WINDOW.getProperty("%s.%s.odlist" % ('LazyTV', pass1)).replace("[","").replace("]","").replace(" ","").split(",")

				self.store_next_ep(int(list_of_next_eps[0]),'temp', [int(x) for x in list_of_next_eps[1:]])
				self.WINDOW.setProperty("%s.%s" % ('LazyTV', 'daemon_acknowledges') , str(pass1))

				target = runtime_converter(xbmc.getInfoLabel('VideoPlayer.Duration')) * 0.9

			pass2 =self.WINDOW.getProperty("%s.%s" % ('LazyTV', 'daemon_acknowledges'))
			if pass2 != 'null':
				count = (count + 1) % 50

				if count == 0: 	#check the position of the playing item every 5 seconds, if it is past the target then run the swap
					if runtime_converter(xbmc.getInfoLabel('VideoPlayer.Time')) > target:

						self.WINDOW.setProperty("%s.%s" % ('LazyTV', 'daemon_acknowledges'),'null')
						self.WINDOW.setProperty("%s.%s" % ('LazyTV', 'trigger'), str(pass2))

			pass3 = self.WINDOW.getProperty("%s.%s" % ('LazyTV', 'trigger'))

			if pass3 != 'null':
				#triggered if the player is stopped and the gun is loaded, or if the show is almost finished
				self.swap_over(int(pass3))

				self.WINDOW.setProperty("%s.%s" % ('LazyTV', 'daemon_acknowledges') , 'null')
				self.WINDOW.setProperty("%s.%s" % ('LazyTV', 'trigger'), 'null')


	def onSettingsChanged(self):
		#update the settings
		self.grab_settings()

	def onDatabaseUpdated(self, database):
		if database == 'video':
			# update the entire list again, this is to ensure we have picked up any new shows.
			self.retrieve_all_show_ids()
			self.get_eps(showids = self.all_shows_list)

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
								ep_to_show_query['params']['episodeid'] = self.ndata['item']['id']
								self.candidate = json_query(ep_to_show_query, True)['episodedetails']['tvshowid']
								self.get_eps(self.candidate)
								self.test_output()


		elif method == 'Player.OnPlay':
			# Method 		Player.OnPlay
			# data 			{"item":{"id":1,"type":"episode"},"player":{"playerid":1,"speed":1}}
			if 'item' in self.ndata:
				if 'type' in self.ndata['item']:
					if self.ndata['item']['type'] == 'episode':
						if 'player' in self.ndata:
							pass
							#show notification if set
							#probably not needed, addon can take care of notification



	def retrieve_all_show_ids(self):

		self.result = json_query(show_request, True)
		if 'tvshows' not in self.result:
			self.all_shows_list = []
		else:
			self.all_shows_list = [id['tvshowid'] for id in self.result['tvshows']]


	def get_eps(self, showids = []):
		log('get eps started')
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

			eps_query['params']['tvshowid'] = show[1]			# creates query
			self.ep = json_query(eps_query, True)				# query grabs the TV show episodes

			if 'episodes' not in self.ep: 						#ignore show if show has no episodes
				continue
			else:
				self.eps = self.ep['episodes']

			self.last_watched = show[0]
			played_eps        = []
			unplayed_eps      = []
			Season            = 0
			Episode           = 0
			watched_showcount = 0
			uw_Season            = 999999
			uw_Episode           = 999999
			self.count_ondeckeps = 0 	# will be the total number of ondeck episodes
			on_deck_epid = ''

			_append = unplayed_eps.append 		#reference to avoid reevaluation on each loop

			# runs through the list and finds the watched episode with the highest season and episode numbers, and creates a list of unwatched episodes
			for ep in self.eps:
				if ep['playcount'] != 0:
					watched_showcount += 1
					if (ep['season'] == Season and ep['episode'] > Episode) or ep['season'] > Season:
						Season = ep['season']
						Episode = ep['episode']
				else:
					_append(ep)

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
				if show[1] in self.nepl:					# remove the show from nepl
					self.nepl.remove(show[1])
				continue

			# get the id for the next show and load the list of episode ids into ondecklist
			on_deck_epid        = ordered_eps[0]['episodeid']
			if len(ordered_eps) > 1:
				on_deck_list = [x['episodeid'] for x in ordered_eps[1:]]
			else:
				on_deck_list = []

			self.store_next_ep(on_deck_epid, show[1], on_deck_list)		#load the data into 10000 using the showID as the ID

			if show[1] not in self.nepl:
				self.nepl.append(show[1])		# store the showID in NEPL so DEFAULT can retrieve it
			kcount += 1
			if kcount >= self.initial_limit:		# restricts the first run to the initial limit
				self.initial_limit = 1000000000
				break

		#update the stored nepl
		self.WINDOW.setProperty("%s.nepl" % 'LazyTV', str(self.nepl))

		log('get eps ended')



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
				path = media_path(ep_details['file'])

				play = 'XBMC.RunScript(' + __addonid__ + ',episodeid=' + str(ep_details.get('episodeid')) + ')'

				streaminfo = media_streamdetails(ep_details['file'].encode('utf-8').lower(),ep_details['streamdetails'])

				#self.WINDOW.setProperty("%s.%s.DBID"                	% ('LazyTV', TVShowID_), str(ep_details.get('episodeid')))
				self.WINDOW.setProperty("%s.%s.Title"               	% ('LazyTV', TVShowID_), ep_details['title'])
				self.WINDOW.setProperty("%s.%s.Episode"             	% ('LazyTV', TVShowID_), episode)
				self.WINDOW.setProperty("%s.%s.EpisodeNo"           	% ('LazyTV', TVShowID_), episodeno)
				self.WINDOW.setProperty("%s.%s.Season"              	% ('LazyTV', TVShowID_), season)
				#self.WINDOW.setProperty("%s.%s.Plot"                	% ('LazyTV', TVShowID_), plot)
				self.WINDOW.setProperty("%s.%s.TVshowTitle"         	% ('LazyTV', TVShowID_), ep_details['showtitle'])
				#self.WINDOW.setProperty("%s.%s.Rating"              	% ('LazyTV', TVShowID_), rating)
				self.WINDOW.setProperty("%s.%s.Runtime"             	% ('LazyTV', TVShowID_), str(int((ep_details['runtime'] / 60) + 0.5)))
				#self.WINDOW.setProperty("%s.%s.Premiered"           	% ('LazyTV', TVShowID_), ep_details['firstaired'])
				self.WINDOW.setProperty("%s.%s.Art(thumb)"          	% ('LazyTV', TVShowID_), art.get('thumb',''))
				self.WINDOW.setProperty("%s.%s.Art(tvshow.fanart)"  	% ('LazyTV', TVShowID_), art.get('tvshow.fanart',''))
				self.WINDOW.setProperty("%s.%s.Art(tvshow.poster)"  	% ('LazyTV', TVShowID_), art.get('tvshow.poster',''))
				self.WINDOW.setProperty("%s.%s.Art(tvshow.banner)"  	% ('LazyTV', TVShowID_), art.get('tvshow.banner',''))
				self.WINDOW.setProperty("%s.%s.Art(tvshow.clearlogo)"	% ('LazyTV', TVShowID_), art.get('tvshow.clearlogo',''))
				self.WINDOW.setProperty("%s.%s.Art(tvshow.clearart)" 	% ('LazyTV', TVShowID_), art.get('tvshow.clearart',''))
				self.WINDOW.setProperty("%s.%s.Art(tvshow.landscape)"	% ('LazyTV', TVShowID_), art.get('tvshow.landscape',''))
				self.WINDOW.setProperty("%s.%s.Art(tvshow.characterart)"% ('LazyTV', TVShowID_), art.get('tvshow.characterart',''))
				self.WINDOW.setProperty("%s.%s.Resume"              	% ('LazyTV', TVShowID_), resume)
				self.WINDOW.setProperty("%s.%s.PercentPlayed"       	% ('LazyTV', TVShowID_), played)
				#self.WINDOW.setProperty("%s.%s.Watched"             	% ('LazyTV', TVShowID_), watched)
				self.WINDOW.setProperty("%s.%s.File"                	% ('LazyTV', TVShowID_), ep_details['file'])
				self.WINDOW.setProperty("%s.%s.Path"                	% ('LazyTV', TVShowID_), path)
				self.WINDOW.setProperty("%s.%s.Play"                	% ('LazyTV', TVShowID_), play)
				#self.WINDOW.setProperty("%s.%s.VideoCodec"          	% ('LazyTV', TVShowID_), streaminfo['videocodec'])
				#self.WINDOW.setProperty("%s.%s.VideoResolution"     	% ('LazyTV', TVShowID_), streaminfo['videoresolution'])
				#self.WINDOW.setProperty("%s.%s.VideoAspect"         	% ('LazyTV', TVShowID_), streaminfo['videoaspect'])
				#self.WINDOW.setProperty("%s.%s.AudioCodec"          	% ('LazyTV', TVShowID_), streaminfo['audiocodec'])
				#self.WINDOW.setProperty("%s.%s.AudioChannels"       	% ('LazyTV', TVShowID_), str(streaminfo['audiochannels']))
				self.WINDOW.setProperty("%s.%s.CountEps"       			% ('LazyTV', TVShowID_), str(self.count_eps))
				self.WINDOW.setProperty("%s.%s.CountWatchedEps"       	% ('LazyTV', TVShowID_), str(self.count_weps))
				self.WINDOW.setProperty("%s.%s.CountUnwatchedEps"       % ('LazyTV', TVShowID_), str(self.count_uweps))
				self.WINDOW.setProperty("%s.%s.CountonDeckEps"       	% ('LazyTV', TVShowID_), str(self.count_ondeckeps))
				self.WINDOW.setProperty("%s.%s.EpisodeID"       		% ('LazyTV', TVShowID_), str(episodeid))
				self.WINDOW.setProperty("%s.%s.odlist"          		% ('LazyTV', TVShowID_), str(ondecklist))

			del ep_details


	def swap_over(self, TVShowID_):

		#self.WINDOW.setProperty("%s.%s.DBID"                   % ('LazyTV', TVShowID_), self.WINDOW.getProperty("%s.%s.DBID"                   % ('LazyTV', 'temp')))
		self.WINDOW.setProperty("%s.%s.Title"                   % ('LazyTV', TVShowID_), self.WINDOW.getProperty("%s.%s.Title"                   % ('LazyTV', 'temp')))
		self.WINDOW.setProperty("%s.%s.Episode"                 % ('LazyTV', TVShowID_), self.WINDOW.getProperty("%s.%s.Episode"                   % ('LazyTV', 'temp')))
		self.WINDOW.setProperty("%s.%s.EpisodeNo"               % ('LazyTV', TVShowID_), self.WINDOW.getProperty("%s.%s.EpisodeNo"                   % ('LazyTV', 'temp')))
		self.WINDOW.setProperty("%s.%s.Season"                  % ('LazyTV', TVShowID_), self.WINDOW.getProperty("%s.%s.Season"                   % ('LazyTV', 'temp')))
		#self.WINDOW.setProperty("%s.%s.Plot"                   % ('LazyTV', TVShowID_), self.WINDOW.getProperty("%s.%s.Plot"                   % ('LazyTV', 'temp')))
		self.WINDOW.setProperty("%s.%s.TVshowTitle"             % ('LazyTV', TVShowID_), self.WINDOW.getProperty("%s.%s.TVshowTitle"                   % ('LazyTV', 'temp')))
		#self.WINDOW.setProperty("%s.%s.Rating"                 % ('LazyTV', TVShowID_), self.WINDOW.getProperty("%s.%s.Rating"                   % ('LazyTV', 'temp')))
		self.WINDOW.setProperty("%s.%s.Runtime"                 % ('LazyTV', TVShowID_), self.WINDOW.getProperty("%s.%s.Runtime"                   % ('LazyTV', 'temp')))
		#self.WINDOW.setProperty("%s.%s.Premiered"              % ('LazyTV', TVShowID_), self.WINDOW.getProperty("%s.%s.Premiered"                   % ('LazyTV', 'temp')))
		self.WINDOW.setProperty("%s.%s.Art(thumb)"              % ('LazyTV', TVShowID_), self.WINDOW.getProperty("%s.%s.Art(thumb)"                   % ('LazyTV', 'temp')))
		self.WINDOW.setProperty("%s.%s.Art(tvshow.fanart)"      % ('LazyTV', TVShowID_), self.WINDOW.getProperty("%s.%s.Art(tvshow.fanart)"                   % ('LazyTV', 'temp')))
		self.WINDOW.setProperty("%s.%s.Art(tvshow.poster)"      % ('LazyTV', TVShowID_), self.WINDOW.getProperty("%s.%s.Art(tvshow.poster)"                   % ('LazyTV', 'temp')))
		self.WINDOW.setProperty("%s.%s.Art(tvshow.banner)"      % ('LazyTV', TVShowID_), self.WINDOW.getProperty("%s.%s.Art(tvshow.banner)"                   % ('LazyTV', 'temp')))
		self.WINDOW.setProperty("%s.%s.Art(tvshow.clearlogo)"   % ('LazyTV', TVShowID_), self.WINDOW.getProperty("%s.%s.Art(tvshow.clearlogo)"                   % ('LazyTV', 'temp')))
		self.WINDOW.setProperty("%s.%s.Art(tvshow.clearart)"    % ('LazyTV', TVShowID_), self.WINDOW.getProperty("%s.%s.Art(tvshow.clearart)"                   % ('LazyTV', 'temp')))
		self.WINDOW.setProperty("%s.%s.Art(tvshow.landscape)"   % ('LazyTV', TVShowID_), self.WINDOW.getProperty("%s.%s.Art(tvshow.landscape)"                   % ('LazyTV', 'temp')))
		self.WINDOW.setProperty("%s.%s.Art(tvshow.characterart)"% ('LazyTV', TVShowID_), self.WINDOW.getProperty("%s.%s.Art(tvshow.characterart)"                   % ('LazyTV', 'temp')))
		self.WINDOW.setProperty("%s.%s.Resume"                  % ('LazyTV', TVShowID_), self.WINDOW.getProperty("%s.%s.Resume"                   % ('LazyTV', 'temp')))
		self.WINDOW.setProperty("%s.%s.PercentPlayed"           % ('LazyTV', TVShowID_), self.WINDOW.getProperty("%s.%s.PercentPlayed"                   % ('LazyTV', 'temp')))
		#self.WINDOW.setProperty("%s.%s.Watched"                % ('LazyTV', TVShowID_), self.WINDOW.getProperty("%s.%s.watched"                   % ('LazyTV', 'temp')))
		self.WINDOW.setProperty("%s.%s.File"                    % ('LazyTV', TVShowID_), self.WINDOW.getProperty("%s.%s.File"                   % ('LazyTV', 'temp')))
		self.WINDOW.setProperty("%s.%s.Path"                    % ('LazyTV', TVShowID_), self.WINDOW.getProperty("%s.%s.Path"                   % ('LazyTV', 'temp')))
		self.WINDOW.setProperty("%s.%s.Play"                    % ('LazyTV', TVShowID_), self.WINDOW.getProperty("%s.%s.Play"                   % ('LazyTV', 'temp')))
		#self.WINDOW.setProperty("%s.%s.VideoCodec"             % ('LazyTV', TVShowID_), self.WINDOW.getProperty("%s.%s.VideoCodec"                   % ('LazyTV', 'temp')))
		#self.WINDOW.setProperty("%s.%s.VideoResolution"        % ('LazyTV', TVShowID_), self.WINDOW.getProperty("%s.%s.VideoResolution"                   % ('LazyTV', 'temp')))
		#self.WINDOW.setProperty("%s.%s.VideoAspect"            % ('LazyTV', TVShowID_), self.WINDOW.getProperty("%s.%s.VideoAspect"                   % ('LazyTV', 'temp')))
		#self.WINDOW.setProperty("%s.%s.AudioCodec"             % ('LazyTV', TVShowID_), self.WINDOW.getProperty("%s.%s.AudioCodec"                   % ('LazyTV', 'temp')))
		#self.WINDOW.setProperty("%s.%s.AudioChannels"          % ('LazyTV', TVShowID_), self.WINDOW.getProperty("%s.%s.AudioChannels"                   % ('LazyTV', 'temp')))
		self.WINDOW.setProperty("%s.%s.CountEps"                % ('LazyTV', TVShowID_), self.WINDOW.getProperty("%s.%s.CountEps"                   % ('LazyTV', 'temp')))
		self.WINDOW.setProperty("%s.%s.CountWatchedEps"         % ('LazyTV', TVShowID_), self.WINDOW.getProperty("%s.%s.CountWatchedEps"                   % ('LazyTV', 'temp')))
		self.WINDOW.setProperty("%s.%s.CountUnwatchedEps"       % ('LazyTV', TVShowID_), self.WINDOW.getProperty("%s.%s.CountUnwatchedEps"                   % ('LazyTV', 'temp')))
		self.WINDOW.setProperty("%s.%s.CountonDeckEps"          % ('LazyTV', TVShowID_), self.WINDOW.getProperty("%s.%s.CountonDeckEps"                   % ('LazyTV', 'temp')))
		self.WINDOW.setProperty("%s.%s.EpisodeID"               % ('LazyTV', TVShowID_), self.WINDOW.getProperty("%s.%s.EpisodeID"                   % ('LazyTV', 'temp')))
		self.WINDOW.setProperty("%s.%s.odlist"                  % ('LazyTV', TVShowID_), self.WINDOW.getProperty("%s.%s.odlist"                   % ('LazyTV', 'temp')))

	def test_output(self):
		for x in self.nepl:
			log(self.WINDOW.getProperty("%s.%s.TVshowTitle" % ('LazyTV', x)) + ' :-: ' +self.WINDOW.getProperty("%s.%s.EpisodeNo" % ('LazyTV', x)))


	def day_conv(self, date_string):
		self.op_format = '%Y-%m-%d %H:%M:%S'
		self.lw        = time.strptime(date_string, self.op_format)
		self.lw_max    = datetime.datetime(self.lw[0],self.lw[1],self.lw[2],self.lw[3],self.lw[4],self.lw[5])
		self.date_num  = time.mktime(self.lw_max.timetuple())
		return self.date_num


def media_path(path):
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


def media_streamdetails(filename, streamdetails):
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



if ( __name__ == "__main__" ):
	xbmc.sleep(000) #testing delay for clean system
	log(' %s started' % __addonversion__)

	LazyMonitor()
	del LazyMonitor
	del LazyPlayer

	log(' %s stopped' % __addonversion__)



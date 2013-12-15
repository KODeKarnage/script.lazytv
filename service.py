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
#@@@@@@@@@@ 4. add path, play
#@@@@@@@@@@ 6. option to choose to watch next episode on finish of last (the next episode is available...)
#@@@@@@@@@@ 8. store show list and ep list for addon quick reference
#@@@@@@@@@@ 9. option onNotify for Frodo (needs http enabled)
#@@@@@@@@@@
#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@'''



import xbmc
import xbmcgui
import xbmcaddon
import os
import time
import datetime
from resources.lazy_lib import *
from resources.lazy_queries import *
import ast

# This is a throwaway variable to deal with a python bug
throwaway = datetime.datetime.strptime('20110101','%Y%m%d')

__addon__        = xbmcaddon.Addon()
__addonid__      = __addon__.getAddonInfo('id')
__addonversion__ = __addon__.getAddonInfo('version')
__scriptPath__   = __addon__.getAddonInfo('path')
__profile__      = xbmc.translatePath(__addon__.getAddonInfo('profile'))
__setting__      = __addon__.getSetting
start_time       = time.time()
base_time        = time.time()
__release__      = "Frodo" if xbmcaddon.Addon('xbmc.addon').getAddonInfo('version') == (12,0,0) else "Gotham"

def log(message):
	global start_time
	global base_time
	new_time = time.time()
	gap_time = "%5f" % (new_time - start_time)
	start_time = new_time
	total_gap = "%5f" % (new_time - base_time)
	logmsg       = '%s : %s :: %s ::: %s ' % (__addonid__, total_gap, gap_time, message)
	xbmc.log(msg = logmsg)



class LazyPlayer(xbmc.Player):
	def __init__(self, *args, **kwargs):
		xbmc.Player.__init__(self)
		self.engage = 'still'
		self.WINDOW   = xbmcgui.Window(10000)							# where the show info will be stored

	def onPlayBackStarted(self):
		self.ep_details = json_query(whats_playing, True)
		if 'item' in self.ep_details:
			if 'type' in self.ep_details['item']:
				if self.ep_details['item']['type'] == 'episode':
					self.engage = self.ep_details['item']['tvshowid']
					show_lastplayed['params']['tvshowid'] = self.engage
					self.engage_lw = json_query(show_lastplayed, True)['tvshowdetails']['lastplayed']
					#log('initial last played ' + str(self.engage_lw))


	def onPlayBackEnded(self):
		self.onPlayBackStopped()

	def onPlayBackStopped(self):

		if not self.engage == 'still' and __release__ == 'Frodo':

			#check if last watched has been updated
			self.stoptime = time.time()
			show_lastplayed['params']['tvshowid'] = self.engage

			self.count = 0
			while self.engage != 'still' and self.count < 10:
				self.current_lw = json_query(show_lastplayed, True)
				if 'tvshowdetails' in self.current_lw:
					if 'lastplayed' in self.current_lw['tvshowdetails']:
						#log(str(self.count) + ' last played ' + str(self.current_lw['tvshowdetails']['lastplayed']))
						if self.current_lw['tvshowdetails']['lastplayed'] > self.engage_lw:
							self.WINDOW.setProperty('%s_players_showid' % __addon__, str(self.engage))
							self.engage = 'still'

				self.count += 1
				xbmc.sleep(500)

			self.engage = 'still'


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
		self.players_showid = 'still'
		self.WINDOW.setProperty('%s_players_showid' % __addon__, 'still')

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
		self.test_output()
		while not xbmc.abortRequested and self.WINDOW.getProperty('%s_service_running' % __addon__) == 'true':
			xbmc.sleep(100)
			self.rec_showid = self.WINDOW.getProperty('%s_players_showid' % __addon__)
			if self.rec_showid != 'still':
				self.get_eps(int(self.rec_showid))
				self.WINDOW.setProperty('%s_players_showid' % __addon__, 'still')
				log('triggered in daemon ' + self.rec_showid)
				self.test_output()

	def onSettingsChanged(self):
		#update the settings
		self.grab_settings()

	def onDatabaseUpdated(self, database):

		if database == 'VideoLibrary':

			#renew the stored_show_ids
			self.retrieve_all_show_ids()
			self.get_eps(showids = self.all_shows_list)

			'''
			#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
			#@@@@@@@@@@
			#@@@@@@@@@@ HOW TO DETERMINE WHEN A SHOW NEEDS TO BE UPDATED ON SCAN FINISHED?
			#@@@@@@@@@@
			#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@


			#		NEW SHOW ADDED or show removed 		--  scan all shows, find new shows or removed shows
			#												for new shows - send to get_eps
			#												for removed shows, send to special function
			#		new episode available 	-- scan all shows, find the shows with different number of episode'''


	def onNotification(self, sender, method, data):
		pass

		log('notification recieved')
		log(data)
		skip = False
		try:
			self.ndata = ast.literal_eval(data)
			log(self.ndata)
		except:
			skip = True
		if skip == True:
			pass
		elif method == 'VideoLibrary.OnUpdate':
			log('onNotification started')
			# Method 		VideoLibrary.OnUpdate
			# data 			{"item":{"id":1,"type":"episode"},"playcount":4}
			if 'item' in self.ndata:
				if 'playcount' in self.ndata:
					if 'type' in self.ndata['item']:
						if self.ndata['item']['type'] == 'episode':
							if self.ndata['playcount'] < 2:

								#get showID and re-run getnextepisode for that show
								#what if last show is now watched
								#what if last show watched and previous show unwatched
								#what if user changed watched status of previous show
								#what if user set last show to unwatched

								ep_to_show_query['params']['episodeid'] = self.ndata['item']['id']
								self.candidate = json_query(ep_to_show_query, True)['episodedetails']['tvshowid']
								self.get_eps(self.candidate)
								self.test_output()
			log('onNotification ended')


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

		#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
		#@@@@@@@@@@
		#@@@@@@@@@@ CHECK IF THE ONUPDATE PICKS UP RESUME POINTS
		#@@@@@@@@@@
		#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@'''


	def retrieve_all_show_ids(self):

		self.result = json_query(show_request, True)
		if 'tvshows' not in self.result:
			self.all_shows_list = []
		else:
			self.all_shows_list = [id['tvshowid'] for id in self.result['tvshows']]




	def get_eps(self, showids = []):
		log('get eps started')
		# called whenever the Next_Eps stored in 10000 need to be updated
		# determines the next ep for the showids it is sent and saves the info to 10000

		#turns single show id into a list
		self.showids = []
		self.showids = showids if isinstance(showids, list) else [showids]
		self.orig_shows = []
		self.count = 0

		for x in range(len(self.nepl)):				#sets nepl original order, creates list of original shows, lists are in sync
			self.nepl[x][2] = x
			self.orig_shows.append(self.nepl[x][1])

		self.lshowsR = json_query(show_request_lw, True)		#gets showids and last watched
		if 'tvshows' not in self.lshowsR:						#if 'tvshows' isnt in the result, return without doing anything
			self.lshows = []
		else:
			self.lshows               = self.lshowsR['tvshows']
			self.lshows_int = [x for x in self.lshows if x['tvshowid'] in self.showids]
			self.show_lw              = [[self.day_conv(x['lastplayed']) if x['lastplayed'] else 0, x['tvshowid']] for x in self.lshows_int]
		self.show_lw.sort(reverse =True)		#this list is now ordered by last watched

		#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
		#@@@@@@@@@@
		#@@@@@@@@@@ WHERE IS THE BEST PLACE TO PUT THE SLOW-SYSTEM-SHOWID-LIMITER???
		#@@@@@@@@@@
		#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@

		for show in self.show_lw:				#process the list of shows

			eps_query['params']['tvshowid'] = show[1]			# creates query
			self.ep = json_query(eps_query, True)				# query grabs the TV show episodes

			if 'episodes' not in self.ep: 						#ignore show if show has no episodes
				continue
			else:
				self.eps = self.ep['episodes']

			self.played_eps = [x for x in self.eps if x['playcount'] is not 0]		#creates a list of episodes for the show that have been watched

			self.count_eps = len(self.eps)							# the total number of episodes
			self.count_weps = len(self.played_eps)					# the total number of watched episodes
			self.count_uweps = self.count_eps - self.count_weps 	# the total number of unwatched episodes

			if self.count_uweps == 0: 						# ignores show if there are no unwatched episodes
				continue

			if not self.played_eps:		#if the show doesnt have any watched episodes, the season, episode, and last watched are zero
				self.Season       = 0
				self.Episode      = 0
				self.last_watched = 0

			else:		#the last played episode is the one with the highest season number and then the highest episode number
				self.last_played_ep = sorted(self.played_eps, key =  lambda played_eps: (played_eps['season'], played_eps['episode']), reverse=True)[0]
				self.Season         = self.last_played_ep['season']
				self.Episode        = self.last_played_ep['episode']
				self.last_watched   = show[0]

			#uses the season and episode number to create a list of unwatched shows newer than the last watched one
			self.unplayed_eps = [x for x in self.eps if ((x['season'] == self.Season and x['episode'] > self.Episode) or (x['season'] > self.Season))]

			#sorts the list of unwatched shows by lowest season and lowest episode, filters the list to remove empty strings
			self.next_ep = sorted(self.unplayed_eps, key = lambda unplayed_eps: (unplayed_eps['season'], unplayed_eps['episode']))
			self.next_ep = filter(None, self.next_ep)

			if not self.next_ep:							#ignores show if there is no on-deck episode
				continue

			self.count_ondeckeps = len(self.unplayed_eps)			# the total number of ondeck episodes

			if self.next_ep[0]['tvshowid'] in self.orig_shows:							#check if the show is in original_list
				self.indrem = self.orig_shows.index(self.next_ep[0]['tvshowid'])		#replace last watched stat and order metric
				self.nepl.pop(self.indrem)
				self.new_entry = [show[0], show[1], 'lz%s' % self.count]
				self.nepl.insert(self.indrem, self.new_entry)
			else:
				self.new_entry = [show[0], show[1], 'lz%s' % self.count]					#add new entry to the end of the original list
				self.nepl.append(self.new_entry)

			self.store_next_ep(self.next_ep[0]['episodeid'], 'lz%s' % self.count)		#load the data into 10000
			self.count += 1

			if self.count >= self.initial_limit:		# restricts the first run to the initial limit
				self.initial_limit = 1000000000
				break

		#fixing the labels on the stored info

		self.nepl.sort(reverse=True)					# sort the active stored list by last watched
		self.new_pos = {}								# create a dict with {new_pos : old_pos}

		for x in range(len(self.nepl)):					# create list of tuples of old position and new position
			if x == self.nepl[x][2]:					# ignores the tuple if the order hasnt changed
				pass
			else:
				self.new_pos[x] = self.nepl[x][2]   	#	{new_pos:old_pos}

		self.all_pos = [x[2] for x in self.nepl]		#get the positions, old and new from nepl,
		self.available_slots = list(set(range(len(self.nepl))).difference(set(self.all_pos)))	# get all available slots in new order

		self.placeholder_slots = []			# place to hold temp moved
		#log('new_pos  ' + str(self.new_pos))
		while self.new_pos:

			while self.available_slots:
				#log('available slots '+ str(self.available_slots))
				self.popped_slot = self.available_slots.pop()						#grab an empty slot, remove it from available slots
				#log('popped slot' + str(self.popped_slot))
				self.reassign(self.popped_slot, self.new_pos[self.popped_slot])		#find the entry for that slot, send to Reassignment
				#log('tuple in question ' + str(self.new_pos[self.popped_slot]))
				if len(self.new_pos) > 1:
					try:
						int(self.new_pos[self.popped_slot])  							#is the slot a number or a string
						self.available_slots.append(self.new_pos[self.popped_slot])		#add the vacated slot to available slots '''
					except:
						self.placeholder_slots.append(self.new_pos[self.popped_slot])
				del self.new_pos[self.popped_slot]									#removes the new_pos:old_pos entry from dict
				#log('new_pos ' + str(self.new_pos))

			if self.new_pos:
				random_key = self.new_pos.keys()[0]									#select random integer key to reassign
				#log('random key ' + str(random_key))
				#log('original pair ' +str(random_key)+':'+str(self.new_pos[random_key]))
				random_placeholder = self.placeholder_slots.pop()					#select any placeholder slot
				#log('random placeholder '+str(random_placeholder))
				self.reassign(random_placeholder, self.new_pos[random_key])			#assign it to a placeholder slot
				self.available_slots.append(self.new_pos[random_key])				#add its old position to available slots
				self.new_pos[random_key] = random_placeholder						#change its old_pos to the freshly added placeholder
				#log('new pair ' +str(random_key)+':'+str( random_placeholder))
		log('get eps stopped')



	def store_next_ep(self,episodeid,show_place):
		#stores the episode info into 10000

		try:
			place = int(show_place)
		except:
			place = show_place

		if not xbmc.abortRequested:
			ep_details_query['params']['episodeid'] = episodeid				# creates query
			ep_details = json_query(ep_details_query, True)					# query grabs all the episode details
			if ep_details.has_key('episodedetails'):						# continue only if there are details
				ep_details = ep_details['episodedetails']
				episode = ("%.2d" % float(ep_details['episode']))
				season = "%.2d" % float(ep_details['season'])
				episodeno = "s%se%s" %(season,episode)
				rating = str(round(float(ep_details['rating']),1))

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

				'''		NOT SHOWING PLOT
				if not self.PLOT_ENABLE and watched == "false":
					plot = __localize__(32014)
				else:
					plot = ep_details['plot']'''

				plot = ''
				art = ep_details['art']
				path = media_path(ep_details['file'])

				'''		NEED TO CONSIDER WHAT TO DO HERE
				play = 'XBMC.RunScript(' + __addonid__ + ',episodeid=' + str(ep_details.get('episodeid')) + ')' '''
				play = ''

				streaminfo = media_streamdetails(ep_details['file'].encode('utf-8').lower(),ep_details['streamdetails'])

				self.WINDOW.setProperty("%s.%s.DBID"                	% ('LazyTV', place), str(ep_details.get('episodeid')))
				self.WINDOW.setProperty("%s.%s.Title"               	% ('LazyTV', place), ep_details['title'])
				self.WINDOW.setProperty("%s.%s.Episode"             	% ('LazyTV', place), episode)
				self.WINDOW.setProperty("%s.%s.EpisodeNo"           	% ('LazyTV', place), episodeno)
				self.WINDOW.setProperty("%s.%s.Season"              	% ('LazyTV', place), season)
				self.WINDOW.setProperty("%s.%s.Plot"                	% ('LazyTV', place), plot)
				self.WINDOW.setProperty("%s.%s.TVshowTitle"         	% ('LazyTV', place), ep_details['showtitle'])
				self.WINDOW.setProperty("%s.%s.Rating"              	% ('LazyTV', place), rating)
				self.WINDOW.setProperty("%s.%s.Runtime"             	% ('LazyTV', place), str(int((ep_details['runtime'] / 60) + 0.5)))
				self.WINDOW.setProperty("%s.%s.Premiered"           	% ('LazyTV', place), ep_details['firstaired'])
				self.WINDOW.setProperty("%s.%s.Art(thumb)"          	% ('LazyTV', place), art.get('thumb',''))
				self.WINDOW.setProperty("%s.%s.Art(tvshow.fanart)"  	% ('LazyTV', place), art.get('tvshow.fanart',''))
				self.WINDOW.setProperty("%s.%s.Art(tvshow.poster)"  	% ('LazyTV', place), art.get('tvshow.poster',''))
				self.WINDOW.setProperty("%s.%s.Art(tvshow.banner)"  	% ('LazyTV', place), art.get('tvshow.banner',''))
				self.WINDOW.setProperty("%s.%s.Art(tvshow.clearlogo)"	% ('LazyTV', place), art.get('tvshow.clearlogo',''))
				self.WINDOW.setProperty("%s.%s.Art(tvshow.clearart)" 	% ('LazyTV', place), art.get('tvshow.clearart',''))
				self.WINDOW.setProperty("%s.%s.Art(tvshow.landscape)"	% ('LazyTV', place), art.get('tvshow.landscape',''))
				self.WINDOW.setProperty("%s.%s.Art(tvshow.characterart)"% ('LazyTV', place), art.get('tvshow.characterart',''))
				self.WINDOW.setProperty("%s.%s.Resume"              	% ('LazyTV', place), resume)
				self.WINDOW.setProperty("%s.%s.PercentPlayed"       	% ('LazyTV', place), played)
				self.WINDOW.setProperty("%s.%s.Watched"             	% ('LazyTV', place), watched)
				self.WINDOW.setProperty("%s.%s.File"                	% ('LazyTV', place), ep_details['file'])
				self.WINDOW.setProperty("%s.%s.Path"                	% ('LazyTV', place), path)
				self.WINDOW.setProperty("%s.%s.Play"                	% ('LazyTV', place), play)
				self.WINDOW.setProperty("%s.%s.VideoCodec"          	% ('LazyTV', place), streaminfo['videocodec'])
				self.WINDOW.setProperty("%s.%s.VideoResolution"     	% ('LazyTV', place), streaminfo['videoresolution'])
				self.WINDOW.setProperty("%s.%s.VideoAspect"         	% ('LazyTV', place), streaminfo['videoaspect'])
				self.WINDOW.setProperty("%s.%s.AudioCodec"          	% ('LazyTV', place), streaminfo['audiocodec'])
				self.WINDOW.setProperty("%s.%s.AudioChannels"       	% ('LazyTV', place), str(streaminfo['audiochannels']))
				self.WINDOW.setProperty("%s.%s.CountEps"       			% ('LazyTV', place), str(self.count_eps))
				self.WINDOW.setProperty("%s.%s.CountWatchedEps"       	% ('LazyTV', place), str(self.count_weps))
				self.WINDOW.setProperty("%s.%s.CountUnwatchedEps"       % ('LazyTV', place), str(self.count_uweps))
				self.WINDOW.setProperty("%s.%s.CountonDeckEps"       	% ('LazyTV', place), str(self.count_ondeckeps))

			#log('show added ' + self.WINDOW.getProperty("%s.%s.TVshowTitle" 		% ('LazyTV', place)))
			#log('added into ' + str(place))
			del ep_details


	def reassign(self, new_pos, old_pos):
		#changes the labels on the stored episode data
		#log('show reassigned ' + self.WINDOW.getProperty("%s.%s.TVshowTitle" 		% ('LazyTV', old_pos)))
		#log('from ' + str(old_pos) + ' to ' + str(new_pos))

		self.WINDOW.setProperty("%s.%s.DBID"                	% ('LazyTV', new_pos), self.WINDOW.getProperty("%s.%s.DBID"                		% ('LazyTV', old_pos)))
		self.WINDOW.setProperty("%s.%s.Title"               	% ('LazyTV', new_pos), self.WINDOW.getProperty("%s.%s.Title"               		% ('LazyTV', old_pos)))
		self.WINDOW.setProperty("%s.%s.Episode"             	% ('LazyTV', new_pos), self.WINDOW.getProperty("%s.%s.Episode"             		% ('LazyTV', old_pos)))
		self.WINDOW.setProperty("%s.%s.EpisodeNo"           	% ('LazyTV', new_pos), self.WINDOW.getProperty("%s.%s.EpisodeNo"           		% ('LazyTV', old_pos)))
		self.WINDOW.setProperty("%s.%s.Season"              	% ('LazyTV', new_pos), self.WINDOW.getProperty("%s.%s.Season"              		% ('LazyTV', old_pos)))
		self.WINDOW.setProperty("%s.%s.Plot"                	% ('LazyTV', new_pos), self.WINDOW.getProperty("%s.%s.Plot"                		% ('LazyTV', old_pos)))
		self.WINDOW.setProperty("%s.%s.TVshowTitle"         	% ('LazyTV', new_pos), self.WINDOW.getProperty("%s.%s.TVshowTitle"         		% ('LazyTV', old_pos)))
		self.WINDOW.setProperty("%s.%s.Rating"              	% ('LazyTV', new_pos), self.WINDOW.getProperty("%s.%s.Rating"              		% ('LazyTV', old_pos)))
		self.WINDOW.setProperty("%s.%s.Runtime"             	% ('LazyTV', new_pos), self.WINDOW.getProperty("%s.%s.Runtime"             		% ('LazyTV', old_pos)))
		self.WINDOW.setProperty("%s.%s.Premiered"           	% ('LazyTV', new_pos), self.WINDOW.getProperty("%s.%s.Premiered"           		% ('LazyTV', old_pos)))
		self.WINDOW.setProperty("%s.%s.Art(thumb)"          	% ('LazyTV', new_pos), self.WINDOW.getProperty("%s.%s.Art(thumb)"          		% ('LazyTV', old_pos)))
		self.WINDOW.setProperty("%s.%s.Art(tvshow.fanart)"  	% ('LazyTV', new_pos), self.WINDOW.getProperty("%s.%s.Art(tvshow.fanart)"  		% ('LazyTV', old_pos)))
		self.WINDOW.setProperty("%s.%s.Art(tvshow.poster)"  	% ('LazyTV', new_pos), self.WINDOW.getProperty("%s.%s.Art(tvshow.poster)"  		% ('LazyTV', old_pos)))
		self.WINDOW.setProperty("%s.%s.Art(tvshow.banner)"  	% ('LazyTV', new_pos), self.WINDOW.getProperty("%s.%s.Art(tvshow.banner)"  		% ('LazyTV', old_pos)))
		self.WINDOW.setProperty("%s.%s.Art(tvshow.clearlogo)"	% ('LazyTV', new_pos), self.WINDOW.getProperty("%s.%s.Art(tvshow.clearlogo)"	% ('LazyTV', old_pos)))
		self.WINDOW.setProperty("%s.%s.Art(tvshow.clearart)" 	% ('LazyTV', new_pos), self.WINDOW.getProperty("%s.%s.Art(tvshow.clearart)" 	% ('LazyTV', old_pos)))
		self.WINDOW.setProperty("%s.%s.Art(tvshow.landscape)"	% ('LazyTV', new_pos), self.WINDOW.getProperty("%s.%s.Art(tvshow.landscape)"	% ('LazyTV', old_pos)))
		self.WINDOW.setProperty("%s.%s.Art(tvshow.characterart)"% ('LazyTV', new_pos), self.WINDOW.getProperty("%s.%s.Art(tvshow.characterart)"	% ('LazyTV', old_pos)))
		self.WINDOW.setProperty("%s.%s.Resume"              	% ('LazyTV', new_pos), self.WINDOW.getProperty("%s.%s.Resume"              		% ('LazyTV', old_pos)))
		self.WINDOW.setProperty("%s.%s.PercentPlayed"       	% ('LazyTV', new_pos), self.WINDOW.getProperty("%s.%s.PercentPlayed"       		% ('LazyTV', old_pos)))
		self.WINDOW.setProperty("%s.%s.Watched"             	% ('LazyTV', new_pos), self.WINDOW.getProperty("%s.%s.Watched"             		% ('LazyTV', old_pos)))
		self.WINDOW.setProperty("%s.%s.File"                	% ('LazyTV', new_pos), self.WINDOW.getProperty("%s.%s.File"                		% ('LazyTV', old_pos)))
		self.WINDOW.setProperty("%s.%s.Path"                	% ('LazyTV', new_pos), self.WINDOW.getProperty("%s.%s.Path"                		% ('LazyTV', old_pos)))
		self.WINDOW.setProperty("%s.%s.Play"                	% ('LazyTV', new_pos), self.WINDOW.getProperty("%s.%s.Play"                		% ('LazyTV', old_pos)))
		self.WINDOW.setProperty("%s.%s.VideoCodec"          	% ('LazyTV', new_pos), self.WINDOW.getProperty("%s.%s.VideoCodec"          		% ('LazyTV', old_pos)))
		self.WINDOW.setProperty("%s.%s.VideoResolution"     	% ('LazyTV', new_pos), self.WINDOW.getProperty("%s.%s.VideoResolution"     		% ('LazyTV', old_pos)))
		self.WINDOW.setProperty("%s.%s.VideoAspect"         	% ('LazyTV', new_pos), self.WINDOW.getProperty("%s.%s.VideoAspect"         		% ('LazyTV', old_pos)))
		self.WINDOW.setProperty("%s.%s.AudioCodec"          	% ('LazyTV', new_pos), self.WINDOW.getProperty("%s.%s.AudioCodec"          		% ('LazyTV', old_pos)))
		self.WINDOW.setProperty("%s.%s.AudioChannels"       	% ('LazyTV', new_pos), self.WINDOW.getProperty("%s.%s.AudioChannels"       		% ('LazyTV', old_pos)))
		self.WINDOW.setProperty("%s.%s.CountEps"       			% ('LazyTV', new_pos), self.WINDOW.getProperty("%s.%s.CountEps"       			% ('LazyTV', old_pos)))
		self.WINDOW.setProperty("%s.%s.CountWatchedEps"       	% ('LazyTV', new_pos), self.WINDOW.getProperty("%s.%s.CountWatchedEps"       	% ('LazyTV', old_pos)))
		self.WINDOW.setProperty("%s.%s.CountUnwatchedEps"       % ('LazyTV', new_pos), self.WINDOW.getProperty("%s.%s.CountUnwatchedEps"       	% ('LazyTV', old_pos)))
		self.WINDOW.setProperty("%s.%s.CountonDeckEps"       	% ('LazyTV', new_pos), self.WINDOW.getProperty("%s.%s.CountonDeckEps"       	% ('LazyTV', old_pos)))


	def test_output(self):
		for x in range(10):
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




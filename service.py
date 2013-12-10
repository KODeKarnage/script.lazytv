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

"""
Launch Monitor class to check for library updates
 add setting to specify how often to run the check in the background

Launch Player class to catch item starts and resume opportunities
 maybe use RequestNextItem as the trigger for both?
Have Default.py announce that it is running a playlist
Then have the Player (once it recognises that default has run) intermittently check if the player is still playing,
and if it isnt, then reset the announcement back to not running
Player checks for that announcement before allowing Resume or Notify


Service = waiting for signal or library update
LazyTV = started by user, random playlist selected, Resume and Notification in settings, sends Signal, sets LTV as active
Signal = [Resume, Notify, Resume Data, Notify Data]
Service = recieves signal, activates Player, provides data from Signal
Player = Notify and/or Resume with provided data, runs until player finishes, then ends setting LTV as inactive
		and lets Service know it can run

XBMC = updates library
Service = checks if LTV is active, if it is then do nothing, once LTV isnt active, wait 10 seconds
		 then generate the Next_List

		= if LTV is not active then generate full Next_List


OnInit for service, set LTV to inactive (this is to account for crashes while playing, where LTV would be left active)



"""

import xbmc
import xbmcgui
import xbmcaddon
import os
import datetime
from resources.lazy_lib import *
from resources.lazy_queries import *



__addon__  = xbmcaddon.Addon()
__addonid__ = __addon__.getAddonInfo('id')
__addonversion__ = __addon__.getAddonInfo('version')
__scriptPath__        = __addon__.getAddonInfo('path')
__profile__ = xbmc.translatePath(__addon__.getAddonInfo('profile'))
__setting__ = __addon__.getSetting


def log(message):
	#if settings['debug']:
	logmsg = '%s: %s' % (__addonid__, message)
	xbmc.log(msg = logmsg, level = xbmc.LOGDEBUG))


class LazyPlayer(xbmc.Player):
	def __init__(self, *args, **kwargs):
		xbmc.Player.__init__(self)

	def onPlayBackStarted(self):
		xbmc.log('PONG! started')

	def onPlayBackEnded(self):
		self.onPlayBackStopped()

	def onPlayBackStopped(self):
		xbmc.log('PONG! Stopped')


class LazyMonitor(xbmc.Monitor):
	def __init__(self, *args, **kwargs):
		# determine how I was called
		# skin will be providing a handle
		# user will be providing nothing
		#if called by skin:
		# 	check if instance already exists
		# 		if no other instance, then continue
		#		if other instance exists, send notification to other instance to service skin then die
		#



		# Set a window property that let's other scripts know we are running (window properties are cleared on XBMC start)
		self.WINDOW.clearProperty('%s_service_running' % __addon__)

		#give any other instance a chance to notice that it must kill itself
		self.initialisation_variables()
		self.WINDOW.setProperty('%s_service_running' % __addon__, 'true')

		#temp notification for testing
		xbmc.executebuiltin('Notification("LazyTV Service has started",20000)')
		xbmc.log(msg=xbmcgui.Window(10000).getProperty('%s_service_running' % __addon__))

		#xbmc.Monitor.__init__(self)

		#_daemon keeps the monitor alive
		self._daemon()	


	def parse_argv(self):
		try:
            params = dict( arg.split( "=" ) for arg in sys.argv[ 1 ].split( "&" ) )
        except:
            params = {}

        self.limit = params.get('limit', 0)
        self.type = params.get('type', 'user')
        self.moniker = params.get('moniker', 'skin')


	def initialisation_variables(self):
		parse_argv()
		self.WINDOW = xbmcgui.Window(10000)
		self.lzplayer = LazyPlayer()
		self.grab_settings()
		self.store_all_show_ids()


	def grab_settings(self):
		self.useSPL = True if__setting__("populate_by") == 'true' else False
		self.multiples = True if __setting__("multipleshows") == 'true' else False
		self.premieres = True if__setting__("premieres")  == 'true' else False
		self.resume = True if__setting__("resume_partials")  == 'true' else False
		self.notifications = True if__setting__("notify")  == 'true' else False
		self.firstrun = True if__setting__("first_run")  == 'true' else False 
		self.pl_length = int(__setting__("length"))
		self.primary = int(__setting__("primary_function"))
		self.sortby = int(__setting__("sort_list_by"))
		self.users_spl = __setting__(users_spl)


	def _daemon(self):
		while not xbmc.abortRequested and WINDOW.getProperty('%s_service_running' % __addon__, 'True') == 'true':
			xbmc.sleep(100)


	def onSettingsChanged(self):

		#update the settings
		self.grab_settings()

		#check if playlist settings have changed
		# if they have then renew the stored showIDs

		#renew the stored showIDs
		self.store_all_show_ids()


	def onDatabaseUpdated(self, database):

		xbmc.sleep(100)

		if database == 'VideoLibrary':

			#renew the stored_show_ids
			self.store_all_show_ids()

			#renew the Next Ep ID List

			#check set of unwatched_shows_list and filtered_shows_list != next_ep_show_list
			#if  it is then take differences and send to Get_Eps_Machine


	def onNotification(self, sender, method, data):

		if method == 'VideoLibrary.OnUpdate':
			# Method 		VideoLibrary.OnUpdate
			# data 			{"item":{"id":1,"type":"episode"},"playcount":4}
			if 'item' in data:
				if 'playcount' in data:
					if 'type' in data['item']:
						if data['item']['type'] == 'episode':
							if data['playcount'] < 2:
								pass
								#get showID and re-run getnextepisode for that show

		elif method == 'Player.OnPlay':
			# Method 		Player.OnPlay
			# data 			{"item":{"id":1,"type":"episode"},"player":{"playerid":1,"speed":1}}
			if 'item' in data:
				if 'type' in data['item']:
					if data['item']['type'] == 'episode':
						if 'player' in data:
							pass
							#show notification if set

		elif method = 'VideoLibrary.OnScanFinished':
			# Method 		VideoLibrary.OnScanFinished
			# covered by onDatabaseUpdated
			pass
			#renew the stored_show_ids
			#self.store_all_show_ids()



	def store_all_show_ids(self):

		self.result = json_query(show_request, True)

		if 'tvshows' not in self.result:

			self.unwatched_shows_list = []

		else:

			self.unwatched_shows_list = [key for key in self.result['tvshows'].keys()]

		self.WINDOW.setProperty('%s_unwatched_shows_list' % __addon__, self.unwatched_shows_list)



	def get_eps(self, limit = 0, showids = [], caller_handle = 'none', type = 'latest_watched'):
		
		# called whenever the Next_Eps stored in 10000 need to be updated
		# determines the next ep for the showids it is sent and saves the info to 10000

		for show in showids:
			self.eps_query['params']['tvshowid'] = show
			self.ep = json_query(eps_query, True)

			#accounts for the query not returning any TV shows
			if 'episodes' not in self.ep:
				continue
				#failed no episodes available
			else:
				self.eps = self.ep['episodes']

			#creates a list of episodes for the show that have been watched
			self.played_eps = [x for x in self.eps if x['playcount'] is not 0]

			if not self.played_eps:
				#if the show doesnt have any watched episodes, the season and episode are both zero
				self.Season  = 0
				self.Episode = 0
				self.last_watched = ''

			else:
				#the last played episode is the one with the highest season number and then the highest episode number
				self.last_played_ep = sorted(self.played_eps, key =  lambda played_eps: (self.played_eps['season'], self.played_eps['episode']), reverse=True)[0]
				self.Season = self.last_played_ep['season']
				self.Episode = self.last_played_ep['episode']
				self.last_watched = self.last_played_ep['lastwatched']

			#uses the season and episode number to create a list of unwatched shows newer than the last watched one
			self.unplayed_eps = [x for x in eps if ((x['season'] == self.Season and x['episode'] > self.Episode) or (x['season'] > self.Season))]

			#sorts the list of unwatched shows by lowest season and lowest episode, filters the list to remove empty strings
			self.next_ep = sorted(self.unplayed_eps, key = lambda unplayed_eps: (uself.nplayed_eps['season'], self.unplayed_eps['episode']))
			self.next_ep = filter(None, self.next_ep)







if ( __name__ == "__main__" ):

	log(' %s started' % __addonversion__)

	LazyMonitor()
	del LazyMonitor
	del LazyPlayer

	log(' %s stopped' % __addonversion__)


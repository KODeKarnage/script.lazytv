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


def log(message):
	logmsg       = '%s: %s' % (__addonid__, message)
	xbmc.log(msg = logmsg)


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

		self.initialisation_variables()

		# Set a window property that let's other scripts know we are running (window properties are cleared on XBMC start)
		self.WINDOW.clearProperty('%s_service_running' % __addon__)

		#give any other instance a chance to notice that it must kill itself

		self.WINDOW.setProperty('%s_service_running' % __addon__, 'true')

		#temp notification for testing
		xbmc.executebuiltin('Notification("LazyTV Service has started",20000)')
		xbmc.log(msg=self.WINDOW.getProperty('%s_service_running' % __addon__))

		#xbmc.Monitor.__init__(self)

		#gets the beginning list of unwatched shows
		self.get_eps(showids = self.unwatched_shows_list)

		#_daemon keeps the monitor alive
		self._daemon()


	def parse_argv(self):
		try:
			params = dict( arg.split( "=" ) for arg in sys.argv[ 1 ].split( "&" ) )
		except:
			params = {}
		self.limit   = params.get('limit', 0)
		self.type    = params.get('type', 'lastwatched')

	def initialisation_variables(self):
		self.parse_argv()
		self.WINDOW   = xbmcgui.Window(10000)
		self.lzplayer = LazyPlayer()
		self.grab_settings()
		self.store_all_show_ids()
		self.nepl = []
		self.WINDOW.setProperty('%s_next_ep_list' % __addon__,'[]']


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
		while not xbmc.abortRequested and self.WINDOW.getProperty('%s_service_running' % __addon__) == 'true':
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
								#what if last show is now watched
								#what if last show watched and previous show unwatched
								#what if user changed watched status of previous show
								#what if user set last show to unwatched

		elif method == 'Player.OnPlay':
			# Method 		Player.OnPlay
			# data 			{"item":{"id":1,"type":"episode"},"player":{"playerid":1,"speed":1}}
			if 'item' in data:
				if 'type' in data['item']:
					if data['item']['type'] == 'episode':
						if 'player' in data:
							pass
							#show notification if set
							#probably not needed, addon can take care of notification

		elif method == 'VideoLibrary.OnScanFinished':
			# Method 		VideoLibrary.OnScanFinished
			# covered by onDatabaseUpdated
			pass
			#renew the stored_show_ids
			self.store_all_show_ids()
			#find new show entries, get the episodes

		#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
		#@@@@@@@@@@
		#@@@@@@@@@@ HOW TO DETERMINE WHEN A SHOW NEEDS TO BE UPDATED ON SCAN FINISHED?
		#@@@@@@@@@@
		#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@


		#		NEW SHOW ADDED
		#		new episode available

	def store_all_show_ids(self):

		self.result = json_query(show_request, True)
		if 'tvshows' not in self.result:
			self.unwatched_shows_list = []
		else:
			self.unwatched_shows_list = [id['tvshowid'] for id in self.result['tvshows']]



	def get_eps(self, limit = 0, showids = [], type = 'latest_watched'):

		# called whenever the Next_Eps stored in 10000 need to be updated
		# determines the next ep for the showids it is sent and saves the info to 10000
		log('get_eps started')

		self.orig_shows = []
		self.count = 0

		#gets stored show id list NO LONGER NEEDED
		#self.nepl = ast.literal_eval(self.WINDOW.getProperty('%s_next_ep_list' % __addon__))

		#creates single list of showids; those in the requested list, and those in the existing stored id list
		self.comb_showids = list(set([x[1] for x in self.nepl).union(set(showids)))

		#inserts original order, creates list of original shows, these two lists are in sync
		for x in range(len(self.nepl)):
			self.nepl[x].insert(3, x)
			self.orig_shows.insert(len(self.orig_shows), self.nepl[1])




		#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
		#@@@@@@@@@@
		#@@@@@@@@@@ NEED TO HAVE THIS GRAB THE X LAST WATCHED AND THEN FILL WITH RANDOM
		#@@@@@@@@@@
		#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@

		#gets showids and last watched
		self.lshowsR = json_query(show_request_lw, True)
		if 'tvshows' not in self.lshowsR:
			return

		self.lshows               = self.lshowsR['tvshows']
		self.show_lw              = [[self.day_conv(x['lastplayed']),x['tvshowid']] for x in self.lshows if x['tvshowid'] in showids]
		self.show_lw.sort(reverse =True)
		self.truelim              = min(len(self.show_lw),limit) if limit != 0 else len(self.show_lw)

		#this list is now ordered by last watched and is limited to the x most recent
		self.final_showids        = self.show_lw[0:self.truelim]

		#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
		#@@@@@@@@@@
		#@@@@@@@@@@ THIS SHOULD JUST BE PROCESSING THE SENT SHOWIDS
		#@@@@@@@@@@
		#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@

		#process the list of shows
		for show in self.final_showids:

			#query grabs the TV show episodes
			eps_query['params']['tvshowid'] = show[1]
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
				self.Season       = 0
				self.Episode      = 0
				self.last_watched = 0

			else:
				#the last played episode is the one with the highest season number and then the highest episode number
				self.last_played_ep = sorted(self.played_eps, key =  lambda played_eps: (played_eps['season'], played_eps['episode']), reverse=True)[0]
				self.Season         = self.last_played_ep['season']
				self.Episode        = self.last_played_ep['episode']
				self.last_watched   = show[0]

			#uses the season and episode number to create a list of unwatched shows newer than the last watched one
			self.unplayed_eps = [x for x in self.eps if ((x['season'] == self.Season and x['episode'] > self.Episode) or (x['season'] > self.Season))]

			#sorts the list of unwatched shows by lowest season and lowest episode, filters the list to remove empty strings
			self.next_ep = sorted(self.unplayed_eps, key = lambda unplayed_eps: (unplayed_eps['season'], unplayed_eps['episode']))
			self.next_ep = filter(None, self.next_ep)

			#post the ep info to the log
			log(self.next_ep)

			#check if the show is in original_list
			if self.next_ep['episodeid'] in self.orig_shows:
				#replace last watched stat and order metric
				self.indrem = self.orig_shows.index(self.next_ep['episodeid'])
				self.nepl.pop(self.indrem)
				self.new_entry = [show[0], show[1], 'lz%s' % count]
				self.nepl.insert(self.indrem, self.new_entry)
			else:
				#add new entry to the end of the original list
				self.new_entry = [show[0], show[1], 'lz%s' % count]
				self.nepl.append(self.new_entry)

			#load the data into 10000
			self.store_next_ep(self.next_ep['episodeid'], 'lz%s' % count)

		#now that the shows are all added to 10000, prepare to fix the labels
		#sort the list by last watched
		self.nepl.sort(reverse=True)		# [lastwatched, showid, original position]




		#create a dict with {new_pos : old_pos}
		self.new_pos = {}
		#create list of tuples of old position and new position
		for x in range(len(self.nepl)):
			if x == self.nepl[x][2]:
				pass
			else:
				self.new_pos[x] = self.nepl[x][2]   	#	{new_pos:old_pos}

		#get the positions, old and new from nepl,
		self.all_pos = [x[2] for x in self.nepl]
		self.available_slots = list(set(range(self.nepl)).difference(set[self.all_pos]))

		while self.available_slots:
			#grab an empty slot, remove it from available slots
			self.popped_slot = self.available_slots.pop()
			#find the entry for that slot, send to Reassignment
			self.reassign(self.popped_slot, self.new_pos[self.popped_slot])
			#add the vacated slot to available slots
			self.available_slots.append(self.new_pos[self.popped_slot])


	def reassign(self, new_pos,old_pos):
		self.WINDOW.setProperty("%s.%d.DBID"                % ('LazyTV', new_pos), self.WINDOW.getProperty("%s.%d.DBID"                % ('LazyTV', old_pos)))
		self.WINDOW.setProperty("%s.%d.Title"               % ('LazyTV', new_pos), self.WINDOW.getProperty("%s.%d.Title"               % ('LazyTV', old_pos)))
		self.WINDOW.setProperty("%s.%d.Episode"             % ('LazyTV', new_pos), self.WINDOW.getProperty("%s.%d.Episode"             % ('LazyTV', old_pos)))
		self.WINDOW.setProperty("%s.%d.EpisodeNo"           % ('LazyTV', new_pos), self.WINDOW.getProperty("%s.%d.EpisodeNo"           % ('LazyTV', old_pos)))
		self.WINDOW.setProperty("%s.%d.Season"              % ('LazyTV', new_pos), self.WINDOW.getProperty("%s.%d.Season"              % ('LazyTV', old_pos)))
		self.WINDOW.setProperty("%s.%d.Plot"                % ('LazyTV', new_pos), self.WINDOW.getProperty("%s.%d.Plot"                % ('LazyTV', old_pos)))
		self.WINDOW.setProperty("%s.%d.TVshowTitle"         % ('LazyTV', new_pos), self.WINDOW.getProperty("%s.%d.TVshowTitle"         % ('LazyTV', old_pos)))
		self.WINDOW.setProperty("%s.%d.Rating"              % ('LazyTV', new_pos), self.WINDOW.getProperty("%s.%d.Rating"              % ('LazyTV', old_pos)))
		self.WINDOW.setProperty("%s.%d.Runtime"             % ('LazyTV', new_pos), self.WINDOW.getProperty("%s.%d.Runtime"             % ('LazyTV', old_pos)))
		self.WINDOW.setProperty("%s.%d.Premiered"           % ('LazyTV', new_pos), self.WINDOW.getProperty("%s.%d.Premiered"           % ('LazyTV', old_pos)))
		self.WINDOW.setProperty("%s.%d.Art(thumb)"          % ('LazyTV', new_pos), self.WINDOW.getProperty("%s.%d.Art(thumb)"          % ('LazyTV', old_pos)))
		self.WINDOW.setProperty("%s.%d.Art(tvshow.fanart)"  % ('LazyTV', new_pos), self.WINDOW.getProperty("%s.%d.Art(tvshow.fanart)"  % ('LazyTV', old_pos)))
		self.WINDOW.setProperty("%s.%d.Art(tvshow.poster)"  % ('LazyTV', new_pos), self.WINDOW.getProperty("%s.%d.Art(tvshow.poster)"  % ('LazyTV', old_pos)))
		self.WINDOW.setProperty("%s.%d.Art(tvshow.banner)"  % ('LazyTV', new_pos), self.WINDOW.getProperty("%s.%d.Art(tvshow.banner)"  % ('LazyTV', old_pos)))
		self.WINDOW.setProperty("%s.%d.Art(tvshow.clearlogo)"% ('LazyTV', new_pos), self.WINDOW.getProperty("%s.%d.Art(tvshow.clearlogo)"% ('LazyTV', old_pos)))
		self.WINDOW.setProperty("%s.%d.Art(tvshow.clearart)" % ('LazyTV', new_pos), self.WINDOW.getProperty("%s.%d.Art(tvshow.clearart)" % ('LazyTV', old_pos)))
		self.WINDOW.setProperty("%s.%d.Art(tvshow.landscape)"% ('LazyTV', new_pos), self.WINDOW.getProperty("%s.%d.Art(tvshow.landscape)"% ('LazyTV', old_pos)))
		self.WINDOW.setProperty("%s.%d.Art(tvshow.characterart)"% ('LazyTV', new_pos), self.WINDOW.getProperty("%s.%d.Art(tvshow.characterart)"% ('LazyTV', old_pos)))
		self.WINDOW.setProperty("%s.%d.Resume"              % ('LazyTV', new_pos), self.WINDOW.getProperty("%s.%d.Resume"              % ('LazyTV', old_pos)))
		self.WINDOW.setProperty("%s.%d.PercentPlayed"       % ('LazyTV', new_pos), self.WINDOW.getProperty("%s.%d.PercentPlayed"       % ('LazyTV', old_pos)))
		self.WINDOW.setProperty("%s.%d.Watched"             % ('LazyTV', new_pos), self.WINDOW.getProperty("%s.%d.Watched"             % ('LazyTV', old_pos)))
		self.WINDOW.setProperty("%s.%d.File"                % ('LazyTV', new_pos), self.WINDOW.getProperty("%s.%d.File"                % ('LazyTV', old_pos)))
		self.WINDOW.setProperty("%s.%d.Path"                % ('LazyTV', new_pos), self.WINDOW.getProperty("%s.%d.Path"                % ('LazyTV', old_pos)))
		self.WINDOW.setProperty("%s.%d.Play"                % ('LazyTV', new_pos), self.WINDOW.getProperty("%s.%d.Play"                % ('LazyTV', old_pos)))
		self.WINDOW.setProperty("%s.%d.VideoCodec"          % ('LazyTV', new_pos), self.WINDOW.getProperty("%s.%d.VideoCodec"          % ('LazyTV', old_pos)))
		self.WINDOW.setProperty("%s.%d.VideoResolution"     % ('LazyTV', new_pos), self.WINDOW.getProperty("%s.%d.VideoResolution"     % ('LazyTV', old_pos)))
		self.WINDOW.setProperty("%s.%d.VideoAspect"         % ('LazyTV', new_pos), self.WINDOW.getProperty("%s.%d.VideoAspect"         % ('LazyTV', old_pos)))
		self.WINDOW.setProperty("%s.%d.AudioCodec"          % ('LazyTV', new_pos), self.WINDOW.getProperty("%s.%d.AudioCodec"          % ('LazyTV', old_pos)))
		self.WINDOW.setProperty("%s.%d.AudioChannels"       % ('LazyTV', new_pos), self.WINDOW.getProperty("%s.%d.AudioChannels"       % ('LazyTV', old_pos)))


	def store_next_ep(self,episodeid,place):
		#stores the episode info into 10000
		#get show info, load into 10000
		#determine correct position of item
		#change EP ORDER DICT to reflect new order.
		#EP ORDER DICT is a dictionary (or list of tuples or lists) saved in the service that records the order of the last watched shows,
		#it is used to keep the stored eps in order, and to determine how many shows have been added

		if not xbmc.abortRequested:
			ep_details_query = ep_details_query['params']['episodeid'] = episodeid
			ep_details = json_query(ep_details_query, True)

			if ep_details.has_key('episodedetails'):

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

                '''		NEED TO CONSIDER THIS
                play = 'XBMC.RunScript(' + __addonid__ + ',episodeid=' + str(ep_details.get('episodeid')) + ')' '''
                play = ''
                streaminfo = media_streamdetails(ep_details['file'].encode('utf-8').lower(),
                                                 ep_details['streamdetails'])

                self.WINDOW.setProperty("%s.%d.DBID"                % ('LazyTV', place), str(ep_details.get('episodeid')))
                self.WINDOW.setProperty("%s.%d.Title"               % ('LazyTV', place), ep_details['title'])
                self.WINDOW.setProperty("%s.%d.Episode"             % ('LazyTV', place), episode)
                self.WINDOW.setProperty("%s.%d.EpisodeNo"           % ('LazyTV', place), episodeno)
                self.WINDOW.setProperty("%s.%d.Season"              % ('LazyTV', place), season)
                self.WINDOW.setProperty("%s.%d.Plot"                % ('LazyTV', place), plot)
                self.WINDOW.setProperty("%s.%d.TVshowTitle"         % ('LazyTV', place), ep_details['showtitle'])
                self.WINDOW.setProperty("%s.%d.Rating"              % ('LazyTV', place), rating)
                self.WINDOW.setProperty("%s.%d.Runtime"             % ('LazyTV', place), str(int((ep_details['runtime'] / 60) + 0.5)))
                self.WINDOW.setProperty("%s.%d.Premiered"           % ('LazyTV', place), ep_details['firstaired'])
                self.WINDOW.setProperty("%s.%d.Art(thumb)"          % ('LazyTV', place), art.get('thumb',''))
                self.WINDOW.setProperty("%s.%d.Art(tvshow.fanart)"  % ('LazyTV', place), art.get('tvshow.fanart',''))
                self.WINDOW.setProperty("%s.%d.Art(tvshow.poster)"  % ('LazyTV', place), art.get('tvshow.poster',''))
                self.WINDOW.setProperty("%s.%d.Art(tvshow.banner)"  % ('LazyTV', place), art.get('tvshow.banner',''))
                self.WINDOW.setProperty("%s.%d.Art(tvshow.clearlogo)"% ('LazyTV', place), art.get('tvshow.clearlogo',''))
                self.WINDOW.setProperty("%s.%d.Art(tvshow.clearart)" % ('LazyTV', place), art.get('tvshow.clearart',''))
                self.WINDOW.setProperty("%s.%d.Art(tvshow.landscape)"% ('LazyTV', place), art.get('tvshow.landscape',''))
                self.WINDOW.setProperty("%s.%d.Art(tvshow.characterart)"% ('LazyTV', place), art.get('tvshow.characterart',''))
                self.WINDOW.setProperty("%s.%d.Resume"              % ('LazyTV', place), resume)
                self.WINDOW.setProperty("%s.%d.PercentPlayed"       % ('LazyTV', place), played)
                self.WINDOW.setProperty("%s.%d.Watched"             % ('LazyTV', place), watched)
                self.WINDOW.setProperty("%s.%d.File"                % ('LazyTV', place), ep_details['file'])
                self.WINDOW.setProperty("%s.%d.Path"                % ('LazyTV', place), path)
                self.WINDOW.setProperty("%s.%d.Play"                % ('LazyTV', place), play)
                self.WINDOW.setProperty("%s.%d.VideoCodec"          % ('LazyTV', place), streaminfo['videocodec'])
                self.WINDOW.setProperty("%s.%d.VideoResolution"     % ('LazyTV', place), streaminfo['videoresolution'])
                self.WINDOW.setProperty("%s.%d.VideoAspect"         % ('LazyTV', place), streaminfo['videoaspect'])
                self.WINDOW.setProperty("%s.%d.AudioCodec"          % ('LazyTV', place), streaminfo['audiocodec'])
                self.WINDOW.setProperty("%s.%d.AudioChannels"       % ('LazyTV', place), str(streaminfo['audiochannels']))
            del ep_details


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












	def day_conv(self, date_string):
		self.op_format = '%Y-%m-%d %H:%M:%S'
		self.lw        = time.strptime(date_string, self.op_format)
		self.lw_max    = datetime.datetime(self.lw[0],self.lw[1],self.lw[2],self.lw[3],self.lw[4],self.lw[5])
		self.date_num  = time.mktime(self.lw_max.timetuple())
		return self.date_num




if ( __name__ == "__main__" ):

	log(' %s started' % __addonversion__)

	LazyMonitor()
	del LazyMonitor
	del LazyPlayer

	log(' %s stopped' % __addonversion__)




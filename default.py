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

import random
import xbmcgui
import xbmcaddon
import time
import datetime
import sys
import os
import ast
from resources.lazy_lib import *
from resources.lazy_queries import *

#####################################################################################################
###
###				CURRENTLY WORKING ON
###		- LazyTV SERVICE for 'resume in playlist' and 'notification in playlist' functions
###		- service to also maintain a watch list in cache and update on library updates
###		- need to maintain next 3 or 4 to watch to account for multiples
###		- change default.py to make the first itme in the playlist the latest 'Resume'
###		- call settings only when needed (initialisation is taking too long on Pi)
###
#####################################################################################################

#sys.stdout = open('C:\\Temp\\test.txt', 'w')




bug_exists = False #Buggalo
try:
	__buggalo__    = xbmcaddon.Addon("script.module.buggalo")
	_bugversion_ = __buggalo__.getAddonInfo("version")
	bv = _bugversion_.split(".")
	bvtup = (bv[0],bv[1],bv[2])
	if bvtup > (1,1,3):
		import buggalo
		bug_exists = True
except:
	pass

__addon__        = xbmcaddon.Addon()
__addonid__      = __addon__.getAddonInfo('id')
__setting__       = __addon__.getSetting
lang              = __addon__.getLocalizedString
dialog            = xbmcgui.Dialog()
scriptPath        = __addon__.getAddonInfo('path')
settings, IGNORES = get_settings()

WINDOW   = xbmcgui.Window(10000)

__resource__      =  os.path.join(scriptPath, 'resources', 'lib')

sys.path.append(__resource__)
start_time       = time.time()
base_time        = time.time()
primary_function = __setting__('primary_function')
populate_by = __setting__('populate_by')
select_pl = __setting__('select_pl')
default_playlist = __setting__('file')


def log(message):
	global start_time
	global base_time
	new_time = time.time()
	gap_time = "%5f" % (new_time - start_time)
	start_time = new_time
	total_gap = "%5f" % (new_time - base_time)
	logmsg       = '%s : %s :: %s ::: %s ' % (__addonid__+'addon', total_gap, gap_time, message)
	xbmc.log(msg = logmsg)

def gracefail(message):
	dialog.ok("LazyTV",message)
	sys.exit()

log('entered')

def playlist_selection_window():
	#Purpose: launch Select Window populated with smart playlists

	plf = {"jsonrpc": "2.0", "method": "Files.GetDirectory", "params": {"directory": "special://profile/playlists/video/", "media": "video"}, "id": 1}
	playlist_files = json_query(plf, True)['files']

	if playlist_files != None:

		plist_files   = dict((x['label'],x['file']) for x in playlist_files)
		playlist_list =  plist_files.keys()

		playlist_list.sort()
		inputchoice = xbmcgui.Dialog().select(lang(32048), playlist_list)

		return plist_files[playlist_list[inputchoice]]
	else:
		return 'empty'

def day_calc(date_string, todate, output):
	op_format = '%Y-%m-%d %H:%M:%S'
	lw = time.strptime(date_string, op_format)
	if output == 'diff':
		lw_date = datetime.date(lw[0],lw[1],lw[2])
		day_string = str((todate - lw_date).days) + " days)"
		return day_string
	else:
		lw_max = datetime.datetime(lw[0],lw[1],lw[2],lw[3],lw[4],lw[5])
		date_num = time.mktime(lw_max.timetuple())
		return date_num



'''def smart_playlist_showids(raw_playlist):

	log('rawpl ' + str(raw_playlist))
	pl_file = os.path.split(raw_playlist)
	log('plfile  ' +str(pl_file[1]))

	new_path = os.path.join('special://videoplaylists',pl_file)

	playlist = xbmc.translatePath(new_path)

	# derive playlist_showids from smart playlist
	#retrieve the shows in the supplied playlist, save their ids to a list
	plf['params']['directory'] = playlist
	log(plf)
	playlist_contents = json_query(plf, True)


	if 'files' not in playlist_contents:
		gracefail(lang(32205))
	else:
		if not playlist_contents['files']:
			gracefail(lang(32205))
		else:
			for x in playlist_contents['files']:
				playlist_showids = [x['id'] for x in playlist_contents['files'] if x['type'] == 'tvshow']
			if not playlist_showids:
				gracefail(lang(32206))

	#returns the list of all and filtered shows and episodes
	return playlist_showids'''


length = int(__setting__('length'))					#DONE
multipleshows = __setting__('multipleshows')		#DONE
premieres = __setting__('premieres')				#DONE
resume_partials = __setting__('resume_partials')	#HANDLE IN SERVICE OR THROUGH PLAYER CLASS


def random_playlist(selected_pl):


	if premieres == 'false':
		nepl_raw = WINDOW.getProperty("%s.nepl"	% ('LazyTV'))
		nepl = ast.literal_eval(nepl_raw)
		new_show_list = []
		for x in range(len(nepl)):
			if WINDOW.getProperty("%s.%s.EpisodeID"  % ('LazyTV', x)) != 's01e01':
				new_show_list.append(nepl[x][1])
		if selected_pl == 'null':
			selected_pl = new_show_list
		else:
			selected_pl = list(set(selected_pl).intersection(set(new_show_list)))

	process_stored(selected_pl)

	#clear the existing playlist
	clear_playlist = {"jsonrpc": "2.0","method": "Playlist.Clear","params": {"playlistid": 1},"id": "1"}
	json_query(clear_playlist, False)

	added_ep_dict = {}

	count = 0

	while count < length and count <= len(stored_episodes) and stored_showids:  		#while the list isnt filled

		R = random.randint(0,len(stored_episodes) - 1)									#get random number

		if premieres == 'false':
			if self.WINDOW.getProperty("%s.%s.EpisodeNo" % ('LazyTV', R)) == 's01e01':	#if desired, ignore s01e01
				continue

		if multipleshows == 'true' and stored_showids[R] in added_ep_dict.keys():		#check added_ep list if multiples allowed
			tmp_episode_id = next_show_engine(showid=stored_episodes[R],Season=added_ep_dict[stored_episodes[R]][0],Episode=added_ep_dict[stored_episodes[R]][1])
			if tmp_episode_id == 'null':
				continue
		else:
			tmp_episode_id = stored_episodes[R]

		#add episode to playlist
		add_this_ep = { 'jsonrpc' : '2.0', 'method' : 'Playlist.Add', 'id' : 1, 'params' : {'item' : {'episodeid' : int(tmp_episode_id) }, 'playlistid' : 1}}
		json_query(add_this_ep, False)


		#check if multipleshows allowed
		if multipleshows == 'true':
			added_ep_dict[stored_showids[R]] = [self.WINDOW.getProperty("%s.%s.Season" % ('LazyTV', R)), self.WINDOW.getProperty("%s.%s.Episode" % ('LazyTV', R))]
		else:
			# remove show from stored_episodes

			del stored_showids[R]
			del stored_lw[R]
			del stored_positions[R]
			del stored_episodes[R]

		count += 1
	xbmc.Player().play(xbmc.PlayList(1))




def next_show_engine(showid, eps = [], Season = 'null', Episode = 'null'):

	if not eps:
		eps_query = '{"jsonrpc": "2.0","method": "VideoLibrary.GetEpisodes","params": {"properties": ["season","episode","runtime","resume","playcount","tvshowid","lastplayed","file"],"tvshowid": %i },"id": "1"}' % int(showid)
		ep = json_query(eps_query, True)				# query grabs the TV show episodes

		if 'episodes' not in ep: 						#ignore show if show has no episodes
			return 'null'
		else:
			eps = ep['episodes']

	#uses the season and episode number to create a list of unwatched shows newer than the last watched one
	unplayed_eps = [x for x in eps if ((x['season'] == Season and x['episode'] > Episode) or (x['season'] > Season))]

	#sorts the list of unwatched shows by lowest season and lowest episode, filters the list to remove empty strings
	next_ep = sorted(unplayed_eps, key = lambda unplayed_eps: (unplayed_eps['season'], unplayed_eps['episode']))
	next_ep = filter(None, next_ep)

	if not next_ep:
		return null
	elif 'episodeid' not in next_ep[0]:
		return null
	else:
		return next_ep[0]['episodeid']


def create_playlist():
	#creates a random playlist of unwatched episodes

	#clears the playlist
	json_query(clear_playlist, False)

	#generates the show and episode lists
	playlist_showids, all_shows = populate_by_x()

	#updates progross dialog

	#notifies the user when there is no shows in the show list
	if not playlist_showids and partial_exists == False:
		dialog.ok('LazyTV', lang(32150))

	#loop to add more files to the playlist, the loop carries on until the playlist is full or not shows are left in the show list
	while itera in range((settings['playlist_length']-1) if partial_exists == True else settings['playlist_length']):

		#counts the number of shows in the showlist, if it is ever empty, the loop ends
		show_count = len(playlist_showids)
		if show_count == 0 or not playlist_showids:
			itera = 10000

		else:

			#selects a show at random from the show list
			R = random.randint(0,show_count - 1)
			SHOWID = playlist_showids[R]

			#gets the details of that show and the shows episodes
			this_show = [x for x in all_shows if x['tvshowid'] == SHOWID][0]

			eps_query['params']['tvshowid'] = SHOWID
			ep = json_query(eps_query, True)

			#accounts for the query not returning any TV shows
			if 'episodes' not in ep:
				gracefail(lang(32203))
			else:
				eps = ep['episodes']

			#ascertains the appropriate season and episode number of the last watched show
			if SHOWID in playlist_tally:

				#if the show is already in the tally, then use that entry as the last show watched
				Season  = playlist_tally[SHOWID][0]
				Episode = playlist_tally[SHOWID][1]

			elif this_show['watchedepisodes'] == 0:
				#if the show doesnt have any watched episodes, the season and episode are both zero
				Season  = 0
				Episode = 0

			else:
				#creates a list of episodes for the show that have been watched
				played_eps = [x for x in eps if x['playcount'] is not 0 and x['tvshowid'] == SHOWID]

				#the last played episode is the one with the highest season number and then the highest episode number
				last_played_ep = sorted(played_eps, key =  lambda played_eps: (played_eps['season'], played_eps['episode']), reverse=True)[0]
				Season = last_played_ep['season']
				Episode = last_played_ep['episode']

			#uses the season and episode number to create a list of unwatched shows newer than the last watched one
			unplayed_eps = [x for x in eps if ((x['season'] == Season and x['episode'] > Episode)
			or (x['season'] > Season)) and x['tvshowid'] == SHOWID]

			#sorts the list of unwatched shows by lowest season and lowest episode, filters the list to remove empty strings
			next_ep = sorted(unplayed_eps, key = lambda unplayed_eps: (unplayed_eps['season'], unplayed_eps['episode']))
			next_ep = filter(None, next_ep)

			#if there is no next episode then remove the show from the show list, and start again
			#removes the next_ep if it is the first in the series and premieres arent wanted,
			#or the show is partially watched and expartials is true
			if not next_ep or (Season == 1 and Episode == 1 and settings['premieres'] == 'false') or (settings['expartials'] == 'true' and next_ep[0]['resume']['position'] == 0):
				playlist_showids = [x for x in playlist_showids if x != SHOWID]
			else:
				next_ep = next_ep[0]

				#creates safe version of next episode
				clean_next_ep = next_ep

				#cleans the name, letters such as à were breaking the search for .strm in the name
				dirty_name = clean_next_ep['file']
				clean_name = fix_name(dirty_name).lower()

				#only processes files that arent streams or that are streams but the user has specified that that is ok and either it isnt the first entry in the list or there is already a partial running
				if ".strm" not in clean_name or (".strm" in clean_name and settings['streams'] == 'true'):# and (itera != 0 or partial_exists == True)):

					#adds the file to the playlist
					json_query(dict_engine(next_ep['episodeid'],'episodeid'), False)

					#if the user doesnt want multiples then the file is removed from the list, otherwise the episode is added to the tally list
					if settings['multiples'] == 'false':
						playlist_showids = [x for x in playlist_showids if x != SHOWID]
					else:
						playlist_tally[SHOWID] = (next_ep['season'],next_ep['episode'])

					#starts the player if this is the first entry, seeks to the right point if resume selected
					if itera == 0 and ".strm" not in clean_name:

						norm_start = True
						xbmc.Player().play(xbmc.PlayList(1))

						if settings['resume_partials'] == 'true' and next_ep['resume']['total'] != 0:

							#IF RESUMES WANTED THEN CHECK IF THIS IS A RESUME, IF IT IS THEN SEEK TO THE APPROPRIATE LOCATION
							#jumps to resume point of the partial

							seek_percent = float(next_ep['resume']['position'])/float(next_ep['resume']['total'])*100.0

							seek['params']['value'] = seek_percent

							json_query(seek, False)

					elif next_ep['resume']['position'] != 0 and settings['resume_partials'] == 'true':
						show_key = str(this_show['title']) + 'S' + str(next_ep['season']) + 'E' + str(next_ep['episode'])
						resume_dict[show_key] = float(next_ep['resume']['position'])/float(next_ep['resume']['total'])*100.0

					if ".strm" in clean_name:
						plist_has_strm = True

					#records a file was added to the playlist
					itera +=1

				#if the next episode is a stream and the user doesnt want streams, the show is removed from the show list
				elif ".strm" in clean_name and settings['streams'] == 'false':
					playlist_showids = [x for x in playlist_showids if x != SHOWID]

				#records that he loop has completed one more time
				cycle +=1

				#infinite loop escape, is triggered if the cycle has run 100 times and streams are not allowed or there hasnt been anything added to the playlist
				#this may occur if all episodes of all shows are strms and strms are not permitted
				#if all the shows are streams, then exit the loop, otherwise, keep trying another 100 times
				if cycle % 100 == 0 and _checked == False and (settings['streams'] == 'false' or itera == 0):
					#confirm all eps are streams
					check_eps = [fix_name(x['file']) for x in eps if x['tvshowid'] in playlist_showids]
					if all(".strm" in ep.lower() for ep in check_eps):
						itera = 1000
					_checked = True


	if itera != 0:
		if not plist_has_strm and (settings['notify'] == 'true' or settings['resume_partials'] == 'true'):
			play_monitor = MyPlayer()

			while not xbmc.abortRequested and play_monitor.player_active:
				xbmc.sleep(100)

		elif norm_start:
			pass
		else:
			xbmc.Player().play(xbmc.PlayList(1))


	#print 'final end'


class MyPlayer(xbmc.Player):
	def __init__(self, *args, **kwargs):
		xbmc.Player.__init__(self)
		self.player_active = True
		self.send_notification()

	def onPlayBackEnded(self):
		xbmc.sleep(100)
		self.now_name = xbmc.getInfoLabel('VideoPlayer.TVShowTitle')
		if self.now_name == '':
			xbmc.executebuiltin('ActivateWindow(10028)')
			self.player_active = False

	def onPlayBackStopped(self):
		self.onPlayBackEnded()

	def onPlayBackStarted(self):
		self.send_notification()

	def send_notification(self):
		xbmc.sleep(100)
		self.now_name = xbmc.getInfoLabel('VideoPlayer.TVShowTitle')
		if self.now_name == '':
			self.player_active = False
		else:
			self.now_season  = xbmc.getInfoLabel('VideoPlayer.Season')
			self.now_episode = xbmc.getInfoLabel('VideoPlayer.Episode')

			if settings['resume_partials'] == 'true':
				now_key = self.now_name + 'S' + self.now_season +'E' + self.now_episode
				if now_key in resume_dict.keys():
					seek['params']['value'] = resume_dict[now_key]
					json_query(seek, False)

			if settings['notify'] == 'true':
				if len(self.now_season)==1:
					self.now_season = '0' + self.now_season
				if len(self.now_episode)==1:
					self.now_episode = '0' + self.now_episode
				xbmc.executebuiltin('Notification("Now Playing",%s S%sE%s,%i)' % (self.now_name,self.now_season,self.now_episode,5000))


class xGUI(xbmcgui.WindowXMLDialog):

	def onInit(self):

		self.ok = self.getControl(5)
		self.ok.setLabel(lang(32106))

		self.hdg = self.getControl(1)
		self.hdg.setLabel('LazyTV')
		self.hdg.setVisible(True)

		self.ctrl6failed = False

		try:
			self.name_list = self.getControl(6)

			self.x = self.getControl(3)
			self.x.setVisible(False)

		except:
			self.ctrl6failed = True  #for some reason control3 doesnt work for me, so this work around tries control6
			self.close()			 #and exits if it fails, CTRL6FAILED then triggers a dialog.select instead

		self.now = time.time()


		self.count = 0
		for show in stored_positions:
			if self.count == 1000:
				break

			self.pctplyd  = WINDOW.getProperty("%s.%s.PercentPlayed"           % ('LazyTV', show))
			if stored_lw[show] == 0:
				self.lw_time = 'never'
			else:
				self.gap = str(round((self.now - stored_lw[show]) / 86400.0, 1))
				if self.gap > 1:
					self.lw_time = self.gap + 'days'
				else:
					self.lw_time = self.gap + 'day'

			if self.pctplyd == '0%':
				self.pct = ''
			else:
				self.pct = self.pctplyd + ','
			self.label2 = '(' + self.pct + self.lw_time + ')'
			self.thumb = WINDOW.getProperty("%s.%s.Art(tvshow.poster)" % ('LazyTV', show))
			self.title = WINDOW.getProperty("%s.%s.TVshowTitle" % ('LazyTV', show))
			self.tmp = xbmcgui.ListItem(label=self.title, label2=self.label2, thumbnailImage = self.thumb)
			self.name_list.addItem(self.tmp)
			self.count += 1

		self.ok.controlRight(self.name_list)
		self.setFocus(self.name_list)
		log('window complete')

	def onAction(self, action):
		actionID = action.getId()
		if (actionID in (10, 92)):
			self.load_show_id = -1
			self.close()

	def onClick(self, controlID):
		if controlID == 5:
			self.load_show_id = -1
			self.close()
		else:
			self.pos = self.name_list.getSelectedPosition()
			self.playid = stored_episodes[self.pos]
			self.resume = WINDOW.getProperty("%s.%s.Resume" % ('LazyTV', self.pos))
			self.play_show(int(self.playid), self.resume)
			self.close()

	def play_show(self, epid, resume):
		xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "Player.Open", "params": { "item": { "episodeid": %d }, "options":{ "resume": "true" }  }, "id": 1 }' % (epid))


def process_stored(selected_pl):

	global stored_showids
	global stored_lw
	global stored_positions
	global stored_episodes

	stored_episodes = {}

	nepl_raw = WINDOW.getProperty("%s.nepl"	% ('LazyTV'))
	nepl = ast.literal_eval(nepl_raw)

	if selected_pl != 'null':
		stored_showids = [x[1] for x in nepl if x[1] in selected_pl]
		stored_lw = [x[0] for x in nepl if x[1] in selected_pl]
	else:
		stored_showids = [x[1] for x in nepl]
		stored_lw = [x[0] for x in nepl]

	stored_positions = [stored_showids.index(x) for x in stored_showids]
	stored_episodes = [WINDOW.getProperty("%s.%s.EpisodeID"  % ('LazyTV', x)) for x in stored_positions]


def create_next_episode_list(selected_pl):
	#creates a list of next episodes for all shows or a filtered subset and adds them to a playlist

	process_stored(selected_pl)

	log('window_opening')
	list_window = xGUI("DialogSelect.xml", scriptPath, 'Default')
	list_window.doModal()

	del list_window


if __name__ == "__main__":
	if populate_by == 'true':
		if select_pl == '0':
			selected_pl = playlist_selection_window()
		else:
			#get setting for default_playlist
			if not default_playlist:
				selected_pl = 'null'
			else:
				selected_pl = default_playlist
	else:
		selected_pl = 'null'
	if primary_function == '2':
		#assume this is selection
		choice = dialog.yesno('LazyTV', lang(32158),'',lang(32159), lang(32160),lang(32161))
		if choice == 1:
			random_playlist(selected_pl)
		elif choice == 0:
			create_next_episode_list(selected_pl)
		else:
			pass
	elif primary_function == '1':
		#assume this is random play
		random_playlist(selected_pl)
	else:
		#just build screen list
		create_next_episode_list(selected_pl)


#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
#@@@@@@@@@@
#@@@@@@@@@@ check for resume point in list selection
#@@@@@@@@@@
#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@

#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
#@@@@@@@@@@
#@@@@@@@@@@ add notification and next show prompt to service
#@@@@@@@@@@
#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@

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

plf            = {"jsonrpc": "2.0","id": 1, "method": "Files.GetDirectory", 		"params": {"directory": "special://profile/playlists/video/", "media": "video"}}
eps_query      = {"jsonrpc": "2.0","id": 1, "method": "VideoLibrary.GetEpisodes",	"params": {"properties": ["season","episode","runtime","resume","playcount","tvshowid","lastplayed","file"],"tvshowid": "placeholder" }}
seek           = {"jsonrpc": "2.0","id": 1, "method": "Player.Seek",				"params": {"playerid": 1, "value": 0 }}
clear_playlist = {"jsonrpc": "2.0","id": 1, "method": "Playlist.Clear",				"params": {"playlistid": 1}}
add_this_ep    = {'jsonrpc': '2.0','id': 1, "method": 'Playlist.Add', 				"params": {'item' : {'episodeid' : 'placeholder' }, 'playlistid' : 1}}
get_items      = {'jsonrpc': '2.0','id': 1, "method": 'Player.GetItem',				"params": {'playerid': 1, 'properties': ['tvshowid','resume']}}

#sys.stdout = open('C:\\Temp\\test.txt', 'w')
'''
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
	pass'''

__addon__         = xbmcaddon.Addon()
__addonid__       = __addon__.getAddonInfo('id')
__setting__       = __addon__.getSetting
lang              = __addon__.getLocalizedString
dialog            = xbmcgui.Dialog()
scriptPath        = __addon__.getAddonInfo('path')
__release__       = "Frodo" if xbmcaddon.Addon('xbmc.addon').getAddonInfo('version') == (12,0,0) else "Gotham"

WINDOW            = xbmcgui.Window(10000)

__resource__      =  os.path.join(scriptPath, 'resources', 'lib')
sys.path.append(__resource__)

start_time       = time.time()
base_time        = time.time()

primary_function = __setting__('primary_function')
populate_by      = __setting__('populate_by')
select_pl        = __setting__('select_pl')
default_playlist = __setting__('file')
length           = int(__setting__('length'))					#DONE
multipleshows    = __setting__('multipleshows')		#DONE
premieres        = __setting__('premieres')				#DONE
resume_partials  = __setting__('resume_partials')	#ONLY applies in random playlist, need to populate resume_dict
nextprompt       = __setting__('nextprompt')				#HANDLE IN SERVICE OR THROUGH PLAYER CLASS
promptduration   = __setting__('promptduration')		#HANDLE IN SERVICE OR THROUGH PLAYER CLASS
notify           = __setting__('notify')

def log(message, label=''):
	global start_time
	global base_time
	new_time   = time.time()
	gap_time   = "%5f" % (new_time - start_time)
	start_time = new_time
	total_gap  = "%5f" % (new_time - base_time)
	logmsg     = '%s : %s :: %s ::: %s     %s ' % (__addonid__+'addon', round(float(total_gap),5), round(float(gap_time),5), label,message)
	xbmc.log(msg = logmsg)


def gracefail(message):
	dialog.ok("LazyTV",message)
	sys.exit()


log('entered')


def playlist_selection_window():
	#Purpose: launch Select Window populated with smart playlists

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
		lw_date    = datetime.date(lw[0],lw[1],lw[2])
		day_string = str((todate - lw_date).days) + " days)"
		return day_string
	else:
		lw_max   = datetime.datetime(lw[0],lw[1],lw[2],lw[3],lw[4],lw[5])
		date_num = time.mktime(lw_max.timetuple())
		return date_num


def next_show_engine(showid, eps = [], Season = 'null', Episode = 'null'):

	if not eps:
		eps_query['params']['tvshowid'] = int(showid)
		ep = json_query(eps_query, True)				# query grabs the TV show episodes

		if 'episodes' not in ep: 						#ignore show if show has no episodes
			return 'null'
		else:
			eps = ep['episodes']

	#uses the season and episode number to create a list of unwatched shows newer than the last watched one
	unplayed_eps = [x for x in eps if ((x['season'] == int(Season) and x['episode'] > int(Episode)) or (x['season'] > int(Season)))]

	#sorts the list of unwatched shows by lowest season and lowest episode, filters the list to remove empty strings
	next_ep = sorted(unplayed_eps, key = lambda unplayed_eps: (unplayed_eps['season'], unplayed_eps['episode']))
	next_ep = filter(None, next_ep)

	if not next_ep:
		return 'null', ['null','null']
	elif 'episodeid' not in next_ep[0]:
		return 'null', ['null','null']
	else:
		return next_ep[0]['episodeid'], [next_ep[0]['season'],next_ep[0]['episode']]


class MyPlayer(xbmc.Player):
	def __init__(self, *args, **kwargs):
		log('player STARTED')
		xbmc.Player.__init__(self)
		#disable next_show_prompt in service (can be done in the service when "LazyTV.playlist_running" is 'true')
		self.player_active = True
		self.send_notification()

	def onPlayBackEnded(self):
		log('player ENDED')
		xbmc.sleep(250)		#give the chance for the playlist to start the next item
		self.now_name = xbmc.getInfoLabel('VideoPlayer.TVShowTitle')
		if self.now_name == '':
			xbmc.executebuiltin('ActivateWindow(10028)')
			self.player_active = False
			WINDOW.setProperty("%s.playlist_running"	% ('LazyTV'), 'false')
		self.player_active = False

	def onPlayBackStopped(self):
		self.onPlayBackEnded()

	def onPlayBackStarted(self):
		self.send_notification()

	def send_notification(self):
		xbmc.sleep(50) #give the chance for the playlist to start the next item

		self.now_name    = xbmc.getInfoLabel('VideoPlayer.TVShowTitle')
		self.now_season  = xbmc.getInfoLabel('VideoPlayer.Season')
		self.now_episode = xbmc.getInfoLabel('VideoPlayer.Episode')

		if self.now_name == '':
			self.player_active = False
		else:
			#this ensures that a resumable episode gets resumed no matter where it is in the playlist
			if resume_partials == 'true':
				#try:
				self.tmp_res = json_query(get_items, True)['item']['resume']
				if self.tmp_res['position'] > 0:
					seek_point = int((float(self.tmp_res['position']) / float(self.tmp_res['total'])) *100)
					seek['params']['value'] = seek_point
					json_query(seek, False)
				#except:
				#	pass

			if notify == 'true':
				if len(self.now_season) == 1:
					self.now_season = '0' + self.now_season
				if len(self.now_episode) == 1:
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
			position = stored_positions.index(show)
			if self.count == 1000:
				break

			self.pctplyd  = WINDOW.getProperty("%s.%s.PercentPlayed"           % ('LazyTV', show))
			if stored_lw[position] == 0:
				self.lw_time = 'never'
			else:
				self.gap = str(round((self.now - stored_lw[position]) / 86400.0, 1))
				if self.gap > 1:
					self.lw_time = self.gap + 'days'
				else:
					self.lw_time = self.gap + 'day'

			if self.pctplyd == '0%':
				self.pct = ''
			else:
				self.pct = self.pctplyd + ', '
			self.label2 = '(' + self.pct + self.lw_time + ')'
			self.thumb  = WINDOW.getProperty("%s.%s.Art(tvshow.poster)" % ('LazyTV', show))
			self.title  = WINDOW.getProperty("%s.%s.TVshowTitle" % ('LazyTV', show))
			self.tmp    = xbmcgui.ListItem(label=self.title, label2=self.label2, thumbnailImage = self.thumb)
			self.name_list.addItem(self.tmp)
			self.count += 1

		self.ok.controlRight(self.name_list)
		self.setFocus(self.name_list)

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
			self.pos    = self.name_list.getSelectedPosition()
			self.playid = stored_episodes[self.pos]
			self.resume = WINDOW.getProperty("%s.%s.Resume" % ('LazyTV', self.pos))
			self.play_show(int(self.playid), self.resume)
			self.close()

	def play_show(self, epid, resume):
		xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "Player.Open", "params": { "item": { "episodeid": %d }, "options":{ "resume": "true" }  }, "id": 1 }' % (epid))


def process_stored(sel_pl):

	global stored_showids
	global stored_lw
	global stored_positions
	global stored_episodes

	nepl_raw = WINDOW.getProperty("%s.nepl"	% ('LazyTV'))
	nepl     = ast.literal_eval(nepl_raw)

	if sel_pl == 'null':
		new_show_list = []
		for x in range(len(nepl)):
			new_show_list.append(nepl[x][1])
		selected_pl = new_show_list
	else:
		selected_pl = convert_pl_to_showlist(sel_pl)

	stored_episodes     = []
	stored_showids_orig = [x[1] for x in nepl]

	if selected_pl != 'null':
		stored_showids  = [x[1] for x in nepl if x[1] in selected_pl]
		stored_lw       = [x[0] for x in nepl if x[1] in selected_pl]
	else:
		stored_showids  = [x[1] for x in nepl]
		stored_lw       = [x[0] for x in nepl]

	stored_positions = [stored_showids_orig.index(x) for x in stored_showids]
	stored_episodes  = [WINDOW.getProperty("%s.%s.EpisodeID"  % ('LazyTV', x)) for x in stored_positions]


def convert_pl_to_showlist(selected_pl):
	# derive filtered_showids from smart playlist
	filename = os.path.split(selected_pl)[1]
	clean_path = 'special://profile/playlists/video/' + filename

	#retrieve the shows in the supplied playlist, save their ids to a list
	plf['params']['directory'] = clean_path
	playlist_contents = json_query(plf, True)

	if 'files' not in playlist_contents:
		log('files not in playlist contents')
	else:
		if not playlist_contents['files']:
			log('playlist contents empty')
		else:
			for x in playlist_contents['files']:
				filtered_showids = [x['id'] for x in playlist_contents['files'] if x['type'] == 'tvshow']
				log(filtered_showids, 'showids in playlist')
				if not filtered_showids:
					log('no filtered shows')

	#returns the list of all and filtered shows and episodes
	return filtered_showids


def random_playlist(selected_pl):
	#get the showids and such from the playlist
	process_stored(selected_pl)

	#clear the existing playlist
	json_query(clear_playlist, False)

	added_ep_dict   = {}
	abandoned_shows = []
	count           = 0

	while count < length and len(abandoned_shows) != len(stored_episodes): 		#while the list isnt filled, and all shows arent abandoned
		multi = False
		R = random.randint(0,len(stored_episodes) - 1)	#get random number

		if stored_showids[R] in added_ep_dict.keys():
			if multipleshows == 'true':		#check added_ep list if multiples allowed
				multi = True
				tmp_episode_id, tmp_details = next_show_engine(showid=stored_showids[R],Season=added_ep_dict[stored_showids[R]][0],Episode=added_ep_dict[stored_showids[R]][1])
				if tmp_episode_id == 'null':
					abandoned_shows.append(stored_showids[R])
					continue
			else:
				abandoned_shows.append(stored_showids[R])
				continue
		else:
			tmp_episode_id = stored_episodes[R]
		if premieres == 'false':
			if WINDOW.getProperty("%s.%s.EpisodeNo" % ('LazyTV', R)) == 's01e01':	#if desired, ignore s01e01
				abandoned_shows.append(stored_showids[R])
				continue

		#add episode to playlist
		add_this_ep['params']['item']['episodeid'] = int(tmp_episode_id)
		json_query(add_this_ep, False)

		#add episode to added episode dictionary
		if multi == False:
			added_ep_dict[stored_showids[R]] = [WINDOW.getProperty("%s.%s.Season" % ('LazyTV', R)), WINDOW.getProperty("%s.%s.Episode" % ('LazyTV', R))]
		else:
			added_ep_dict[stored_showids[R]] = [tmp_details[0],tmp_details[1]]

		count += 1

	WINDOW.setProperty("%s.playlist_running"	% ('LazyTV'), 'true')
	xbmc.Player().play(xbmc.PlayList(1))
	LazyTV_def = MyPlayer()

	while not xbmc.abortRequested and LazyTV_def.player_active == True:
		xbmc.sleep(100)
	log('LIST complete')


def create_next_episode_list(selected_pl):
	#creates a list of next episodes for all shows or a filtered subset and adds them to a playlist

	process_stored(selected_pl)
	list_window = xGUI("DialogSelect.xml", scriptPath, 'Default')
	list_window.doModal()
	del list_window


if __name__ == "__main__":

	try:
		params = dict( arg.split( "=" ) for arg in sys.argv[ 1 ].split( "&" ) )
	except:
		params = {}
	episodeid = params.get( "episodeid", "" )

	if episodeid:
		xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "Player.Open", "params": { "item": { "episodeid": %d }, "options":{ "resume": "true" }  }, "id": 1 }' % int(episodeid))

	else:
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
	#@@@@@@@@@@ add notification and next show prompt to service
	#@@@@@@@@@@
	#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@

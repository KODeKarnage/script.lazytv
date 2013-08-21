# declare file encoding
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

import random, xbmcgui, xbmcaddon
import os
from resources.lazy_lib import *
#import sys
#sys.stdout = open('C:\\Temp\\test.txt', 'w')

_addon_ = xbmcaddon.Addon("script.lazytv")
_setting_ = _addon_.getSetting
lang = _addon_.getLocalizedString
dialog = xbmcgui.Dialog()

premieres = _setting_('premieres')
partial = _setting_('partial')
playlist_length = _setting_('length')
multiples = _setting_('multipleshows')
ignore_list = _setting_('IGNORE')
streams = _setting_('streams')
expartials = _setting_('expartials')
filter_show = _setting_('filter_show')
filter_genre = _setting_('filter_genre')
filter_length = _setting_('filter_length')
filter_rating = _setting_('filter_rating')
first_run = _setting_('first_run')
primary_function = _setting_('primary_function')
populate_by = _setting_('populate_by')
smart_pl = _setting_('default_spl')

IGNORE_SHOWS = proc_ig(ignore_list,'name') if filter_show == 'true' else []
IGNORE_GENRE = proc_ig(ignore_list,'genre') if filter_genre == 'true' else []
IGNORE_LENGTH = proc_ig(ignore_list,'length') if filter_length == 'true' else []
IGNORE_RATING = proc_ig(ignore_list,'rating') if filter_rating == 'true' else []

IGNORES = [IGNORE_SHOWS,IGNORE_GENRE,IGNORE_LENGTH,IGNORE_RATING]


def criteria_filter():

	grab_all_shows = {"jsonrpc": "2.0", 
	"method": "VideoLibrary.GetTVShows", 
	"params": 
		{"filter": {"field": "playcount", "operator": "is", "value": "0"},
		"properties": ["genre", "title", "playcount", "mpaa", "watchedepisodes", "episode"]}, 
	"id": "allTVShows"}

	all_shows = json_query(grab_all_shows)['result']['tvshows']

	filtered_showids = [show['tvshowid'] for show in all_shows 
	if show['title'] not in IGNORES[0] 
	and bool(set(show['genre']) & set(IGNORES[1])) == False
	and show['mpaa'] not in IGNORES[3]
	and (show['watchedepisodes'] > 0 or premieres == 'true')
	and show['episode']>0]

	grab_all_episodes = {"jsonrpc": "2.0", 
	"method": "VideoLibrary.GetEpisodes", 
	"params": 
		{"properties": ["season","episode","runtime", "resume","playcount", "tvshowid", "lastplayed", "file"]}, 
	"id": "allTVEpisodes"}

	eps = json_query(grab_all_episodes)['result']['episodes']


	#Applies Length exclusion
	filtered_eps = [x for x in eps if x['tvshowid'] in filtered_showids and x['runtime'] not in IGNORES[2]]
	filtered_eps_showids = [show['tvshowid'] for show in filtered_eps]
	filtered_showids = [x for x in filtered_showids if x in filtered_eps_showids]

	return filtered_eps, filtered_showids, all_shows, eps

def smart_playlist_filter(playlist):
	"""Purpose: derive filtered_eps, filtered_showids from smart playlist"""
	plf = {"jsonrpc": "2.0", "method": "Files.GetDirectory", "params": {"directory": "placeholder", "media": "video"}, "id": 1}
	plf['params']['directory'] = playlist
	playlist_contents = json_query(plf)['result']['files']
	filtered_showids = [x['id'] for x in playlist_contents]

	grab_all_episodes = {"jsonrpc": "2.0", 
	"method": "VideoLibrary.GetEpisodes", 
	"params": 
		{"properties": ["season","episode","runtime", "resume","playcount", "tvshowid", "lastplayed", "file"]}, 
	"id": "allTVEpisodes"}

	eps = json_query(grab_all_episodes)['result']['episodes']

	filtered_eps = [x for x in eps if x['tvshowid'] in filtered_showids]

	grab_all_shows = {"jsonrpc": "2.0", 
	"method": "VideoLibrary.GetTVShows", 
	"params": 
		{"filter": {"field": "playcount", "operator": "is", "value": "0"},
		"properties": ["genre", "title", "playcount", "mpaa", "watchedepisodes", "episode"]}, 
	"id": "allTVShows"}

	all_shows = json_query(grab_all_shows)['result']['tvshows']

	return filtered_eps, filtered_showids, all_shows, eps


def populate_by_x():
	#determines what populates the playlist or selection
	if populate_by == '1':
		filtered_eps, filtered_showids, all_shows, eps = smart_playlist_filter(smart_pl)
	elif populate_by == '2':
		selected_pl = playlist_selection_window()
		filtered_eps, filtered_showids, all_shows, eps = smart_playlist_filter(selected_pl)
	else:
		filtered_eps, filtered_showids, all_shows, eps = criteria_filter()

	return filtered_eps, filtered_showids, all_shows, eps


def create_playlist():
	partial_exists = False
	itera = 0
	playlist_tally = {}

	json_query({'jsonrpc': '2.0','method': 'Playlist.Clear','params': {'playlistid':1},'id': '1'}) 

	filtered_eps, filtered_showids, all_shows, eps = populate_by_x()

	#Applies start with partial setting
	if partial == 'true':
		partial_eps = [x for x in filtered_eps if x['resume']['position']>0]
		if len(partial_eps) >0:
			most_recent_partial = sorted(partial_eps, key = lambda partial_eps: (partial_eps['lastplayed']), reverse=True)[0]
			playlist_tally[most_recent_partial['tvshowid']] = (most_recent_partial['season'],most_recent_partial['episode'])
			
			if multiples == 'false':
				filtered_showids = [x for x in filtered_showids if x != most_recent_partial['tvshowid']]
			
			json_query(dict_engine(most_recent_partial['file']))
			player_start()
			partial_exists = True

			#jumps to seek point
			seek_percent = float(most_recent_partial['resume']['position'])/float(most_recent_partial['resume']['total'])*100.0
			seek = {'jsonrpc': '2.0','method': 'Player.Seek','params': {'playerid':1,'value':0.0}, 'id':1}
			seek['params']['value'] = seek_percent
			json_query(seek)

	#Applies exclude partials setting
	if expartials == 'true':
		partially_watched = [x['tvshowid'] for x in filtered_eps if x['resume']['position']>0]
		filtered_eps = [x for x in filtered_eps if x['tvshowid'] not in partially_watched]
		filtered_eps_showids = [show['tvshowid'] for show in filtered_eps]
		filtered_showids = [x for x in filtered_showids if x in filtered_eps_showids]
	
	show_count = len(filtered_showids)
	if show_count == 0 and partial == 'false':
		dialog.ok('LazyTV', lang(30047))
	while itera in range((int(playlist_length)-1) if partial_exists == True else int(playlist_length)):
		show_count = len(filtered_showids)
		if show_count == 0:
			itera = 1000
		else:
			R = random.randint(0,show_count - 1)
			SHOWID = filtered_showids[R]
			this_show = [x for x in all_shows if x['tvshowid'] == SHOWID][0]
			if SHOWID in playlist_tally.keys():
				Season = playlist_tally[SHOWID][0]
				Episode = playlist_tally[SHOWID][1]
			elif this_show['watchedepisodes'] == 0 and premieres == 'true':
				Season = 0
				Episode = 0
			else:
				played_eps = [x for x in eps if x['playcount'] is not 0 and x['tvshowid'] == SHOWID]
				last_played_ep = sorted(played_eps, key =  lambda played_eps: (played_eps['season'], played_eps['episode']), reverse=True)[0]
				Season = last_played_ep['season']
				Episode = last_played_ep['episode']

			unplayed_eps = [x for x in eps if ((x['season'] == Season and x['episode'] > Episode)
			or (x['season'] > Season)) and x['tvshowid'] == SHOWID]

			next_ep = sorted(unplayed_eps, key = lambda unplayed_eps: (unplayed_eps['season'], unplayed_eps['episode']))
			if len(next_ep) == 0:    
				filtered_showids = [x for x in filtered_showids if x != SHOWID]
			
			elif ".strm" not in str(next_ep[0]['file'].lower()) or (".strm" in str(next_ep[0]['file'].lower()) and streams == 'true' and itera != 0):

				json_query(dict_engine(next_ep[0]['file']))
				if multiples == 'false':
					filtered_showids = [x for x in filtered_showids if x != SHOWID]
				else:
					playlist_tally[SHOWID] = (next_ep[0]['season'],next_ep[0]['episode'])

				if itera == 0 and partial_exists == False:	
					player_start()

				itera +=1

def create_next_episode_list():
	pass
	"""populate window with ShowName - [state: Premiere as [p] | Partial [r]] - SyEz - EpName

	selection window does not remove partials 

	sort entries by title or last watched

	[OPT] selecting show creates playlist populated with the next X episodes
	"""

if __name__ == "__main__":
	if first_run == 'true':
		_addon_.setSetting(id="first_run",value="false")
		xbmcaddon.Addon().openSettings()
	elif primary_function == '0':
		create_playlist()
	elif primary_function == '1':
		create_next_episode_list()

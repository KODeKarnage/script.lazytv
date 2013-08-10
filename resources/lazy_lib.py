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

import sqlite3, json, xbmc, xbmcaddon, os, re
from resources.queries import *

_addon_ = xbmcaddon.Addon("plugin.video.lazytv")
_setting_ = _addon_.getSetting
lang = _addon_.getLocalizedString

def proc_ig(ignore_list, ignore_by):
	il = ignore_list.split("|")
	return [i.replace(ignore_by+":-:","") for i in il if ignore_by+":-:" in i]

def find_database():
	folder = str(os.listdir(xbmc.translatePath('special://database/')))
	dbn = re.findall('MyVideos(\d+).db', folder)
	dbn.sort()
	max_num = dbn[len(dbn)-1]
	return os.path.join(xbmc.translatePath("special://database"),'MyVideos' + str(max_num) + '.db')

def filter(IGNORES, tally, show):
	if (len(show) != 0
	and show[0] not in IGNORES[0]
	and bool(set(str(show[4]).split(" / ")) & set(IGNORES[1])) == False
	and show[5] not in IGNORES[2]
	and show[7] not in IGNORES[3]
	and show[6] not in tally
	and (False if show[7]=='' and lang(30111) in IGNORES[3] else True)):
		return True
	else:
		return False

def sql_query(database, query):
	connection = sqlite3.connect(database)
	cursor = connection.cursor()
	cursor.execute(query)
	return cursor.fetchall()

def json_query(query):
	xbmc_request = json.dumps(query)
	result = xbmc.executeJSONRPC(xbmc_request)
	return json.loads(result)

def player_start():
	#the play list is now complete, this next part starts playing
	play_command = {'jsonrpc': '2.0','method': 'Player.Open','params': {'item': {'playlistid':1}},'id': 1}
	json_query(play_command)  

def replace_show(database, popped):
	# replaces the recently added episode with another from the same series, if elected
	#discovers the last episode of the current season for the popped show
	last_ep = sql_query(database, last_episode_this_season % (int(popped[1]), int(popped[3])))
	replacement_show = []
	if last_ep[0][0] == popped[2]:
		replacement_show += (sql_query(database, next_episode_next_season % (int(popped[1]),int(popped[3]),int(popped[1]),int(popped[1]))))
	else:
		replacement_show += (sql_query(database, next_episode_this_season % (popped[1],int(popped[3]),int(popped[2]),int(popped[1]),int(popped[3]))))
	return replacement_show


def dict_engine(popped6):
	d = {}
	e = {}
	f = {}
	d['jsonrpc'] = '2.0'
	d['method'] = 'Playlist.Add'
	d['id'] = '1'	
	d['params'] = {}
	d['params']['item'] = {}
	d['params']['item']['file'] = popped6
	d['params']['playlistid'] = 1
	return d
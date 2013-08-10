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
from resources.queries import *
from resources.lazy_lib import *
#import sys
#sys.stdout = open('C:\\Temp\\test.txt', 'w')

_addon_ = xbmcaddon.Addon("plugin.video.lazytv")
_setting_ = _addon_.getSetting
lang = _addon_.getLocalizedString
dialog = xbmcgui.Dialog()

premieres = _setting_('premieres')
partial = _setting_('partial')
playlist_length = _setting_('length')
multiples = _setting_('multipleshows')
ignore_list = _setting_('IGNORE')
expartials = _setting_('expartials')
first_run = _setting_('first_run')
filter_show = _setting_('filter_show')
filter_genre = _setting_('filter_genre')
filter_length = _setting_('filter_length')
filter_rating = _setting_('filter_rating')
first_run = _setting_('first_run')

database = find_database()


IGNORE_SHOWS = proc_ig(ignore_list,'name') if filter_show == 'true' else []
IGNORE_GENRE = proc_ig(ignore_list,'genre') if filter_genre == 'true' else []
IGNORE_LENGTH = proc_ig(ignore_list,'length') if filter_length == 'true' else []
IGNORE_RATING = proc_ig(ignore_list,'rating') if filter_rating == 'true' else []

IGNORES = [IGNORE_SHOWS,IGNORE_GENRE,IGNORE_LENGTH,IGNORE_RATING]

def create_start_playlist():
	showlist, clean_showlist, add_part, bookmarked, tally = [[],[],[],[],[]]
	partial_exists = False
	seek_percent = 0.0
	itera = 0
	sump = 0
	global partial, multiples, premieres, playlist_length

	showlist = sql_query(database, grab_active_series) 															#begins by grabbing the next show from active series
	if showlist == [] and premieres == 'false':
		answ = dialog.yesno('LazyTV', lang(30045), lang(30046))
		if answ ==1:
			premieres = 'true'
	
	showlist = showlist + sql_query(database, grab_inactive_series) if premieres == 'true' else showlist 		#adds the shows from unwatched series, if elected
	bookmarked = sql_query(database, bookmarks) if expartials == 'true' else []   								#gets the list of partials to exclude
	clean_showlist = [x for x in showlist if filter(IGNORES, tally, x) == True and x[6] not in bookmarked]    	#runs the showlist through a filter to remove the shows on the ignore lists and clears out the partially watched
	json_query({'jsonrpc': '2.0','method': 'Playlist.Clear','params': {'playlistid':1},'id': '1'})  			#clears the existing play list

	# adds the latest partial show to the play list, if elected  
	add_part = sql_query(database, latest_partial)
	part_count = len(add_part)
	while partial == 'true' and part_count != 0:
		for part in range(part_count):
			if filter(IGNORES, tally, add_part[part]):
				#adds to playlist
				p = dict_engine(add_part[part][6])
				json_query(p) 
				tally.append(add_part[part][6])
				
				#starts playing
				player_start()
				partial_exists = True
				
				#jumps to seek point
				seek_percent = float(add_part[part][8])/float(add_part[part][9])*100.0
				seek = {'jsonrpc': '2.0','method': 'Player.Seek','params': {'playerid':1,'value':0.0}, 'id':1}
				seek['params']['value'] = seek_percent
				json_query(seek)
				
				#replace PARTIAL with next episode
				if multiples == 'true':
					b = replace_show(database, add_part[part])
					if b != []:
						clean_showlist.append(b[0])
				break
		break
				
	show_count = len(clean_showlist)
	if show_count == 0 and partial == 'false':
		dialog.ok('LazyTV', lang(30047))
	#loops through the clean showlist and randomly adds shows to the playlist 
	while itera in range((int(playlist_length)-1) if partial_exists == True else int(playlist_length)):
		show_count = len(clean_showlist)
		if show_count == 0:
			itera = 1000
		else:
			R = random.randint(0,show_count - 1)
			popped = clean_showlist.pop(R)
			if len(popped) != 0 and popped[6] not in tally:
				json_query(dict_engine(popped[6]))
				if itera == 0 and partial_exists == False:	
					player_start()
				if multiples == 'true':
					a = replace_show(database, popped)
					if a != []:
						if a[0][6] == popped[6]:							#to accommodate double episodes
							b = replace_show(database, a[0])
							if b != []:
								clean_showlist.append(b[0])
						else:
							clean_showlist.append(a[0])
				tally.append(popped[6])
				itera +=1
	


if __name__ == "__main__":
	if first_run == 'true':
		_addon_.setSetting(id="first_run",value="false")
		xbmcaddon.Addon().openSettings()
	else:
		create_start_playlist()

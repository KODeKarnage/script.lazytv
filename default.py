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
#

# XBMC modules
import xbmcgui
import xbmc
import xbmcaddon

# STANDARD library modules
import random
import socket
import time
import datetime
import os
import ast
import json
import sys
sys.path.append(xbmc.translatePath(os.path.join(xbmcaddon.Addon().getAddonInfo('path'), 'resources','lib')))

# LAZYTV modules
import lazy_classes as C
import lazy_queries as Q
import lazy_tools   as T

__addon__        = xbmcaddon.Addon()
__addonid__      = __addon__.getAddonInfo('id')
__addonversion__ = tuple([int(x) for x in __addon__.getAddonInfo('version').split('.')])
__scriptPath__       = __addon__.getAddonInfo('path')
__setting__      = __addon__.getSetting
scriptName       = __addon__.getAddonInfo('Name')
language         = xbmc.getInfoLabel('System.Language')

# GUI constructs
WINDOW           = xbmcgui.Window(10000)
DIALOG           = xbmcgui.Dialog()

# creates the logger & translator
keep_logs = True if __setting__('logging') == 'true' else False
logger    = C.lazy_logger(__addon__, __addonid__ + ' default', keep_logs)
log       = logger.post_log
lang      = logger.lang
# log('Running: ' + str(__release__))

# localises tools
json_query = T.json_query
stringlist_to_reallist = T.stringlist_to_reallist
runtime_converter = T.runtime_converter
fix_SE = T.fix_SE




if __setting__('skinorno') == 'true':
	skin = 1
	__addon__.setSetting('skinorno','1')
elif __setting__('skinorno') == 'false' or __setting__('skinorno') == '32073':
	skin = 0
	__addon__.setSetting('skinorno','1')
else:
	skin = int(float(__setting__('skinorno')))


# This is a throwaway variable to deal with a python bug
try:
	throwaway = datetime.datetime.strptime('20110101','%Y%m%d')
except:
	pass


log('language = ' + str(language))





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


def next_show_engine(showid, epid=[],eps = [], Season = 'null', Episode = 'null'):
	log('nextep_engine_start', showid)

	if showid in randos:
		newod = eps.remove(epid)
		if not eps:
			return 'null', ['null','null', 'null','null']
		random.shuffle(newod)
		next_ep = newod[0]

	else:
		if not eps:
			return 'null', ['null','null', 'null','null']
		try:
			next_ep = eps[1]
		except:
			return 'null', ['null','null', 'null','null']
			
		newod = eps[1:]

	#get details of next_ep
	ep_details_query = {"jsonrpc": "2.0","method": "VideoLibrary.GetEpisodeDetails","params": {"properties": ["season","episode"],"episodeid": next_ep},"id": "1"}
	epd = T.json_query(Q.ep_details_query, True)

	if 'episodedetails' in epd and epd['episodedetails']:
		return next_ep, [epd['episodedetails']['season'],epd['episodedetails']['episode'],newod,next_ep]

	else:
		return 'null', ['null','null', 'null','null']

	log('nextep_engine_End', showid)


def get_TVshows():
	log('get_TVshows_started', reset = True)
	log('sort by = ' + str(sort_by))

	#get the most recent info on inProgress TV shows, cross-check it with what is currently stored
	query          = '{"jsonrpc": "2.0","method": "VideoLibrary.GetTVShows","params": {"filter": {"field": "playcount", "operator": "is", "value": "0" },"properties": ["lastplayed"], "sort": {"order": "descending", "method": "lastplayed"} },"id": "1" }'

	nepl_retrieved = xbmc.executeJSONRPC(query)
	nepl_retrieved = unicode(nepl_retrieved, 'utf-8', errors='ignore')
	nepl_retrieved = json.loads(nepl_retrieved)

	log('get_TVshows_querycomplete')

	if 'result' in nepl_retrieved and 'tvshows' in nepl_retrieved["result"] and nepl_retrieved['result']['tvshows']:
		nepl_retrieved = nepl_retrieved['result']['tvshows']
		for x in nepl_retrieved:
			log(str(x))
	else:
		log('no unwatched TV shows in library')
		log(nepl_retrieved)
		nepl_retrieved = {}

	nepl_from_service = WINDOW.getProperty("LazyTV.nepl")

	if nepl_from_service:
		p = ast.literal_eval(nepl_from_service)
		nepl_stored = [int(x) for x in p]
	else:
		dialog.ok('LazyTV',lang(32115),lang(32116))
		sys.exit()

	nepl = sort_shows(nepl_retrieved, nepl_stored)

	stored_data = [[x[0],x[1],WINDOW.getProperty("%s.%s.EpisodeID"  % ('LazyTV', x[1]))] for x in nepl]

	log('get_TVshows_End')

	return stored_data


def sort_shows(nepl_retrieved, nepl_stored):

	if sort_by == 0:
		# SORT BY show name
		log('sort by name')
		nepl_inter  = [[x['label'], T.day_conv(x['lastplayed']) if x['lastplayed'] else 0, x['tvshowid']] for x in nepl_retrieved if x['tvshowid'] in nepl_stored]
		nepl_inter.sort(key= lambda x: T.order_name(x[0]), reverse = sort_reverse )
		nepl        = [x[1:] for x in nepl_inter]

	elif sort_by == 2:
		# sort by Unwatched Episodes
		log('sort by unwatched count')
		nepl_inter  = [[ int(WINDOW.getProperty("%s.%s.CountonDeckEps" % ('LazyTV', x['tvshowid'])))
								, T.day_conv(x['lastplayed']) if x['lastplayed'] else 0
								, x['tvshowid']]
							for x in nepl_retrieved if x['tvshowid'] in nepl_stored]

		nepl_inter.sort(reverse = sort_reverse == False)
		nepl        = [x[1:] for x in nepl_inter]

	elif sort_by == 3:
		# sort by Watched Episodes
		log('sort by watched count')
		nepl_inter  = [[ int(WINDOW.getProperty("%s.%s.CountWatchedEps" % ('LazyTV', x['tvshowid'])))
							, T.day_conv(x['lastplayed']) if x['lastplayed'] else 0
							, x['tvshowid']]
						for x in nepl_retrieved if x['tvshowid'] in nepl_stored]

		nepl_inter.sort(reverse = sort_reverse == False)

		nepl        = [x[1:] for x in nepl_inter]


	elif sort_by == 4:
		# sort by Season
		log('sort by season')
		nepl_inter  = [[int(WINDOW.getProperty("%s.%s.Season" % ('LazyTV', x['tvshowid'])))
						, T.day_conv(x['lastplayed']) if x['lastplayed'] else 0
						, x['tvshowid']]
					for x in nepl_retrieved if x['tvshowid'] in nepl_stored]
		
		nepl_inter.sort(reverse = sort_reverse == False)

		nepl        = [x[1:] for x in nepl_inter]

	else:
		# SORT BY LAST WATCHED
		log('sort by last watched')
		nepl_inter        = [[T.day_conv(x['lastplayed']) if x['lastplayed'] else 0, x['tvshowid']] for x in nepl_retrieved if x['tvshowid'] in nepl_stored]

		# this sorting section needs to ignore everything that has never been played
		nepl_nev = [x for x in nepl_inter if x[0] == 0]
		nepl_w = [x for x in nepl_inter if x[0] != 0]

		nepl_w.sort(reverse = sort_reverse == False)

		nepl = nepl_w + nepl_nev


	return nepl


def process_stored(population):

	stored_data = get_TVshows()

	log('process_stored', reset = True)

	if 'playlist' in population:
		extracted_showlist = convert_pl_to_showlist(population['playlist'])
	elif 'usersel' in population:
		extracted_showlist = population['usersel']
	else:
		extracted_showlist = False

	if extracted_showlist:
		stored_data_filtered  = [x for x in stored_data if x[1] in extracted_showlist]
	else:
		stored_data_filtered = stored_data

	log('process_stored_End')

	return stored_data_filtered


def convert_pl_to_showlist(pop):
	# derive filtered_showids from smart playlist
	filename = os.path.split(pop)[1]
	clean_path = 'special://profile/playlists/video/' + filename

	#retrieve the shows in the supplied playlist, save their ids to a list
	plf['params']['directory'] = clean_path
	playlist_contents = T.json_query(Q.plf, True)

	if 'files' not in playlist_contents:
		gracefail('files not in playlist contents')
	else:
		if not playlist_contents['files']:
			gracefail('playlist contents empty')
		else:
			for x in playlist_contents['files']:
				filtered_showids = [x['id'] for x in playlist_contents['files'] if x['type'] == 'tvshow']
				log(filtered_showids, 'showids in playlist')
				if not filtered_showids:
					gracefail('no tv shows in playlist')

	#returns the list of all and filtered shows and episodes
	return filtered_showids


def random_playlist(population):
	global movies
	global movieweight

	#get the showids and such from the playlist
	stored_data_filtered = process_stored(population)

	log('random_playlist_started',reset = True)

	#clear the existing playlist
	T.json_query(Q.clear_playlist, False)

	added_ep_dict   = {}
	count           = 0
	movie_list      = []


	if movies or moviesw:

		if movies and moviesw:
			mov = T.json_query(Q.get_moviesa, True)
		elif movies:
			mov = T.json_query(Q.get_movies, True)
		elif moviesw:
			mov = T.json_query(Q.get_moviesw, True)

		movies = True

		if 'movies' in mov and mov['movies']:
			movie_list = [x['movieid'] for x in mov['movies']]
			log('all movies = ' + str(movie_list))
			if not movie_list:
				movies = False
			else:
				random.shuffle(movie_list)
		else:
			movies = False

	storecount = len(stored_data_filtered)
	moviecount = len(movie_list)

	if noshow:
		movieweight = 0.0
		stored_data_filtered = []

	if movieweight != 0.0:
		movieint = min(max(int(round(storecount * movieweight,0)), 1), moviecount)
	else:
		movieint = moviecount

	if movies:
		movie_list = movie_list[:movieint]
		log('truncated movie list = ' + str(movie_list))

	candidate_list = ['t' + str(x[1]) for x in stored_data_filtered] + ['m' + str(x) for x in movie_list]
	random.shuffle(candidate_list)

	watch_partial_now = False

	if start_partials:

		if candidate_list:
			red_candy = [int(x[1:]) for x in candidate_list if x[0] == 't']
		else:
			red_candy = []

		lst = []

		for showid in red_candy:

			if WINDOW.getProperty("%s.%s.Resume" % ('LazyTV',showid)) == 'true':
				temp_ep = WINDOW.getProperty("%s.%s.EpisodeID" % ('LazyTV',showid))
				if temp_ep:
					lst.append({"jsonrpc": "2.0","method": "VideoLibrary.GetEpisodeDetails","params": {"properties": ["lastplayed","tvshowid"],"episodeid": int(temp_ep)},"id": "1"})

		lwlist = []

		if lst:

			xbmc_request = json.dumps(lst)
			result = xbmc.executeJSONRPC(xbmc_request)

			if result:
				reslist = ast.literal_eval(result)
				for res in reslist:
					if 'result' in res:
						if 'episodedetails' in res['result']:
							lwlist.append((res['result']['episodedetails']['lastplayed'],res['result']['episodedetails']['tvshowid']))

			lwlist.sort(reverse=True)

		if lwlist:

			log(lwlist, label="lwlist = ")

			R = candidate_list.index('t' + str(lwlist[0][1]))

			watch_partial_now = True

			log(R,label="R = ")




	while count < length and candidate_list: 		#while the list isnt filled, and all shows arent abandoned or movies added
		log('candidate list = ' + str(candidate_list))
		multi = False

		if start_partials and watch_partial_now:
			watch_partial_now = False
		else:
			R = random.randint(0, len(candidate_list) -1 )	#get random number

		log('R = ' + str(R))

		curr_candi = candidate_list[R][1:]
		candi_type = candidate_list[R][:1]

		if candi_type == 't':
			log('tvadd attempt')

			if curr_candi in added_ep_dict.keys():
				log(str(curr_candi) + ' in added_shows')
				if multipleshows:		#check added_ep list if multiples allowed
					multi = True
					tmp_episode_id, tmp_details = next_show_engine(showid=curr_candi,epid=added_ep_dict[curr_candi][3],eps=added_ep_dict[curr_candi][2],Season=added_ep_dict[curr_candi][0],Episode=added_ep_dict[curr_candi][1])
					if tmp_episode_id == 'null':
						tg = 't' + str(curr_candi)
						if tg in candidate_list:
							candidate_list.remove('t' + str(curr_candi))
							log(str(curr_candi) + ' added to abandonded shows (no next show)')
						continue
				else:
					continue
			else:
				log(str(curr_candi) + ' not in added_showss')
				tmp_episode_id = int(WINDOW.getProperty("%s.%s.EpisodeID" % ('LazyTV',curr_candi)))
				if not multipleshows:		#check added_ep list if multiples allowed, if not then abandon the show
					tg = 't' + str(curr_candi)
					if tg in candidate_list:
						candidate_list.remove('t' + str(curr_candi))
					log(str(curr_candi) + ' added to abandonded shows (no multi)')


			if not premieres:
				if WINDOW.getProperty("%s.%s.EpisodeNo" % ('LazyTV',curr_candi)) == 's01e01':	#if desired, ignore s01e01
					tg = 't' + str(curr_candi)
					if tg in candidate_list:
						candidate_list.remove('t' + str(curr_candi))
					log(str(curr_candi) + ' added to abandonded shows (premieres)')
					continue

			#add episode to playlist
			if tmp_episode_id:
				add_this_ep['params']['item']['episodeid'] = int(tmp_episode_id)
				T.json_query(Q.add_this_ep, False)
				log('episode added = ' + str(tmp_episode_id))
			else:
				tg = 't' + str(curr_candi)
				if tg in candidate_list:
					candidate_list.remove('t' + str(curr_candi))
				continue

			#add episode to added episode dictionary
			if not multi:
				if multipleshows:
					if curr_candi in randos:
						eps_list = ast.literal_eval(WINDOW.getProperty("%s.%s.odlist" % ('LazyTV',curr_candi))) + ast.literal_eval(WINDOW.getProperty("%s.%s.offlist" % ('LazyTV',curr_candi)))
					else:
						eps_list = ast.literal_eval(WINDOW.getProperty("%s.%s.odlist" % ('LazyTV',curr_candi)))
					added_ep_dict[curr_candi] = [WINDOW.getProperty("%s.%s.Season" % ('LazyTV', curr_candi)), WINDOW.getProperty("%s.%s.Episode" % ('LazyTV', curr_candi)),eps_list,WINDOW.getProperty("%s.%s.EpisodeID" % ('LazyTV', curr_candi))]
				else:
					added_ep_dict[curr_candi] = ''
			else:
				added_ep_dict[curr_candi] = [tmp_details[0],tmp_details[1],tmp_details[2],tmp_details[3]]

		elif candi_type == 'm':
			#add movie to playlist
			log('movieadd')
			add_this_movie['params']['item']['movieid'] = int(curr_candi)
			T.json_query(Q.add_this_movie, False)
			candidate_list.remove('m' + str(curr_candi))
		else:
			count = 99999

		count += 1

	WINDOW.setProperty("%s.playlist_running"	% ('LazyTV'), 'true')		# notifies the service that a playlist is running
	WINDOW.setProperty("LazyTV.rando_shuffle", 'true')						# notifies the service to re-randomise the randos

	xbmc.Player().play(xbmc.PlayList(1))
	#xbmc.executebuiltin('ActivateWindow(MyVideoPlaylist)')
	log('random_playlist_End')


def create_next_episode_list(population):

	#creates a list of next episodes for all shows or a filtered subset and adds them to a playlist
	log('create_nextep_list')

	global stay_puft
	global play_now
	global refresh_now

	stored_data_filtered = process_stored(population)

	if excl_randos:
		stored_data_filtered = [x for x in stored_data_filtered if x[1] not in randos]


	log(refresh_now)
	log(stay_puft)

	while stay_puft and not xbmc.abortRequested:


		if refresh_now:
			log('refreshing now')
			refresh_now = False
			try:
				del list_window
				del window_returner

				stored_data_filtered = process_stored(population)
				if excl_randos:
					stored_data_filtered = [x for x in stored_data_filtered if x[1] not in randos]              
			
			except:
				pass
			
			if skin == 1:
				xmlfile = "main.xml"
			elif skin == 2:
				xmlfile = "BigScreenList.xml"
			else:
				xmlfile = "DialogSelect.xml"

			list_window = yGUI(xmlfile, __scriptPath__, 'Default', data=stored_data_filtered)

			window_returner = myPlayer(parent=list_window)

			list_window.doModal()


		da_show = list_window.selected_show

		if da_show != 'null' and play_now:
			log('da_show not null, or play_now')

			play_now = False
			# this fix clears the playlist, adds the episode to the playlist, and then starts the playlist
			# it is needed because .strms will not start if using the executeJSONRPC method

			WINDOW.setProperty("%s.playlist_running"    % ('LazyTV'), 'listview')

			T.json_query(Q.clear_playlist, False)

			try:
				for ep in da_show:
					add_this_ep['params']['item']['episodeid'] = int(ep)
					T.json_query(Q.add_this_ep, False)
			except:
				add_this_ep['params']['item']['episodeid'] = int(da_show)
				T.json_query(Q.add_this_ep, False)

			xbmc.sleep(50)
			window_returner.play(xbmc.PlayList(1))
			xbmc.executebuiltin('ActivateWindow(12005)')
			da_show = 'null'

			WINDOW.setProperty("LazyTV.rando_shuffle", 'true')

		if not skin_return:
			stay_puft = False

		xbmc.sleep(500)

	del list_window
	del window_returner

	WINDOW.setProperty("LazyTV.rando_shuffle", 'true')                      # notifies the service to re-randomise the randos


class myPlayer(xbmc.Player):

	def __init__(self, parent, *args, **kwargs):
		xbmc.Player.__init__(self)
		self.dawindow = parent


	def onPlayBackStarted(self):
		log('Playbackstarted',reset=True)
		self.dawindow.close()

	def onPlayBackStopped(self):
		self.onPlayBackEnded()

	def onPlayBackEnded(self):
		log('Playbackended', reset =True)
		self.dawindow.doModal()




def main_entry():
	log('Main_entry')

	if filterYN:

		if populate_by_d == '1':

			if select_pl == '0':
				selected_pl = playlist_selection_window()
				population = {'playlist': selected_pl}

			else:
				#get setting for default_playlist
				if not default_playlist:
					population = {'none':''}
				else:
					population = {'playlist': default_playlist}
		else:
			population = {'usersel':spec_shows}
	else:
		population = {'none':''}


	if primary_function == '2':

		#assume this is selection
		choice = dialog.yesno('LazyTV', lang(32100),'',lang(32101), lang(32102),lang(32103))
		if choice < 0:
			sys.exit()

	elif primary_function == '1':
		choice = 1

	else:
		choice = 0


	if choice == 1:
		random_playlist(population)
	elif choice == 0:
		create_next_episode_list(population)



# =======================================================================
# this check is to ensure that the Ignore list from the previous addon 
# is respected and replaced in the new version
ignore = __setting__('IGNORE')
if ignore:
	T.convert_previous_settings(ignore, __setting)
# =======================================================================


#@ check if service is running
#@ start service if it isnt running
#@ check server version, if it is higher,
#	@ then check if this is CLONE, update this CLONE
# 	@ if service is lower, then restart service


#@ check if the show list is filtered if so then:
#@ check if there is a filter list or a playlist or playlist selection
#@ get list of showids, request list_items from service
#@ check for default primary function or user selection



class Main_Lazy:
	''' The main LazyTV interfacer '''

	def __init__(self):

		# s is a dictionary that holds the settings
		self.s = T.service_request({'pass_settings_dict': {}}, log)

		log('self.s: ' + str(self.s)[:100])

		# a list that contains all the episodes retrieved from the service 
		raw_all_epitems = T.service_request({'pass_all_epitems': {}}, log).get('pass_all_epitems',[])
		log('self.s: ' + str(raw_all_epitems)[:100])


		class dummy(xbmcgui.ListItem):
			def __init__(self):
				xbmcgui.ListItem.__init__(self)

		bla = []
		for x in raw_all_epitems:
			log('before: ')
			log(type(C.LazyEpisode))
			log(x.__class__)
			log(x.__class__.__bases__)
			log(type(x))
			log(type(xbmcgui.ListItem))
			log(type(dummy))

			bla.append(T.inst_extend(x, dummy))
			# x.__class__ = type('guiEp',(C.LazyEpisode, xbmcgui.ListItem), {})

			log('after: ')
			log(x.__class__)
			log(x.__class__.__bases__)
			log(type(x))
			log(type(xbmcgui.ListItem))	
		# request settings
		# request all list items


	def request_from_service(self, request_dict):
		''' Contacts the service and asks for data '''
		''' Can request:
						'all_list_items'         : [], 
						# receives back a list of all list_items

						'settings_dict'          : [], 
						# receives back the settings dictionary

						'another_single_episode' : [epid already used],
						# receives back a single new list_item

						'confirm_eps'            : [showid, epid]
						# receives back a dict of showid: 
						# { showid: NONE if epid is OD else list_item}


						'''
		address = ('localhost', 6714)

		s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		s.connect(address)
		s.send('Hello, world')
		data = s.recv(1024)
		s.close()
		print 'Received', repr(data)


if __name__ == "__main__":
	log('Default started')

	Main_Lazy()

	log('Gui... Gui NOOOOO!!')
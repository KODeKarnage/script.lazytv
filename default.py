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

#opens progress dialog, removes the cancel button
proglog = xbmcgui.DialogProgress()
proglog.create("LazyTV","Initializing...")
prog_window = xbmcgui.Window(10101)
xbmc.sleep(10)
cancel_button = prog_window.getControl(10)
cancel_button.setEnabled(False)
proglog.update(1, lang(32151))

bug_exists = False #Buggalo
try:
	__buggalo__    = xbmcaddon.Addon("script.module.buggalo")
	_bugversion_ = __buggalo__.getAddonInfo("version")
	bv = _bugversion_.split(".")
	if int(bv[0]) > 1 or (int(bv[0]) == 1 and int(bv[1]) > 1) or (int(bv[0]) == 1 and int(bv[1]) == 1 and int(bv[2]) > 3):
		import buggalo
		bug_exists = True
except:
	pass

__addon__         = xbmcaddon.Addon("script.lazytv")	
__setting__       = __addon__.getSetting
lang              = __addon__.getLocalizedString
dialog            = xbmcgui.Dialog()
scriptPath        = __addon__.getAddonInfo('path')
settings, IGNORES = get_settings()

__resource__      =  os.path.join(scriptPath, 'resources', 'lib')

sys.path.append(__resource__)


def log(vname, message):
	#if settings['debug']:
	xbmc.log(msg=vname + " -- " + str(message))

def gracefail(message):
	proglog.close()
	dialog.ok("LazyTV",message)
	sys.exit()

def criteria_filter():
	#apply the custom filter to get the list of allowable TV shows and episodes

	#retrieve all TV Shows
	all_s = json_query(show_request, True)

	#checks for the absence of unwatched tv shows in the library
	if 'tvshows' not in all_s:
		gracefail(lang(32201))
	else:
		all_shows = all_s['tvshows']

	#filter the TV shows by custom criteria
	filtered_showids = [show['tvshowid'] for show in all_shows 
	if str(show['tvshowid']) not in IGNORES[0] 
	and bool(set(show['genre']) & set(IGNORES[1])) == False
	and show['mpaa'] not in IGNORES[2]
	and (show['watchedepisodes'] > 0 or settings['premieres'] == 'true')
	and show['episode']>0]

	proglog.update(25, lang(32152))

	#filter out the showids not in all_shows
	shows_w_unwatched = [x['tvshowid'] for x in all_shows]
	filtered_showids = [x for x in filtered_showids if x in shows_w_unwatched]

	log('filtered_showids criteria filter',filtered_showids)

	if not filtered_showids:
		gracefail(lang(32202))

	#return the list of all and filtered shows
	return filtered_showids, all_shows


def smart_playlist_filter(playlist):
	# derive filtered_showids from smart playlist

	#retrieve the shows in the supplied playlist, save their ids to a list
	plf['params']['directory'] = playlist
	playlist_contents = json_query(plf, True)

	log('playlist_contents playlist filter',playlist_contents)

	if 'files' not in playlist_contents:
		gracefail(lang(32205))
	else:
		if not playlist_contents['files']:
			gracefail(lang(32205))
		else:
			for x in playlist_contents['files']:
				filtered_showids = [x['id'] for x in playlist_contents['files'] if x['type'] == 'tvshow']
				log('filtered_showids playlist contents',filtered_showids)
			if not filtered_showids:
				gracefail(lang(32206))

	proglog.update(25, lang(32152))

	#retrieves information on all tv shows
	all_s = json_query(show_request, True)

	#checks for the absence of unwatched tv shows in the library
	if 'tvshows' not in all_s:
		gracefail(lang(32201))
	else:
		all_shows = all_s['tvshows']

	#filter out the showids not in all_shows
	shows_w_unwatched = [x['tvshowid'] for x in all_shows]
	filtered_showids = [x for x in filtered_showids if x in shows_w_unwatched]

	#remove empty strings from the lists
	filtered_showids = filter(None, filtered_showids)
	log('filtered_showids playlist filter',filtered_showids)

	#returns the list of all and filtered shows and episodes
	return filtered_showids, all_shows


def populate_by_x():
	#populates the lists depending on the users selected playlist, or custom filter
	
	#updates progress dialog
	proglog.update(25, lang(32152))

	if settings['populate_by'] == '1':
		if settings['smart_pl'] == '':
			selected_pl = playlist_selection_window()
			if selected_pl == 'empty':
				filtered_showids, all_shows = criteria_filter()
			else:
				filtered_showids, all_shows = smart_playlist_filter(selected_pl)
		else:
			filtered_showids, all_shows = smart_playlist_filter(settings['smart_pl'])
	elif settings['populate_by'] == '2':
		selected_pl = playlist_selection_window()
		if selected_pl == 'empty':
			filtered_showids, all_shows = criteria_filter()
		else:
			filtered_showids, all_shows = smart_playlist_filter(selected_pl)
	else:
		filtered_showids, all_shows = criteria_filter()
	
	#remove empty strings from the lists
	filtered_showids = filter(None, filtered_showids)

	#returns the list of all and filtered shows and episodes
	proglog.update(25, lang(32153))
	return filtered_showids, all_shows


def create_playlist():
	#creates a random playlist of unwatched episodes

	partial_exists = False
	itera          = 0
	cycle          = 0
	_checked       = False
	playlist_tally = {}
	global resume_dict
	resume_dict    = {}
	plist_has_strm = False
	norm_start     = False

	#clears the playlist
	json_query(clear_playlist, False) 

	#generates the show and episode lists
	filtered_showids, all_shows = populate_by_x()

	#updates progross dialog
	proglog.update(50, lang(32154))

	#notifies the user when there is no shows in the show list
	if not filtered_showids and partial_exists == False:
		dialog.ok('LazyTV', lang(32150))

	#loop to add more files to the playlist, the loop carries on until the playlist is full or not shows are left in the show list
	while itera in range((settings['playlist_length']-1) if partial_exists == True else settings['playlist_length']):
		
		log('filtered_showids itera='+str(itera),filtered_showids)
		log('playlist_tally itera',playlist_tally)
		
		#counts the number of shows in the showlist, if it is ever empty, the loop ends
		show_count = len(filtered_showids)
		if show_count == 0 or not filtered_showids:
			itera = 10000

		else:

			#selects a show at random from the show list
			R = random.randint(0,show_count - 1)
			SHOWID = filtered_showids[R]

			log('SHOWID itera',SHOWID)
			
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
				filtered_showids = [x for x in filtered_showids if x != SHOWID]
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
						filtered_showids = [x for x in filtered_showids if x != SHOWID]
					else:
						playlist_tally[SHOWID] = (next_ep['season'],next_ep['episode'])

					#starts the player if this is the first entry, seeks to the right point if resume selected
					if itera == 0 and ".strm" not in clean_name:	

						norm_start = True
						proglog.close()
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
					filtered_showids = [x for x in filtered_showids if x != SHOWID]

				#records that he loop has completed one more time
				cycle +=1

				#infinite loop escape, is triggered if the cycle has run 100 times and streams are not allowed or there hasnt been anything added to the playlist
				#this may occur if all episodes of all shows are strms and strms are not permitted
				#if all the shows are streams, then exit the loop, otherwise, keep trying another 100 times
				if cycle % 100 == 0 and _checked == False and (settings['streams'] == 'false' or itera == 0):
					#confirm all eps are streams
					check_eps = [fix_name(x['file']) for x in eps if x['tvshowid'] in filtered_showids]
					if all(".strm" in ep.lower() for ep in check_eps):
						itera = 1000
					_checked = True
	
	proglog.close()
	
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
		xbmc.executebuiltin('ActivateWindow(10028)')
		self.player_active = False

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

		self.show_load_list = show_load_list

		for i in self.show_load_list:
			self.tmp = xbmcgui.ListItem(i[0],i[1],thumbnailImage=i[2])
			self.name_list.addItem(self.tmp)
			
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
			self.load_show_id = self.name_list.getSelectedPosition()
			self.close()


def create_next_episode_list():
	#creates a list of next episodes for all shows or a filtered subset and adds them to a playlist 
	
	global show_load_list
	load_show_id = -1

	
	ep_list = []

	#clears existing playlist
	json_query(clear_playlist, False) 

	#retrieves show and episode lists
	filtered_showids, all_shows = populate_by_x()

	#notifies the user if there are no unwatched shows
	if not filtered_showids:
		gracefail(lang(32150))

	#updates progress dialog
	proglog.update(50, lang(32155))

	#generates a list of the last played episodes of TV shows
	for SHOWID in filtered_showids:
		#gets the details the shows episodes
		eps_query['params']['tvshowid'] = SHOWID
		ep = json_query(eps_query, True)
		#accounts for the query not returning any TV shows
		if 'episodes' not in ep:
			gracefail(lang(32203))
		else:
			eps = ep['episodes']

		played_eps = [x for x in eps if x['playcount'] is not 0]
		if not played_eps:
			#if the show doesnt have any watched episodes, the season and episode are both zero
			Season = 0
			Episode = 0
			LastPlayed = ''			
		else:
			last_played_ep = sorted(played_eps, key =  lambda played_eps: (played_eps['season'], played_eps['episode']), reverse=True)[0]
			Season = last_played_ep['season']
			Episode = last_played_ep['episode']
			LastPlayed = last_played_ep['lastplayed']

		#creates list of unplayed episodes for the TV show
		unplayed_eps = [x for x in eps if ((x['season'] == Season and x['episode'] > Episode) or (x['season'] > Season))]
		if unplayed_eps:

			#sorts the list so the next to be played episode is first and removes empty strings
			sorted_ep = sorted(unplayed_eps, key = lambda unplayed_eps: (unplayed_eps['season'], unplayed_eps['episode']))
			sorted_ep = filter(None, sorted_ep)
			if sorted_ep:

				next_ep = sorted_ep[0]

				#replaces the lastplayed
				if not next_ep['lastplayed']:
					next_ep['lastplayed'] = LastPlayed

				#adds the episode to the episode list
				ep_list.append(next_ep.copy())

	# create a dict of tvshowids and shownames &thumbnails
	shownames = {}
	for x in all_shows:
		shownames[x['tvshowid']] = {}
		shownames[x['tvshowid']]['title'] = x['title']
		shownames[x['tvshowid']]['thumbnail'] = x['thumbnail']

	#today
	tdf = '%Y-%m-%d'
	today = time.strptime(str(datetime.date.today()), tdf)
	todate = datetime.date(today[0],today[1],today[2])

	#sort episode list
	if settings['sort_list_by'] == '0': # Title

		active_list = [(shownames[x['tvshowid']]['title'] + ': ' + x['label'], ("" if not x['resume']['position'] and not x['lastplayed'] else "(") +  ("" if not x['resume']['position'] else str(int(float(x['resume']['position'])/float(x['resume']['total'])*100.0)) +"%") + (",  " if x['resume']['position'] and x['lastplayed'] else "") + ("" if not x['lastplayed'] else day_calc(x['lastplayed'],todate,'diff')) + (")" if x['resume']['position'] and not x['lastplayed'] else ""), shownames[x['tvshowid']]['thumbnail'], x['episodeid']) for x in ep_list]
		active_list.sort()

		show_load_list = [(x[0],x[1],x[2]) for x in active_list]
		id_list = [x[3] for x in active_list]

	else: # last played

		active_list = [(day_calc(x['lastplayed'],todate,'date_list'), shownames[x['tvshowid']]['title'] + ': ' + x['label'], ("(" if x['resume']['position'] == 0 else "(" + str(int(float(x['resume']['position'])/float(x['resume']['total'])*100.0)) +"%,  ") + day_calc(x['lastplayed'],todate,'diff'), shownames[x['tvshowid']]['thumbnail'], x['episodeid']) for x in ep_list if x['lastplayed']]
		prem_list = [(shownames[x['tvshowid']]['title'] + ': ' + x['label'], ("" if x['resume']['position'] == 0 else "(" + str(int(float(x['resume']['position'])/float(x['resume']['total'])*100.0)) +"%"), shownames[x['tvshowid']]['thumbnail'], x['episodeid']) for x in ep_list  if not x['lastplayed']]

		prem_list.sort()
		active_list.sort(reverse=True)		
		active_list_final = [(x[1],x[2],x[3],x[4]) for x in active_list]

		show_load_list = active_list_final + prem_list
		id_list = [x[3] for x in show_load_list]

	log('id_list list',id_list)

	proglog.close()

	list_window = xGUI("DialogSelect.xml", scriptPath, 'Default')
	list_window.doModal()
	
	if list_window.ctrl6failed == True:
		del list_window
		user_options = []
		for xi in show_load_list:
			user_options.append(xi[0] + "  " + xi[1])
		load_show_id= xbmcgui.Dialog().select("LazyTV", user_options)
	
	else:
		load_show_id = list_window.load_show_id
		#del list_window


	if load_show_id != -1:
		play_command['params']['item']['episodeid'] = id_list[load_show_id]
		try:
			json_query(clear_playlist, False) 
			json_query(dict_engine(id_list[load_show_id],'episodeid'), False)
			xbmc.Player().play(xbmc.PlayList(1))
			#json_query(play_command, False) 
		except:
			gracefail(lang(32207))


log('Settings',settings)
log('getprop',xbmcgui.Window(10000).getProperty('%s_service_running' % __addon__))

if __name__ == "__main__":

	#check if service is running, if it isnt, then start it
	

	service_file  = os.path.join(scriptPath, 'service.py')
	# Set the service to not-resume when we start it manually
	try:
		xbmc.executebuiltin("XBMC.RunScript(%s)" % service_file)
	except:
		pass

	if bug_exists:

		buggalo.GMAIL_RECIPIENT = 'subliminal.karnage@gmail.com'

		try:
			
			if settings['first_run'] == 'true':
				__addon__.setSetting(id="first_run",value="false")
				xbmcaddon.Addon().openSettings()
			elif settings['primary_function'] == '0':
				create_playlist()
			elif settings['primary_function'] == '1':
				create_next_episode_list()
			elif settings['primary_function'] == '2':
				choice = dialog.yesno('LazyTV', lang(32158),'',lang(32159), lang(32160),lang(32161))
				if choice == 1:
					create_playlist()
				elif choice == 0:
					create_next_episode_list()
				else:
					pass
		except Exception:
			proglog.close()
			buggalo.onExceptionRaised()
	else:

		try:

			if settings['first_run'] == 'true':
				__addon__.setSetting(id="first_run",value="false")
				xbmcaddon.Addon().openSettings()
			elif settings['primary_function'] == '0':
				create_playlist()
			elif settings['primary_function'] == '1':
				create_next_episode_list()
			elif settings['primary_function'] == '2':
				choice = dialog.yesno('LazyTV', lang(32158),'',lang(32159), lang(32160),lang(32161))
				if choice == 1:
					create_playlist()
				elif choice == 0:
					create_next_episode_list()
				else:
					pass
		except:
			proglog.close()
			dialog.ok('LazyTV', lang(32156), lang(32157))

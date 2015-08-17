# XBMC modules
import xbmc
import xbmcaddon
import xbmcgui

# Standard Library Modules
import ast
import collections
import datetime
import json
import os
import pickle
import pprint
import Queue
import random
import re
import sys
import time
import traceback

try:
    from cStringIO import StringIO
except:
    from StringIO import StringIO

# LazyTV Modules
import lazy_queries 			as Q
import lazy_tools   			as T
import lazy_list    			as G
import lazy_random  			as R 
from   lazy_comms				import LazyComms
from   lazy_interaction 		import LazyInteraction
from   lazy_list 				import LazyList
from   lazy_logger 				import LazyLogger
from   lazy_monitor 			import LazyMonitor
from   lazy_player 				import LazyPlayer
from   lazy_playlist 			import LazyPlayListMaintainer
from   lazy_random 				import LazyRandomiser
from   lazy_settings_handler 	import LazySettingsHandler
from   lazy_tracking_imp 		import LazyTrackingImp
from   lazy_tvshow 				import LazyTVShow
from   lazy_wrangler			import LazyWrangler

# This is a throwaway variable to deal with a python bug
T.datetime_bug_workaround()

# addon structure variables
__addon__               = xbmcaddon.Addon()
__addonid__             = __addon__.getAddonInfo('id')
__addonversion__        = tuple([int(x) for x in __addon__.getAddonInfo('version').split('.')])
__scriptPath__          = __addon__.getAddonInfo('path')
__setting__             = __addon__.getSetting
__release__			 	= T.current_KODI_version()


class LazyService(object):

	def __init__(self):

		# GUI constructs
		self.WINDOW = xbmcgui.Window(10000)
		self.DIALOG = xbmcgui.Dialog()

		# store addon service information
		self.WINDOW.setProperty("LazyTV.Version", str(__addonversion__))
		self.WINDOW.setProperty("LazyTV.ServicePath", str(__scriptPath__))
		self.WINDOW.setProperty('LazyTV_service_running', 'starting')

		# creates the logger & translator
		keep_logs 	= True if __setting__('logging') == 'true' else False
		self.logger = LazyLogger(__addon__, __addonid__ + ' service', keep_logs)
		self.log    = self.logger.post_log
		self.lang   = self.logger.lang

		self.log('LazyTV Running, version: ' + str(__release__))

		# show_store holds all the TV show objects
		self.show_store = {}

		# Try to load the previously saved show_store info.
		# Even though the full update will run, this will make the store_available
		# immediately on LazyTV instantiation.
		'''self.unpickle_show_store() ## will not work as changes to attributes will
			not be saved with pickle.'''

		# communication with the LazyMonitor and LazyPlayer and LazyUI
		# is handled using this queue and instructions are passed as ACTIONS
		# multiple items can be included in each ACTION
		# the queue takes a dict with the following structure,
		# { ACTION: DATA, ACTION: DATA, ...}
		self.lazy_queue = Queue.Queue()

		# communications queue for sending data to the GUI
		self.comm_queue = Queue.Queue()

		# create lazy_settings
		self.lazy_settings = LazySettingsHandler(self, __setting__, self.log, self.lang)
		
		# generate settings dictionary
		self.s = self.lazy_settings.get_settings_dict()

		# spawns an instance of the position_tracking_IMP, which will monitor the position
		# of playing episodes and announce when the swap_over has been triggered
		self.IMP = LazyTrackingImp(self.s['trigger_postion_metric'], self.lazy_queue, self.log)

		# spawns an instance of the LazyPlayer
		self.LazyPlayer = LazyPlayer(queue = self.lazy_queue, log = self.log)

		# spawns an instance of the LazyMonitor
		self.LazyMonitor = LazyMonitor(queue = self.lazy_queue, log = self.log)

		# spawns the LazyComms to handle communications with the GUI
		self.LazyComms = LazyComms(self.lazy_queue, self.comm_queue, self.log)
		self.LazyComms.start()

		# spawn an instance of the Show Wrangler, this handles all interations with the TV Shows
		self.Wrangler = LazyWrangler(self.show_store, self, self.s, self.log, self.lang)

		# spawn a LazyInteraction class to handle all interactions
		self.lazy_interaction = LazyInteraction(self.s, self.log, self.lang, __release__)

		# playlist playing indicates whether a playlist is playing,
		self.playlist = False

		# Tracks whether the currently playing show have been swapped. This occurs
		# when the trigger is pulled by the IMP
		self.swapped = False

		# holds the 'next episode' data temporarily
		self.temp_next_epid = False

		# ACTION dictionary
		self.action_dict = {

				'episode_is_playing'    : self.episode_is_playing, 		# DATA: {allow_prev: v, showid: x, epid: y, duration: z, resume: aa}
				'player_has_ended'      : self.player_has_ended,
				'IMP_reports_trigger'   : self.swap_triggered,
				'manual_watched_change' : self.manual_watched_change, 	# DATA: epid
				'full_library_refresh'	: self.full_library_refresh,
				'update_smartplaylist'	: self.update_smartplaylist, 	# DATA showid
				'movie_is_playing'		: self.movie_is_playing, 		# DATA {'movieid': movieid}
				'retrieve_add_ep'		: self.retrieve_add_ep, 		# DATA {'showid': x, 'epid_list': [] }
				'lazy_playlist_started' : self.lazy_playlist_started,
				'lazy_playlist_ended'   : self.lazy_playlist_ended,
				'version_request'		: self.version_request, 
				'user_called'			: self.user_called, 			# DATA {settings from the calling script}
				'open_random_player'	: self.open_random_player,																
				'open_lazy_gui'			: self.open_lazy_gui, 			# DATA {permitted_showids: [], 
																		#		settings: {
																		#			skinorno: number, 
																		#			skin_return: bool,
																		#			limit_shows: bool,
																		# 			window_length: int,
																		#			sort_by: int,
																		#			sort_reverse: bool
																		#			exclude_randos: bool}}
						}




		# clear the queue, this removes noise from the initial setup
		self.lazy_queue.queue.clear()

		# create the smartplaylist maintainer
		self.playlist_maintainer = LazyPlayListMaintainer(self.s, self.show_store, self.log)

		# apply the initial settings, includes initiating the smart playlist
		self.lazy_settings.apply_settings(delta_dict = self.s, first_run = True)

		# daemon keeps everything alive and monitors the queue for instructions
		self._dispatch_daemon()


	def open_lazy_gui(self, permitted_showids):
		''' opens the lazy_gui in a new thread 
			provides the listitems, sort order, list length, skin options '''

		if self.s.get('skinorno', False) == 1:
			xmlfile = "script-lazytv-main.xml"

		elif self.s.get('skinorno', False) == 2:
			xmlfile = "script-lazytv-BigScreenList.xml"

		else:
			xmlfile = "script-lazytv-DialogSelect.xml"

		epitems = self.Wrangler.pass_all_epitems(permitted_showids)

		self.active_gui = LazyList(xmlfile, __scriptPath__, epitems, self.s, self.log, self.lang)

		self.active_gui.start()


	def open_random_player(self, permitted_showids):
		''' calls for the creation of a randomised playlist of next to watch shows '''

		self.log('Open random player called')

		episode_list = self.Wrangler.pass_all_epitems(permitted_showids)

		self.lazy_randomiser = LazyRandomiser(self, episode_list, self.s, self.log, self.lang)


	def full_library_refresh(self):
		''' Passes the show store interaction request to the LazyWrangler. '''

		self.Wrangler.full_library_refresh()


	def manual_watched_change(self, epid):
		''' Passes the show store interaction request to the LazyWrangler. '''

		self.Wrangler.manual_watched_change(epid)


	def swap_triggered(self, showid):
		''' Passes the show store interaction request to the LazyWrangler. '''

		self.swapped = self.Wrangler.swap_triggered(showid)


	def retrieve_add_ep(self, showid, epid_list, respond_in_comms=True):
		''' Passes the show store interaction request to the LazyWrangler. '''

		return self.Wrangler.retrieve_add_ep(self, showid, epid_list, respond_in_comms=True)


	def update_smartplaylist(self, data):

		self.playlist_maintainer.update_playlist([data])


	# MAIN method
	def version_request(self):
		''' Sends back the version number of the Service '''

		self.comm_queue.put({'version': __addonversion__, 'path' : __scriptPath__})


	# DAEMON
	def _dispatch_daemon(self):
		''' Keeps everything alive, gets instructions from the queue,
			and executes them '''

		self.log('LazyTV daemon started')

		# Post notification that LazyTV has started
		if self.s['startup']:

			xbmc.executebuiltin('Notification(%s,%s,%i)' % ('LazyTV',self.lang(32173),5000))

		while not xbmc.abortRequested:

			xbmc.sleep(10)

			try:

				instruction = self.lazy_queue.get(False)

			except Queue.Empty:

				continue

			self.log(instruction, 'Processing instruction: ')

			for k, v in instruction.iteritems():

				self.log(k, 'function key')
				self.log(v, 'function data')

				# try:
				self.action_dict[k](**v)

			self.lazy_queue.task_done()

			self.log('Instruction processing complete')

		self.clear_listitems()

	
	# EXIT method
	def clear_listitems(self):
		''' clears the listitems from memory '''

		rem_list = [v.showID for k, v in self.show_store.iteritems()]

		for showid in rem_list:

			self.Wrangler.remove_show(showid, update_spl = False)

		self.LazyComms.stop()

		del self.LazyPlayer
		del self.LazyMonitor


	# ON PLAY method
	def episode_is_playing(self, allow_prev, showid, epid, duration, resume):
		''' This process is triggered when the LazyPlayer notifies Main when an episode is playing. '''

		self.log('Episode is playing: showid= {}, epid= {}, allowprev= {}'.format(showid, epid, allow_prev))

		self.swapped = False

		# start the IMP monitoring the currently playing episode
		self.IMP.begin_monitoring_episode(showid, duration)

		# create shorthand for the show
		show = self.show_store[showid]

		# update show.last_played attribute
		self.log(show.last_played, 'lastplayed updated: ')
		show.last_played = T.day_conv()

		# update widget data in Home Window
		self.update_widget_data()

		# check for prior unwatched episodes
		self.prev_check_handler(epid, allow_prev)

		# if in LazyTV random playlist, then resume partially watched
		self.resume_partials(resume)

		# tell show to set up the next episode to play and store it in temp_ep
		self.log(epid, 'tee up requested: ')
		epid_check = show.tee_up_ep(epid)

		# if epid_check returns false, there is no next show
		# record the epid for easy access by the next prompt
		self.temp_next_epid = epid if epid_check else False


	# ON PLAY method
	def movie_is_playing(self, movieid):
		''' If a movie is playing in the random player, check whether playlist is playing, 
			if so then check random resume point '''

		if self.playlist:

			playcount = xbmc.getInfoLabel('VideoPlayer.PlayCount')

			if playcount != '0': #@@@@@ GET PLAYCOUNT OF THE MOVIE, ONLY SEEK IF IT IS MORE THAN 0:

				time = T.runtime_converter(xbmc.getInfoLabel('Player.Duration'))

				seek_point = int(100 * (time * 0.75 * ((random.randint(0,100) / 100.0) ** 2)) / time)

				Q.seek['params']['value'] = seek_point

				T.json_query(Q.seek)


	# ON PLAY method
	def post_notification(self, show):

		self.log('Notification Test; playlist_notifications: {}, self.playlist:: {}'.format(self.s['playlist_notifications'], self.playlist))
		if self.s['playlist_notifications'] and self.playlist:



			self.log('posting notification: showtitle: {}, season: {}, episode: {}'.format(show.show_title,show.Season,show.Episode))

			xbmc.executebuiltin('Notification(%s,%s S%sE%s,%i)' % (self.lang(32163),show.show_title,show.Season,show.Episode,5000))


	# ON PLAY method
	def resume_partials(self, resume):
		''' Jumps to a specific point in the episode. '''

		self.log('Resume Partials Test; resume_partials: {}, self.playlist:: {}'.format(self.s['resume_partials'], self.playlist))
		if self.s['resume_partials'] and self.playlist:

			position = resume.get('position',0)
			total = resume.get('total',0)

			if position:
				# call resume partials only if there is a resume point in the show

				seek_point = int((float(position) / float(total)) *100)
				
				Q.seek['params']['value'] = seek_point

				self.log('seeking to : {}'.format(seek_point))
				T.json_query(Q.seek)


	# ON PLAY method
	def prev_check_handler(self, epid, allow_prev):
		''' handles the check for the previous episode '''

		self.log('Prev Test; allow_prev: {}, prevcheck_setting: {}, self.playlist: {}'.format(allow_prev, self.s['prevcheck'], not self.playlist))
		if all([allow_prev, self.s['prevcheck'], not self.playlist]):

			self.log('prev_check_handler reached')

			showid = self.reverse_lookup(epid)

			if not showid:
				self.log('could not find showid')
				return

			show = self.show_store[showid]

			# retrieves tuple with showtitle, season, episode
			prev_deets = show.look_for_prev_unwatched(epid)

			if not prev_deets:

				self.log('no prev_deets')
				return

			pepid, showtitle, season, episode = prev_deets

			#pause, wait 500 for the thing to actually start
			xbmc.sleep(500)
			xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Player.PlayPause","params":{"playerid":1,"play":false},"id":1}')

			#show notification
			self.log('prev_deets, pepid: {}, showtitle: {}, season: {}, episode: {}'.format(pepid, showtitle, season, episode))
			selection = self.lazy_interaction.display_prev_check(showtitle, season, episode)

			self.log(selection, 'user selection: ')

			if selection == 0:
				# unpause
				xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Player.PlayPause","params":{"playerid":1,"play":true},"id":1}')
			else:
				# stop and play previous episode
				xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Player.Stop", "params": { "playerid": 1 }, "id": 1}')
				xbmc.sleep(100)
				xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "Player.Open", "params": { "item": { "episodeid": %d }, "options":{ "resume": true }  }, "id": 1 }' % (pepid))


	# ON PLAY Method
	def lazy_playlist_started(self):
		''' Called after being notified by the GUI that the random playlist 
			has been initiated.
			Tells the imp that this is a random player playlist. The imp
			will then monitor for something to not be playing for at least 
			XX seconds before sending back notification that the random
			playlist has ended '''

		self.playlist = True

		self.IMP.begin_monitoring_lazy_playlist()


	# ON PLAY method
	def lazy_playlist_ended(self):
		''' Sets self.playlist = FALSE   '''

		self.playlist = False

	
	# ON END method
	def player_has_ended(self, ended_showid, ended_epid):
		''' Triggered when the player sends notification that a video has ended (or was stopped by the user) '''

		self.log('Player has ended, service function reached')

		# stops the IMP episode tracking daemon
		self.IMP.episode_active = False

		# starts the IMP playlist over tracking daemon
		if self.playlist:
			self.log('Request sent to imp to start checking for lazy_playlist end')
			self.IMP.begin_monitoring_lazy_playlist()

		self.log(self.playlist,'self.playlist: ')
		self.log(self.s['nextprompt'], 'self.s["nextprompt"]')
		self.log(self.swapped, 'self.swapped')

		# checks for the next episode if the show has swapped and if it isnt in a playlist
		if all([self.s['nextprompt'], not self.playlist, self.swapped]):

			self.log('next prompt handler called')

			# call the next prompt handler
			self.next_prompt_handler()

		# This would occur if the show has not swapped over, and was stopped by the user.
		# We want to change the Resume status of the episode, and change the percentage watched as well.
		# We can leave the last_played attribute as it is, as that is handled when the episode STARTS playing.
		if not self.swapped and ended_showid is not None:
			show = self.show_store.get(ended_showid, None)
			if show:
				for k, episode in show.eps_store.iteritems():
					if episode.epid == ended_epid:
						episode.retrieve_details(resume_only=True)

		# revert swapped back to its natural state
		self.swapped        = False
		self.temp_next_epid = False


	# ON STOP method
	def next_prompt_handler(self):
		''' handles the next ep functionality '''

		self.log('next prompt handler reached')

		show = self.show_store[self.swapped]

		# if the show isnt in the od_episodes, then it must be:
		#		: watched already, so show ODEP
		#		: prior to the ODEP, so show ODEP
		#		: in erro, so show ODEP
		if self.temp_next_epid not in show.od_episodes:

			self.log('next_prompt_handler: temp epid not in show.od_episodes')

			self.log(self.temp_next_epid)
			self.log(show.od_episodes)
			self.log(self.show_store[self.swapped].eps_store['on_deck_ep'].epid)
			self.log(self.show_store[self.swapped].eps_store['temp_ep'].epid)

			next_ep = show.eps_store.get('on_deck_ep', False)

		else:

			self.log('next_prompt_handler: temp epid in show.od_episodes')

			self.log(self.temp_next_epid)
			self.log(show.od_episodes)
			self.log(self.show_store[self.swapped].eps_store['on_deck_ep'].epid)
			self.log(self.show_store[self.swapped].eps_store['temp_ep'].epid)

			next_ep = show.eps_store.get('temp_ep', False)

		if next_ep:

			self.log(next_ep, 'next_ep exists')

			pause = False

			#give the chance for the playlist to start the next item
			xbmc.sleep(750)	

			# check if another show is playing, if so then pause it
			if xbmc.getInfoLabel('VideoPlayer.TVShowTitle'):

				self.log('show title found, paused')

				xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Player.PlayPause","params":{"playerid":1,"play":false},"id":1}')
				pause = True
		
			# variables for the prompt
			nepid 	  = next_ep.epid
			season    = next_ep.Season
			episode   = next_ep.Episode
			showtitle = next_ep.show_title

			# show prompt
			selection = self.lazy_interaction.next_ep_prompt(showtitle, season, episode)

			self.log(selection, 'user selection')
			if selection == 1:
				# play next episode
				self.log(nepid, 'playing next ep: ')

				# clear playlist
				xbmc.executeJSONRPC('{"jsonrpc":"2.0", "method":"Playlist.Clear","params": {"playlistid": 1},"id": 1}')

				# add the episode to a playlist
				Q.add_this_ep['params']['item']['episodeid'] = int(nepid)
				
				json_query(Q.add_this_ep)

				xbmc.sleep(50)

				#begin playlist
				xbmc.Player().play(xbmc.PlayList(1))

			# unpause if paused
			if pause:
				
				self.log('unpausing')

				xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Player.PlayPause","params":{"playerid":1,"play":true},"id":1}')




	# TOOL
	def reverse_lookup(self, epid):
		''' finds the showid given a specific epid,
			the loop will break as soon as it is found '''

		self.log(epid, 'reverse_lookup reached: ')

		for k, show in self.show_store.iteritems():

				for ep in show.episode_list:

					if ep == epid:

						return k

		return False


	# TOOL
	def check_if_playlist(self):
		''' checks how many items are currently playing '''

		self.log('check_if_playlist reached')

		#FUNCTION: STILL TO DO

		pll = xbmc.getInfoLabel('VideoPlayer.PlaylistLength')

		self.playlist = True if pll != '1' else False

		self.log(self.playlist, 'Is playlist? ')


	# JUNK
	def empty_method(self, **kwargs):
		''' escape method '''

		pass


	# TOOL
	def pickle_show_store(self):
		''' Saves the show store to the addon Settings. This allows LazyTV 
			to start up very quickly. '''

		self.log('pickle_show_store reached')

		# pickling to file for testig only
		pickle_file = os.path.join(xbmc.translatePath('special://profile/playlists/video/'),'pickle.p')
		pickle.dump( self.show_store, open( pickle_file, "wb" ) )
		size = os.path.getsize(pickle_file)

		# create the stringIO object
		memIO = StringIO()

		# pickle the show_store into the object
		pickle.dump( self.show_store, memIO )

		# add the object to the settings
		__addon__.setSetting('pickled_show_store', memIO)

		# close out of the stringIO object
		memIO.close()

		self.log(size, 'show store pickled, file size: ')


	# TOOL
	def unpickle_show_store(self):
		''' Reloads the show_store for quick start-up '''

		self.log('unpickle_show_store reached')

		# create the stringIO object
		memIO = StringIO()

		# read the setting into the object
		pickled_tink = __setting__('pickled_show_store')

		# if the text isnt blank, then reload the show_store
		if pickled_tink: 
			memIO.write()

			self.show_store = pickle.load(memIO)

		memIO.close()

		self.log('unpickle_show_store complete')


	# USER INTERACTION
	def user_called(self, settings_from_script):

		''' This method is called when the user calls LazyTV from Kodi. It is sent a message from the default.py which contains 
			the relevant settings. '''

		# playlist used for filtering
		self.playlist = 'empty'

		# remove the randos and logging from the supplied settings dictionary, randos are only set in the MASTER addon.
		# this is required as some clones will have randos and logging in their userdata/addon_data/Settings.xml
		if 'randos' in settings_from_script:
			del settings_from_script['randos']

		if 'logging' in settings_from_script:
			del settings_from_script['logging']

		# updates the existing settings with the provided data.
		self.s.update(settings_from_script)
		
		self.permitted_ids = 'all'

		# allow the user to select a playlist if they wish
		if self.s['filterYN']:

			# 'populate_by_d' == 0, for populate using the users selection
			# 'populate_by_d' == 1, for populate using a playlist

			# 'select_pl' == 0, means the user wants to select the playlist themselves in real time
			# 'select_pl' == 1, means the user wants to use the deafult playlist (that they chose in settings)

			# populate using playlist, and select which playlist on launch
			if self.s['populate_by_d'] == 1 and self.s['select_pl'] == 0:

				self.log('opening playlist selection window')

				self.playlist = T.playlist_selection_window(self.lang)

			# populate with playlist, and use default playlist
			elif self.s['populate_by_d'] == 1 and self.s['select_pl'] == 1:
				self.playlist = self.s['users_spl', 'empty']

			# populate with the users manual selections
			else:

				self.log('User selection: %s' % self.s.get('selection','Failed'))

				manual_selection = self.s.get('selection',[]) #.replace('[','').replace(']','')

				# manual_selection = manual_selection.split(',')
				
			# retrieve permitted showids
			if self.s['populate_by_d'] == 0:

				self.permitted_ids = [int(x) for x in manual_selection]

				if not self.permitted_ids:

					self.permitted_ids = 'all'					

			elif self.playlist != 'empty':

				self.permitted_ids = T.convert_pl_to_showlist(self.playlist)

			else:
				self.permitted_ids = 'all'

		# determine the required action
		# primary functions are 1: random_playlist, 0: lazy_gui, 2: user_choice
		self.primary_function = self.s['primary_function']

		if self.primary_function == 2:

			# show the gui allowing the user to select their own action
			self.primary_function = self.lazy_interaction.user_input_launch_action()


		# call the primary function and pass the permitted shows
		if self.primary_function == 1:

			self.lazy_queue.put({'open_random_player': {'permitted_showids': self.permitted_ids}})

		else:

			self.lazy_queue.put({'open_lazy_gui': {'permitted_showids': self.permitted_ids}})



	# MAIN method
	def update_widget_data(self):
		''' Updates the widget data in the Home Window.
			The Widget data is the next episode show information stored in the Home Window with key structure:
			lazytv.widget.INTEGER.property 

			The widget order is ALWAYS based on the last played time.
		'''

		show_list_with_lastplayed = [(v.showID, v.last_played) for k, v in self.show_store.iteritems()]
		
		show_list = [x[0] for x in sorted(show_list_with_lastplayed, key= lambda x: x[1], reverse=True)]

		adj = 0
		for i, showID in enumerate(show_list):
			try:
				result = self.show_store[showID].update_window_data(widget_order= i-adj)

			except Exception as e:
			
				self.log('update_widget_data() exception occurred: %s' % type(e).__name__)
				self.log('update_widget_data() exception traceback:\n\n%s' % traceback.format_exc())

				result = 'no_episode'

			# If there is no new show to be added, then step the adjustment by one and move on to the next show.
			# This adjsutment is required to make sure the widget entries are in consecutive order with now gaps.
			if result == 'no_episode':
				adj += 1


	# MAIN method
	def Update_GUI(self):
		''' Updates the gui (if it exists) with the new episode information. '''

		try:
			epitems = self.Wrangler.pass_all_epitems(self.permitted_ids)			
			
			self.active_gui.update_GUI(epitems)

		except NameError:
			self.log('GUI Update failed, GUI not found')
			pass

		except AttributeError:
			self.log('No permitted IDs exist yet')

		except Exception as e:
		
			self.log('Update GUI exception occurred: %s' % type(e).__name__)
			self.log('Update GUI exception traceback:\n\n%s' % traceback.format_exc())

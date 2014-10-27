# XBMC Modules
import xbmc
import xbmcaddon
import xbmcgui

# Standard Modules
import time
import ast
import threading
import socket
import Queue
import os
import json
import pickle
import select
import sys
sys.path.append(xbmc.translatePath(os.path.join(xbmcaddon.Addon().getAddonInfo('path'), 'resources','lib')))

# LazyTV Modules
import lazy_classes as C
import lazy_queries as Q
import lazy_tools   as T

class lazy_logger(object):
	''' adds addon specific logging to xbmc.log '''

	def __init__(self, addon, addonid, logging_enabled):
		self.addon       = addon
		self.addonid     = addonid
		self.keep_logs   = logging_enabled
		self.base_time   = time.time()
		self.start_time  = time.time()

	def post_log(self, message, label = '', reset = False):

		if self.keep_logs:

			new_time    	= time.time()
			gap_time 		= "%5f" % (new_time - self.start_time)
			total_gap  		= "%5f" % (new_time - self.base_time)
			self.base_time  = start_time if reset else self.base_time
			self.start_time = new_time

			xbmc.log(msg = '{} : {} :: {} ::: {} - {} '.format(self.addonid, total_gap, gap_time, label, str(message)[:1000]) )

	def logging_switch(self, switch):

		self.keep_logs = switch

	def lang(self, str_id):

		return self.addon.getLocalizedString(str_id).encode( 'utf-8', 'ignore' )


class settings_handler(object):
	''' handles the retrieval and cleaning of addon settings '''

	def __init__(self, setting_function):

		self.setting_function = setting_function

		self.firstrun = True
		self.settings_dict = {}

		self.id_substitute = {
			'playlist_notifications': 'notify',
			'keep_logs'				: 'logging',
		}

		self.setting_strings = [
			'playlist_notifications', 
			'resume_partials',
			'keep_logs',
			'nextprompt',    
			'nextprompt_or', 
			'startup',       
			'promptduration', 
			'prevcheck',      
			'promptdefaultaction',  
			'moviemid',  
			'randos',           
			'first_run',            
			'startup',              
			'maintainsmartplaylist',
			'trigger_postion_metric',
			'skinorno',
			'movieweight',
			'filterYN',
			'multipleshows',
			'premieres',
			'limitshows',
			'movies',
			'moviesw',
			'noshow',
			'excl_randos',
			'sort_reverse',
			'start_partials',
			'skin_return',
			'window_length',
			'length',
			'sort_by',
			'primary_function',
			'populate_by_d',
			'select_pl',
			'users_spl',
			'selection',
			'IGNORE',

		]


	def clean(self, setting_id):
		''' retrieves and changes the setting into a usable state '''

		if setting_id in self.id_substitute.keys():
			setting_id = self.id_substitute.get(setting_id,setting_id)

		value = self.setting_function(setting_id)

		if value == 'true':
			# convert string bool into real bool
			value = True 

		elif value == 'false':
			# convert string bool into real bool
			value = False

		elif setting_id == 'promptduration':
			# change a zero prompt duration to a non-zero instant
			if value == 0:
				value = 1 / 1000.0
			else:
				value = int(float(value))

		elif setting_id in ['randos', 'selection']:
			# turn the randos string into a real string
			if value == 'none':
				value = []
			else:
				value = ast.literal_eval(value)
			
		else:
			# convert number values into integers
			try:
				value = int(float(value))
			except:
				# otherwise just use the string
				pass

		return value


	def get_settings_dict(self, current_dict={}):
		''' provides a dictionary of all the changed settings,
			where there is no current dict, the full settings would be sent '''

		new_settings_dict = self.construct_settings_dict()

		delta_dict = {}

		for k, v in new_settings_dict.iteritems():
			if v != current_dict.get(k,''):
				delta_dict[k] = v

		return delta_dict


	def construct_settings_dict(self):
		''' creates the settings dictionary '''

		s = {k: self.clean(k) for k in self.setting_strings}

		return s


class postion_tracking_IMP(object):
	''' The IMP will monitor the episode that is playing
		and put an Alert to Main when it passes a certain point in its playback. '''

	def __init__(self, trigger_postion_metric, queue, log):

		# the trigger_postion_metric is the metric that is used to determine the 
		# position in playback when the notification should be Put to Main
		self.trigger_postion_metric = trigger_postion_metric

		# the trigger point recalculated for each new show
		self.trigger_point = False

		# logging function
		self.log = log
		self.log('IMP instantiated')
		self.log(trigger_postion_metric, 'trigger_postion_metric = ')

		# stores the showid of the show being monitored
		self.showid = False

		# self.queue is the Queue used to communicate with Main
		self.queue = queue

		# the current activity status of the episode tracking responsibility
		self.episode_active = False

		# the current activity status of the playlist tracking responsibility
		self.lazy_playlist_active = False

		# flag to abandon playlist_monitoring_daemon
		self.abandon_playlist_daemon = False


	def begin_monitoring_episode(self, showid, duration):
		''' Starts monitoring the episode that is playing to check whether
			it is past a specific position in its playback. '''

		self.log('IMP monitor starting: showid= {}, duration = {}'.format(showid, duration))

		self.trigger_point = self.calculate_trigger_point(duration)

		self.log(self.trigger_point, 'trigger_point = ')

		self.showid = showid

		self.episode_active = True
		
		little_imp = threading.Thread(target = self.monitor_daemon)

		little_imp.start()


	def begin_monitoring_lazy_playlist(self):
		''' Waits a certain amount of time to see if a new playlist has
			been started. If it hasn't then assume the lazy_playlist is over. '''

		little_imp = threading.Thread(target = self.playlist_monitoring_daemon)

		little_imp.start()


	def playlist_monitoring_daemon(self, wait_time = 15):

		# convert wait time to microseconds
		wait_time = wait_time * 1000

		interval = 100
		time_waited = 0

		# loop until xbmc asks to abort, the abandon signal is sent, or the time wait is 
		# more than the critical vale		
		while all([not xbmc.abortRequested, wait_time > time_waited, not self.abandon_playlist_daemon]):
			xbmc.sleep(interval)
			time_waited += interval

		if self.abandon_playlist_daemon:

			# if the abandon signal was sent, then reset back to False
			self.abandon_playlist_daemon = False

		else:

			# check if item is playing and whether it is playing a playlist
			pll = xbmc.getInfoLabel('VideoPlayer.PlaylistLength')
			playing = xbmc.getInfoLabel('VideoPlayer.Title')

			if any(not playing, all(paying, pll in ['0','1'])):
				self.put_playlist_alert_to_Main()


	def monitor_daemon(self):
		''' This loops until either self.active is set to false, xbmc requests an abort, or 
			the current position in the episode exceeds the trigger_point.
			It is spawned in its own thread. It sleeps for a second between loops to reduce
			system load. '''

		while self.episode_active and not xbmc.abortRequested:

			current_position = self.runtime_converter(xbmc.getInfoLabel('VideoPlayer.Time'))

			if current_position >= self.trigger_point:

				self.episode_active = False

				self.put_episode_alert_to_Main()

			xbmc.sleep(1000)


	def calculate_trigger_point(self, duration):
		''' calculates the position in the playback for the trigger '''

		try:
			duration = int(duration)
			return duration * self.trigger_postion_metric / 100
		
		except:
			return self.runtime_converter(duration) * self.trigger_postion_metric / 100


	def put_episode_alert_to_Main(self):
		''' Puts the alert of the trigger to the Main queue '''

		self.log('IMP putting episode alert to queue')
		self.queue.put({'IMP_reports_trigger':{'showid':self.showid}})


	def put_playlist_alert_to_Main(self):
		''' Puts the alert of the playlist ended to the Main queue '''

		self.log('IMP putting playlist alert to queue')
		self.queue.put({'lazy_playlist_ended':{}})


	def runtime_converter(self, time_string):
		''' converts an XBMC time string to an integer of seconds '''

		if time_string == '':
			return 0
		else:
			x = time_string.count(':')

			if x ==  0:
				return int(time_string)

			elif x == 2:
				h, m, s = time_string.split(':')
				return int(h) * 3600 + int(m) * 60 + int(s)

			elif x == 1:
				m, s = time_string.split(':')
				return int(m) * 60 + int(s)

			else:
				return 0


class LazyPlayer(xbmc.Player):

	def __init__(self, *args, **kwargs):

		xbmc.Player.__init__(self)

		self.queue = kwargs.get('queue','')
		self.log   = kwargs.get('log',  '')
		self.log('LazyPlayer instantiated')


	def onPlayBackStarted(self):
		''' checks if the show is an episode
			returns a dictionary of {allow_prev: x, showid: x, epid: x, duration: x} '''

		#check if an episode is playing
		self.ep_details = T.json_query(Q.whats_playing)

		raw_details = self.ep_details.get('item','')

		self.log(raw_details, 'raw details')

		allow_prev = True

		if raw_details:

			video_type = raw_details.get('type','')

			if video_type in ['unknown','episode']:

				showid    = int(raw_details.get('tvshowid', 'none'))
				epid      = int(raw_details.get('id', 'none'))

				if showid != 'none' and epid != 'none':

					if not raw_details.get('episode',0):

						return

					else:

						showtitle  		= raw_details.get('showtitle','')
						episode_np 		= T.fix_SE(raw_details.get('episode'))
						season_np  		= T.fix_SE(raw_details.get('season'))
						duration   		= raw_details.get('runtime','')
						resume_details  = raw_details.get('resume',{})

						# allow_prev, show_npid, ep_id = iStream_fix(show_id, showtitle, episode, season) #FUNCTION: REPLACE ISTREAM FIX

						self.queue.put({'episode_is_playing': {'allow_prev': allow_prev, 'showid': showid, 'epid': epid, 'duration': duration, 'resume': resume_details}})

			elif video_type == 'movie':
				# a movie might be playing in the random player, send the details to MAIN

				self.queue.put({'movie_is_playing': {'movieid': movieid}})


	def onPlayBackStopped(self):
		self.onPlayBackEnded()


	def onPlayBackEnded(self):

		self.queue.put({'player_has_stopped': {}})


class LazyMonitor(xbmc.Monitor):

	def __init__(self, *args, **kwargs):

		xbmc.Monitor.__init__(self)

		self.queue = kwargs.get('queue','')
		self.log   = kwargs.get('log',  '')


	def onSettingsChanged(self):
		
		self.queue.put({'update_settings': {}})


	def onDatabaseUpdated(self, database):

		if database == 'video':

			# update the entire list again, this is to ensure we have picked up any new shows.
			self.queue.put({'full_library_refresh':[]})


	def onNotification(self, sender, method, data):

		#this only works for GOTHAM

		skip = False

		try:
			self.ndata = ast.literal_eval(data)
		except:
			skip = True

		if skip == True:
			pass
			self.log(data, 'Unreadable notification')

		elif method == 'VideoLibrary.OnUpdate':
			# Method 		VideoLibrary.OnUpdate
			# data 			{"item":{"id":1,"type":"episode"},"playcount":4}

			item      = self.ndata.get('item', False)
			playcount = self.ndata.get('playcount', False)
			itemtype  = item.get('type',False)
			epid      = item.get('id',  False)

			if all([item, itemtype == 'episode', playcount == 1]):

				return {'manual_watched_change': epid}


class LazyComms(threading.Thread):
	''' Waits for connections from the GUI, 
		adds the requests to the queue '''

	def __init__(self, to_Parent_queue, from_Parent_queue, log):

		# not sure I need this, but oh well
		self.wait_evt = threading.Event()

		# queues to handles passing items to and recieving from the service
		self.to_Parent_queue = to_Parent_queue
		self.from_Parent_queue = from_Parent_queue

		# old yeller
		self.log = log

		threading.Thread.__init__(self)

		self.daemon = True

		# create the listening socket, it creates new connections when connected to
		self.address = ('localhost', 16458)
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

		# allows the address to be reused (helpful with testing)
		self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self.sock.bind(self.address)
		self.sock.listen(1)
		
		self.stopped = False


	def stop(self):
		''' Orderly shutdown of the socket, sends message to run loop
			to exit. '''

		try:

			self.log('LazyComms stopping')

			self.stopped = True
				
			sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			sock.connect(self.address)
			sock.send('exit')
			sock.close()
			self.sock.close()
				
			self.log('LazyComms stopped')

		except Exception, e:

			self.log('LazyComms error trying to stop: {}'.format(e))


	def run(self):

		self.log('LazyComms started')

		while not xbmc.abortRequested and not self.stopped:

			# wait here for a connection
			conn, addr = self.sock.accept()

			# holds the message parts
			message = []

			# turn off blocking for this temporary connection
			# this will allow the loop to collect all parts of the message
			conn.setblocking(0)

			# recv will throw a 'resource temporarily unavailable' error 
			# if there is no more data
			while True:
				
				try:
					data_part = conn.recv(8192)
				except:
					break

				# add the partial message to the holding list
				message.append(data_part)

			data = ''.join(message)

			# if the message is to stop, then kill the loop
			if data == 'exit':
				self.stopped = True
				conn.close()
				break
			
			# deserialise dict that was recieved
			deserial_data = pickle.loads(data)

			# send the data to Main for it to process
			self.to_Parent_queue.put(deserial_data)

			# wait 3 seconds for a response from Main
			try:
				response = self.from_Parent_queue.get(True, 3)

				# serialise dict for transfer back over the connection
				serial_response = pickle.dumps(response)

				# send the response back
				conn.send(serial_response)

				self.log('LazyComms sent response: ' + str(serial_response)[:50])

			except Queue.Empty:
				# if the queue is empty, then send back a response saying so
				self.log('Main took too long to respond.')
				self.conn.send('Service Timeout')

			# close the connection
			conn.close()


def iStream_fix(show_id, showtitle, episode, season):

	# streams from iStream dont provide the showid and epid for above
	# they come through as tvshowid = -1, but it has episode no and season no and show name
	# need to insert work around here to get showid from showname, and get epid from season and episode no's
	# then need to ignore self.s['prevcheck']

	redo = True
	count = 0

	while redo and count < 2: 				# this ensures the section of code only runs twice at most
		redo = False
		count += 1

		if show_id == -1 and showtitle and episode and season:

			raw_shows = T.json_query(show_request_all,True)

			if 'tvshows'in raw_shows:

				for x in raw_shows['tvshows']:

					if x['label'] == showtitle:

						show_id = x['tvshowid']
						eps_query['params']['tvshowid'] = show_id
						tmp_eps = T.json_query(eps_query,True)

						if 'episodes' in tmp_eps:

							for y in tmp_eps['episodes']:

								if fix_SE(y['season']) == season and fix_SE(y['episode']) == episode:

									ep_id = y['episodeid']

									# get odlist
									tmp_od    = ast.literal_eval(WINDOW.getProperty("%s.%s.odlist" 	% ('LazyTV', show_npid)))

									if show_npid in randos:

										tmpoff = WINDOW.getProperty("%s.%s.offlist" % ('LazyTV', show_npid))
										if tmp_off:
											tmp_od += ast.literal_eval(tmp_off)


									if ep_id not in tmp_od:

										Main.get_eps([show_npid])

										redo = True

	return False, show_npid, ep_npid		


class TVShow(object):
	''' These objects contain the tv episodes and all TV show 
		relevant information. They are stored in the LazyTV show_store '''

	def __init__(self, showID, show_type, show_title, last_played, queue, logging_setting):

		# supplied data
		self.showID = showID
		self.show_type = show_type
		self.show_title = show_title
		self.queue = queue
		self.last_played = last_played
		self.keep_logs = logging_setting

		# the eps_store contains all the episode objects for the show
		# it is a dict which follows this structure
		#   on_deck_ep : ep_object --  current on deck episode
		#   addit_ep   : [ep_object, ep_object, ...] -- additional episodes created as needed
		#   temp_ep    : ep_object -- the pre-loaded episode ready for quick changeover
		self.eps_store = {'on_deck_ep': None, 'temp_ep': None}

		# episode_list is the master list of all episodes
		# in their appropriate order, the items are tuples with (ordering stat, epid, watched status)
		self.episode_list = []

		# od_episodes is an ordered list of the on_deck episode only
		self.od_episodes = []

		# stats on the number of status of shows
		# [ watched, unwatched, skipped, ondeck]
		self.show_watched_stats = [0,0,0,0]


	def log(self, message, label = ''):
		''' This separate logger is required so that the
			TVShow can be pickled. '''

		if self.keep_logs:

			xbmc.log(msg = 'script.LazyTV TVShow ::: {} - {} '.format(label, str(message)[:1000]) )


	def full_show_refresh(self):

		self.log(self.show_title, 'full show refresh called: ')

		# retrieve complete episode list
		self.create_new_episode_list()	

		# if no shows exist, then remove the show
		if not self.episode_list:
			self.log(self.show_title, 'no shows, removing show: ')
			self.queue.put({'remove_show': {'showid': self.showID}})
			return

		# continue refreshing
		self.partial_refresh()


	def partial_refresh(self):	
		''' Create a new od list and select a new ondeck ep '''

		self.log(self.show_title,'partial_refresh called: ')

		# reform the od_list
		self.create_od_episode_list()

		# update the stats
		self.update_stats()

		# retrieve on_deck epid
		ondeck_epid = self.find_next_ep()

		# check the current ondeck ep, return None if it is the
		# same as the new one
		curr_odep = self.eps_store.get('on_deck_ep','')
		if curr_odep:

			if ondeck_epid == curr_odep.epid:

				self.log('curr_odep == ondeck_epid')

				return

		# create episode object
		on_deck_ep = self.create_episode(epid = ondeck_epid)

		# put it in the eps_store
		self.eps_store['on_deck_ep'] = on_deck_ep

		# puts a request for an update of the smartplaylist
		self.queue.put({'update_smartplaylist': {'showid': self.showID, 'remove': False}})


	def create_new_episode_list(self):
		''' returns all the episodes for the TV show, including
			the episodeid, the season and episode numbers,
			the playcount, the resume point, and the file location '''

		self.log(self.show_title, 'create_new_episode_list called: ')

		Q.eps_query['params']['tvshowid'] = self.showID
		raw_episodes = T.json_query(Q.eps_query)

		# this produces a list of lists with the sub-list being
		# [season * 1m + episode, epid, 'w' or 'u' based on playcount]
		
		if 'episodes' in raw_episodes:
			self.episode_list = [[
					int(ep['season']) * 1000000 + int(ep['episode']),
					ep['episodeid'],
					int(ep[ 'season']),
					int(ep['episode']),
					'w' if ep['playcount'] > 0 else 'u',
					] for ep in raw_episodes.get('episodes',[])]

			# sorts the list from smallest season10k-episode to highest
			self.episode_list.sort()

		self.log(self.episode_list, 'create_new_episode_list result: ')

		return self.episode_list


	def create_od_episode_list(self):
		''' identifies the on deck episodes and returns them in a list of epids'''

		self.log(self.episode_list, 'create_od_episode_list called: ')
		self.log(self.show_type, 'show_type: ')

		if self.show_type == 'randos':

			self.od_episodes = [x[1] for x in self.episode_list if x[-1] == 'u']

		else:

			latest_watched = [x for x in self.episode_list if x[-1] == 'w']
			
			if latest_watched:

				self.log(latest_watched, 'latest_watched: ')
				latest_watched = latest_watched[-1]
				position = self.episode_list.index(latest_watched)+1
			
			else:
				position = 0

			self.od_episodes = [x[1] for x in self.episode_list[position:]]

		self.log(self.od_episodes, 'create_od_episode_list result: ')
		
		return self.od_episodes


	def update_watched_status(self, epid, watched):
		''' updates the watched status of episodes in the episode_list '''

		self.log('update_watched_status called: epid: {}, watched: {}'.format(epid,watched))

		# cycle through all episodes, but stop when the epid is found
		for i, v in enumerate(self.episode_list):
			if v[1] == epid:

				#save the previous state
				previous = self.episode_list[i][-1]

				# change the watched status
				self.episode_list[i][-1] = 'w' if watched else 'u'

				# if the state has change then queue the show for a full refresh of episodes
				if self.episode_list[i][-1] != previous:

					self.queue.put({'refresh_single_show': self.showID})

				return


	def update_stats(self):
		''' updates the show-episode watched stats '''

		od_pointer = self.eps_store.get('on_deck_ep', False)

		if not od_pointer:
			od_pointer = 1
		else:
			if epid not in self.episode_list:
				od_pointer = 1
			else:
				od_pointer = self.episode_list.index(epid)

		watched_eps   = len([x for x in self.episode_list if x[-1] == 'w'])
		unwatched_eps = len([x for x in self.episode_list if x[-1] == 'u'])
		skipped_eps   = len([x for x in self.episode_list[:od_pointer] if x[-1] == 'w'])
		ondeck_eps    = len([x for x in self.episode_list[od_pointer-1:]])

		self.show_watched_stats = [watched_eps, unwatched_eps, skipped_eps, ondeck_eps]

		self.log(self.show_watched_stats, 'update_stats called: ')

		return self.show_watched_stats


	def gimme_ep(self, epid_list = False):
		''' Returns an episode object, this simply returns the on_deck episode in the 
			normal case. If a list of epids is provided then this indicates that the random
			player is requesting an additional show. Just send them the next epid. '''

		self.log(epid_list, 'gimme_ep called: ')

		if not epid_list:

			return self.eps_store.get('on_deck_ep', None)

		else:

			return self.find_next_ep(epid_list)


	def tee_up_ep(self, epid):
		''' Identifies what the next on_deck episode should be.
			Then it checks whether that new on_deck ep is is already loaded into
			self.eps_store['temp_ep'], and if it isnt, it creates the new episode
			object and adds it to the store. 
			'''

		self.log(epid, 'tee_up_ep called: ')

		# turn the epid into a list
		epid_list = [epid]

		# find the next epid
		next_epid = self.find_next_ep(epid_list)

		# if there is no next_ep then return None
		if not next_epid:
			self.log('no next ep')
			return

		self.log(next_epid, 'next_epid: ')

		# if temp_ep is already loaded then return None
		if next_epid == self.eps_store.get('temp_ep', ''):

			self.log('next_epid same as temp_ep')

			return
		
		# create the episode object
		temp_ep = self.create_episode(epid = next_epid)

		# store it in eps_store
		self.eps_store['temp_ep'] = temp_ep

		return True


	def find_next_ep(self, epid_list = None):
		''' finds the epid of the next episode. If the epid is None, then the od_ep is returned,
			if a list is provided and the type is randos, then remove the items from the od list,
			if a list is provided and the type is normal, then slice the list from the last epid in the list.
			'''

		self.log(epid_list, 'find_next_ep called: ')

		# get list of on deck episodes
		if not epid_list:
			od_list = self.od_episodes

		elif self.show_type == 'randos':

			# if rando then od_list is all unwatched episodes
			od_list = [x for x in self.od_episodes if x not in epid_list]

		else:

			# find the common items in the supplied epid list and the current odep list
			overlap = [i for i in epid_list if i in self.od_episodes]

			if not overlap:

				# if the epids arent in the od_list
				od_list = self.od_episodes

			else:

				# if normal, then od_list is everything after the maximum position
				# of epids in the supplied list
				max_position = max([self.od_episodes.index(epid) for epid in overlap])

				od_list = self.od_episodes[max_position + 1:]


		# if there are no episodes left, then empty the eps_store and return none
		if not od_list:

			self.log('od_list empty')

			self.eps_store['temp_ep'] = ''

			# puts a request for an update of the smartplaylist to remove the show
			self.queue.put({'update_smartplaylist': {'showid': self.showID, 'remove': True}})

			return

		# if the show type is rando, then shuffle the list
		if self.show_type == 'randos':

			od_list = random.shuffle(od_list)

		# return the first item in the od list
		self.log(od_list, 'find_next_ep result: ')
		return od_list[0]


	def look_for_prev_unwatched(self, epid = False):
		''' Checks for the existence of an unwatched episode prior to the provided epid.
			Returns a tuple of showtitle, season, episode '''


		if not self.show_type == 'randos':

			self.log(epid, 'look_for_prev_unwatched reached: ')

			# if the epid is not in the list, then return None
			if epid not in [x[1] for x in self.episode_list]:

				self.log('epid is not in the list')

				return

			# on deck episode
			odep = self.eps_store.get('on_deck_ep',False)

			self.log(odep, 'on deck episode: ')

			# if there is no ondeck episode then return
			if not odep:
				self.log('no ondeck episode')
				return

			# if the epid is the on_deck_ep then return
			if odep.epid == epid:
				self.log('epid is the on_deck_ep')
				return				

			# if epid is in od_episodes then return details
			if epid in self.od_episodes:
				self.log('epid is in od_episodes')
				return odep.epid, self.show_title, T.fix_SE(odep.Season), T.fix_SE(odep.Episode)


	def swap_over_ep(self):
		''' Swaps the temp_ep over to the on_deck_ep position in the eps_store. The temp_ep
			remains in place so the "notify of next available" function can refer to it '''

		self.log('swap_over_ep called')

		self.eps_store['on_deck_ep'] = self.eps_store['temp_ep']


	def create_episode(self, epid):
		''' creates a new episode class '''

		self.log(epid, 'create_episode called: ')

		# new_ep = LazyEpisode(label = '')

		# new_ep.populate(epid, self.showID, self.last_played, self.show_title, self.show_watched_stats)

		new_ep = xbmcgui.ListItem(label='random')
		return new_ep


class PickalableSWIG(object):

	def __setstate__(self, state):
		self.__init__(*state['args'])

	def __getstate__(self):
		return {'args': self.args}

class LazyEpisode(xbmcgui.ListItem):
# the plan was to create the listitem here, but it cant be pickled
# class LazyEpisode(xbmcgui.ListItem, PickalableSWIG):


	# def __init__(self, *args):
	# 	self.args = args
	# 	xbmcgui.ListItem.__init__(self)

	def __init__(self):
		pass

	def populate(self, epid, showid, lastplayed, show_title, stats):

		self.epid = epid
		self.showid = showid
		self.lastplayed = lastplayed
		self.show_title = show_title
		self.stats = stats

		self.retrieve_details()
		# self.set_properties()
		# self.set_art()
		# self.set_info()
		# self.set_others()


	def retrieve_details(self):

		Q.ep_details_query['params']['episodeid'] = self.epid

		raw_ep_details = T.json_query(Q.ep_details_query)

		ep_details = raw_ep_details.get('episodedetails', False)

		if not ep_details:
			return

		if ep_details.get('resume',{}).get('position',0) and ep_details.get('resume',{}).get('total', 0):
			resume = "true"
			played = '%s%%'%int((float(ep_details['resume']['position']) / float(ep_details['resume']['total'])) * 100)
		else:
			resume = "false"
			played = '0%'

		season  = "%.2d" % float(ep_details.get('season', 0))
		episode = "%.2d" % float(ep_details.get('episode',0))

		self.Episode 				= episode
		self.Season 				= season
		self.EpisodeNo 				= "s%se%s" % (season,episode)
		self.Resume 				= resume
		self.PercentPlayed 			= played
		self.Rating 				= str(round(float(ep_details.get('rating',0)),1))
		self.Plot 					= ep_details.get('plot','')
		self.EpisodeID 				= self.epid
		self.Title 					= ep_details.get('title','')
		self.TVshowTitle 			= ep_details.get('showtitle','')
		self.OrderShowTitle			= T.order_name(self.TVshowTitle)
		self.File 					= ep_details.get('file','')
		self.fanart 				= ep_details.get('art',{}).get('tvshow.fanart','')
		self.thumb 					= ep_details.get('art',{}).get('thumb','')
		self.poster 				= ep_details.get('art',{}).get('tvshow.poster','')
		self.banner 				= ep_details.get('art',{}).get('tvshow.banner','')
		self.clearlogo 				= ep_details.get('art',{}).get('tvshow.clearlogo','')
		self.clearart				= ep_details.get('art',{}).get('tvshow.clearart','')
		self.landscape 				= ep_details.get('art',{}).get('tvshow.landscape','')
		self.characterart			= ep_details.get('art',{}).get('tvshow.characterart','')
		self.Runtime 				= int((ep_details.get('runtime', 0) / 60) + 0.5)
		self.Premiered 				= ep_details.get('firstaired','')


	def set_others(self):
		''' Sets labels and path for listitem '''

		# self.setIconImage('string_location_of_file')
		# self.setThumbnailImage('string_location_of_file')
		self.setPath(self.File)
		self.setLabel(self.TVshowTitle)
		self.setLabel2(self.Title)


	def set_properties(self):
		'''  Sets ad hoc properties for listitem '''

		self.setProperty("Fanart_Image", self.fanart)
		self.setProperty("Backup_Image", self.thumb)
		self.setProperty("numwatched", str(self.stats[0]))
		self.setProperty("numondeck", str(self.stats[3]))
		self.setProperty("numskipped", str(self.stats[2]))
		self.setProperty("lastwatched", str(self.lastplayed))
		self.setProperty("percentplayed", self.PercentPlayed)
		self.setProperty("watched",'false')
		self.setProperty("showid", str(self.showid))


	def set_misc(self):
		''' Sets miscellaneous items for listitem '''

		self.setMimeType('string')
		self.addStreamInfo({'video', 
					  {'codec' : 'string',
					   'aspect' : 'float',
					   'width' : 'integer',
					   'height' : 'integer',
					   'duration' : 'integer'}})
		self.addStreamInfo({'audio',
					  {'codec' : 'string',
					   'language' : 'string',
					   'channels' : 'integer'}})
		self.addStreamInfo({'subtitle', {'language' : 'string'}})

		
	def set_art(self):
		''' Sets the art for the listitem '''

		self.setArt({'banner': self.banner,
				'clearart': self.clearart,
				'clearlogo': self.clearlogo,
				'fanart': self.fanart,
				'landscape': self.landscape,
				'poster': self.poster,
				'thumb': self.thumb })


	def set_info(self):
		''' Sets the built-in info for a video listitem '''

		infos = {'aired': 'string',
				   # 'artist': 'list',
				   # 'cast': 'list',
				   # 'castandrole': 'list',
				   # 'code': 'string',
				   # 'credits': 'string',
				   'dateadded': 'string',
				   # 'director': 'string',
				   'duration': 'string',
				   'episode': self.Episode,
				   'genre': 'string',
				   # 'lastplayed': 'string',
				   # 'mpaa': 'string',
				   # 'originaltitle': 'string',
				   # 'overlay': 'integer',
				   'playcount': 0,
				   'plot': self.Plot,
				   # 'plotoutline': 'string',
				   'premiered': 'string',
				   'rating': float(self.Rating),
				   'season': self.Season ,
				   'sorttitle': self.OrderShowTitle,
				   # 'status': 'string',
				   # 'studio': 'string',
				   # 'tagline': 'string',
				   'title': self.Title,
				   # 'top250': 'integer',
				   # 'tracknumber': 'integer',
				   # 'trailer': 'string',
				   'tvshowtitle': self.TVshowTitle
				   # 'votes': 'string',
				   # 'writer': 'string',
				   # 'year': 'integer'
				   }

		self.setInfo('video', infos)




class PicklableListItem(xbmcgui.ListItem, PickalableSWIG):

	def __init__(self, *args):
		self.args = args
		xbmcgui.ListItem.__init__(self)


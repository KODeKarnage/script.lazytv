# XBMC Modules
import xbmc
import xbmcaddon

# Standard Modules
import time
import ast
import threading
import multiprocessing.connection
import os
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

			xbmc.log(msg = '{} service : {} :: {} ::: {} - {} '.format(self.addonid, total_gap, gap_time, label, message) )

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
			'trigger_postion_metric'
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

		elif setting_id == 'randos':
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

		# the current activity status of the IMP
		self.active = False


	def begin_monitoring(self, showid, duration):
		''' Starts monitoring the episode that is playing to check whether
			it is past a specific position in its playback. '''

		self.log('IMP monitor starting: showid= {}, duration = {}'.format(showid, duration))

		self.trigger_point = self.calculate_trigger_point(duration)

		self.log(self.trigger_point, 'trigger_point = ')

		self.showid = showid

		self.active = True
		
		little_imp = threading.Thread(target = self.monitor_daemon)

		little_imp.start()


	def monitor_daemon(self):
		''' This loops until either self.active is set to false, xbmc requests an abort, or 
			the current position in the episode exceeds the trigger_point.
			It is spawned in its own thread. It sleeps for a second between loops to reduce
			system load. '''

		while self.active and not xbmc.abortRequested:

			current_position = self.runtime_converter(xbmc.getInfoLabel('VideoPlayer.Time'))

			if current_position >= self.trigger_point:

				self.active = False

				self.put_alert_to_Main()

			xbmc.sleep(1000)


	def calculate_trigger_point(self, duration):
		''' calculates the position in the playback for the trigger '''

		try:
			duration = int(duration)
			return duration * self.trigger_postion_metric / 100
		
		except:
			return self.runtime_converter(duration) * self.trigger_postion_metric / 100


	def put_alert_to_Main(self):
		''' Puts the alert of the trigger to the Main queue '''

		self.log('IMP putting alert to queue')
		self.queue.put({'IMP_reports_trigger':{'showid':self.showid}})


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

						showtitle  = raw_details.get('showtitle','')
						episode_np = T.fix_SE(raw_details.get('episode'))
						season_np  = T.fix_SE(raw_details.get('season'))
						duration   = raw_details.get('runtime','')

						# allow_prev, show_npid, ep_id = iStream_fix(show_id, showtitle, episode, season) #FUNCTION: REPLACE ISTREAM FIX

						self.queue.put({'episode_is_playing': {'allow_prev': allow_prev, 'showid': showid, 'epid': epid, 'duration': duration}})


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


class LazyEars(object):
	''' Waits for connections from the GUI, adds the requests to the queue '''

	def __init__(self, queue):

		self.address = ('localhost', 6714)

		self.queue = queue

		self.listener = multiprocessing.connection.Listener(address, authkey='secret password')

		self.listenup()

	def listenup(self):

		while not xbmc.abortRequested:

			conn = self.listener.accept()

			# connection received
			
			msg = conn.recv()

			self.queue.put(msg)

			conn.close()


class LazyTongue(object):
	''' Sends data to the GUI '''

	def __init__(self, queue):

		self.address = ('localhost', 6714)

		self.queue = queue

		self.conn = multiprocessing.connection.Client(address, authkey='secret password')


	def speakup(self, msg):

		self.conn.send(msg)

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

	def __init__(self, showID, show_type, show_title, last_played, queue ):

		# supplied data
		self.showID = showID
		self.show_type = show_type
		self.show_title = show_title
		self.queue = queue
		self.last_played = last_played

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


	def full_show_refresh(self):

		# retrieve complete episode list
		self.create_new_episode_list()	

		# if no shows exist, then remove the show
		if not self.episode_list:
			self.queue.put({'remove_show': {'showid': self.showID}})
			return

		# continue refreshing
		self.partial_refresh()


	def partial_refresh(self):	
		''' Create a new od list and select a new ondeck ep '''

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

		return self.episode_list


	def create_od_episode_list(self):
		''' identifies the on deck episodes and returns them in a list of epids'''

		if self.show_type == 'randos':

			self.od_episodes = [x[1] for x in self.episode_list if x[-1] == 'u']

		else:

			latest_watched = [x for x in self.episode_list if x[-1] == 'w']
			
			if latest_watched:
				latest_watched = latest_watched[-1]
				position = self.episode_list.index(latest_watched)+1
			
			else:
				position = 0

			self.od_episodes = [x[1] for x in self.episode_list[position:]]

		return self.od_episodes


	def update_watched_status(self, epid, watched):
		''' updates the watched status of episodes in the episode_list '''

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

		return self.show_watched_stats


	def gimme_ep(self, epid_list = False):
		''' Returns an episode object, this simply returns the on_deck episode in the 
			normal case. If a list of epids is provided then this indicates that the random
			player is requesting an additional show. Just send them the next epid. '''

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

		# turn the epid into a list
		epid_list = [epid]

		# find the next epid
		next_epid = self.find_next_ep(epid_list)

		# if temp_ep is already loaded then return None
		if next_epid == self.eps_store.get('temp_ep', ''):

			return
		
		# create the episode object
		temp_ep = self.create_episode(epid = next_epid)

		# store it in eps_store
		self.eps_store['temp_ep'] = temp_ep


	def find_next_ep(self, epid_list = None):
		''' finds the epid of the next episode. If the epid is None, then the od_ep is returned,
			if a list is provided and the type is randos, then remove the items from the od list,
			if a list is provided and the type is normal, then slice the list from the last epid in the list.
			'''

		# get list of on deck episodes
		if not epid_list:
			od_list = self.od_episodes

		elif self.show_type == 'randos':

			od_list = [x for x in self.od_episodes if x not in epid_list]

		else:

			od_list = self.od_episodes[self.od_episodes.index(epid_list[-1]) + 1:]


		# if there are no episodes left, then empty the eps_store and return none
		if not od_list:

			self.eps_store['temp_ep'] = ''

			# puts a request for an update of the smartplaylist to remove the show
			self.queue.put({'update_smartplaylist': {'showid': self.showID, 'remove': True}})

			return

		# if the show type is rando, then shuffle the list
		if self.show_type == 'randos':

			od_list = random.shuffle(od_list)

		# return the first item in the od list
		return od_list[0]


	def look_for_prev_unwatched(self, epid = False):
		''' Checks for the existence of an unwatched episode prior to the provided epid.
			Returns a tuple of showtitle, season, episode '''

		if not self.show_store[showID].show_type == 'randos':

			# if the epid is not in the list, then return None
			if epid not in [x[1] for x in self.episode_list]:

				return

			# on deck episode
			odep = self.eps_store.get('on_deck_ep',False)

			# if there is no ondeck episode then return
			if not odep:
				return

			# if the epid is the on_deck_ep then return
			if odep.epid == epid:
				return				

			# if epid is in od_episodes then return details
			if epid in self.od_episodes:
				return odep.epid, self.show_title, T.fix_SE(odep.Season), T.fix_SE(odep.Episode)


	def swap_over_ep(self):
		''' Swaps the temp_ep over to the on_deck_ep position in the eps_store. The temp_ep
			remains in place so the "notify of next available" function can refer to it '''

		self.eps_store['on_deck_ep'] = self.eps_store['temp_ep']


	def create_episode(self, epid):
		''' creates a new episode class '''

		new_ep = LazyEpisode(epid, showid = self.showID, lastplayed = self.last_played, show_title = self.show_title, stats = self.show_watched_stats)

		return new_ep


class LazyEpisode(object):


	def __init__(self, epid, showid, lastplayed, show_title, stats):

		self.epid = epid
		self.showid = showid 
		self.lastplayed = lastplayed
		self.show_title = show_title
		self.stats = stats

		self.retrieve_details()


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

		season  = "%.2d" % float(ep_details.get('episode',0))
		episode = "%.2d" % float(ep_details.get('season'))

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



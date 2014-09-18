# XBMC Modules
import xbmc
import xbmcaddon

# Standard Modules
import time
import ast
import threading
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

	def lang(self, id):

		return self.addon.getLocalizedString(id).encode( 'utf-8', 'ignore' )


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
		    where there is no change, the full settings would be sent '''

		new_settings_dict = construct_settings_dict()

		delta_dict = {}

		for k, v in new_settings_dict.interitems():
			if v != current_dict.get(k,''):
				delta_dict[k] = v

		return delta_dict


	def construct_settings_dict(self):
		''' creates the settings dictionary '''

		s = {k: self.clean(k) for k in setting_strings}

		return s


class postion_tracking_IMP(object):
	''' The IMP will monitor the episode that is playing
		and put an Alert to Main when it passes a certain point in its playback. '''

	def __init__(self, trigger_postion_metric, queue):

		# the trigger_postion_metric is the metric that is used to determine the 
		# position in playback when the notification should be Put to Main
		self.trigger_postion_metric = trigger_postion_metric


		# self.queue is the Queue used to communicate with Main
		self.queue = queue

		# the current activity status of the IMP
		self.active = False


	def begin_monitoring(self):
		''' Starts monitoring the episode that is playing to check whether
			it is past a specific position in its playback. '''

		trigger_point = self.calculate_trigger_point(duration)

		self.active = True
		
		little_imp = threading.Thread(target=monitor_daemon)

		little_imp.start()


	def monitor_daemon(self):
		''' This loops until either self.active is set to false, xbmc requests an abort, or 
			the current position in the episode exceeds the trigger_point.
			It is spawned in its own thread. It sleeps for a second between loops to reduce
			system load. '''

		while self.active and not xbmc.abortRequested:

			current_position = self.runtime_converter(xbmc.getInfoLabel('VideoPlayer.Time'))

			if current_position >= trigger_point:

				self.active = False

				self.put_alert_to_Main()

			xbmc.sleep(1000)


	def calculate_trigger_point(self):
		''' calculates the position in the playback for the trigger '''

		return self.runtime_converter(xbmc.getInfoLabel('VideoPlayer.Duration')) * self.trigger_postion_metric / 100


	def put_alert_to_Main(self):
		''' Puts the alert of the trigger to the Main queue '''

		self.queue.put('IMP_reports_trigger')


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

	def __init__(self, queue):

		xbmc.Player.__init__(self)

		self.queue = queue

	def onPlayBackStarted(self):
		''' checks if the show is an episode
			returns a dictionary of {allow_prev: x, showid: x, epid: x} '''

		#check if an episode is playing
		self.ep_details = T.json_query(Q.whats_playing, True)

		raw_details = self.ep_details.get('item','')

		allow_prev = True

		if raw_details:

			video_type = raw_details.get('type','')

			if video_type in ['unknown','episode']:

				showid    = int(raw_details.get('tvshowid', 'none'))
				epid      = int(raw_details.get('id', 'none'))

				if showid != 'none' and epid == 'none':

					if not raw_details.get('episode',0):

						return

					else:

						showtitle  = raw_details.get('showtitle','')
						episode_np = T.fix_SE(raw_details.get('episode'))
						season_np  = T.fix_SE(raw_details.get('season'))

						allow_prev, show_npid, ep_id = iStream_fix(show_id, showtitle, episode, season) FUNCTION: REPLACE ISTREAM FIX

				self.queue.put({'episode_is_playing': {'allow_prev': allow_prev, 'showid': showid, 'epid': epid}})


	def onPlayBackStopped(self):
		self.onPlayBackEnded()

	def onPlayBackEnded(self):

		self.queue.put({'player_has_stopped': []})


class LazyMonitor(xbmc.Monitor):

	def __init__(self, queue):

		xbmc.Monitor.__init__(self)

		self.queue = queue


	def onSettingsChanged(self):
		
		self.queue.put({'update_settings': []})


	def onDatabaseUpdated(self, database):

		if database == 'video':

			# update the entire list again, this is to ensure we have picked up any new shows.
			self.queue.put({'establish_shows':[]})


	def onNotification(self, sender, method, data):

		#this only works for GOTHAM

		skip = False

		try:
			self.ndata = ast.literal_eval(data)
		except:
			skip = True

		if skip == True:
			log('Unreadable notification')

		elif method == 'VideoLibrary.OnUpdate':
			# Method 		VideoLibrary.OnUpdate
			# data 			{"item":{"id":1,"type":"episode"},"playcount":4}

			item      = self.ndata.get('item', False)
			playcount = self.ndata.get('playcount', False)
			itemtype  = item.get('type',False)

			if all([item, itemtype == 'episode', playcount == 1]):

				return {'manual_watched_change': epid}


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

			raw_shows = json_query(show_request_all,True)

			if 'tvshows'in raw_shows:

				for x in raw_shows['tvshows']:

					if x['label'] == showtitle:

						show_id = x['tvshowid']
						eps_query['params']['tvshowid'] = show_id
						tmp_eps = json_query(eps_query,True)

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






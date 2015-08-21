import threading
import time
import xbmc


class LazyTrackingImp(object):
	''' The IMP will monitor the episode that is playing
		and put an Alert to Main when it passes a certain point in its playback. '''

	def __init__(self, settings, queue, log):

		self.s = settings

		# the trigger_postion_metric is the metric that is used to determine the 
		# position in playback when the notification should be Put to Main
		self.trigger_postion_metric = self.s['trigger_postion_metric']
		self.nextup_point			= self.s['nextup_timing']

		self.duration = 0

		# the trigger point recalculated for each new show
		self.trigger_point = False

		# logging function
		self.log = log
		self.log('IMP instantiated')
		self.log(trigger_postion_metric, 'trigger_postion_metric = ')

		# stores the showid of the show being monitored
		self.triggered_showid = None
		self.running_showid = None

		# self.queue is the Queue used to communicate with Main
		self.queue = queue

		# the current activity status of the episode tracking responsibility
		self.episode_active_trigger = False
		self.episode_active_nextup  = False
		self.abort_tracking 		= True

		# the current activity status of the playlist tracking responsibility
		self.lazy_playlist_active = False

		# flag to abandon playlist_monitoring_daemon
		self.abandon_playlist_daemon = False


	def begin_monitoring_episode(self, showid, duration):
		''' Starts monitoring the episode that is playing to check whether
			it is past a specific position in its playback. '''

		self.log('IMP monitor starting: showid= {}, duration = {}'.format(showid, duration))

		self.duration = int(duration)

		self.trigger_point = self.calculate_trigger_point(self.duration)

		self.log(self.trigger_point, 'trigger_point = ')

		self.triggered_showid = None
		self.running_showid = showid

		self.episode_active_trigger = True
		self.episode_active_trigger = True
		self.abort_tracking 		= False
		
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

			if any([not playing, all([playing, pll in ['0','1']])]):
				self.put_playlist_alert_to_Main()


	def monitor_daemon(self):
		''' This loops until either self.active is set to false, xbmc requests an abort, or 
			the current position in the episode exceeds the trigger_point.
			It is spawned in its own thread. It sleeps for a second between loops to reduce
			system load. '''

		# wait for trigger point to be surpassed
		while self.episode_active_trigger and not self.abort_tracking:

			if xbmc.abortRequested:
				self.episode_active_nextup = False
				break

			current_position = self.runtime_converter(xbmc.getInfoLabel('VideoPlayer.Time'))

			if current_position >= self.trigger_point:

				self.episode_active_trigger = False

				self.put_trigger_alert_to_Main()
				break

			xbmc.sleep(1000)

		while self.episode_active_nextup and not xbmc.abortRequested and not self.abort_tracking:

			current_position = self.runtime_converter(xbmc.getInfoLabel('VideoPlayer.Time'))

			if current_position >= (self.duration - self.nextup_point - 1):

				self.episode_active_nextup False

				self.put_nextup_alert_to_Main()

			xbmc.sleep(1000)


	def stop_tracking(self):

		self.abort_tracking = True


	def calculate_trigger_point(self, duration):
		''' calculates the position in the playback for the trigger '''

		try:
			return duration * self.trigger_postion_metric / 100
		
		except:
			return self.runtime_converter(duration) * self.trigger_postion_metric / 100


	def put_trigger_alert_to_Main(self):
		''' Puts the alert of the trigger to the Main queue '''

		self.log('IMP putting episode trigger alert to queue')
		self.triggered_showid = self.running_showid
		self.queue.put({'IMP_reports_trigger':{'showid':self.triggered_showid}})


	def put_nextup_alert_to_Main(self):
		''' Puts the alert of the trigger to the Main queue '''

		self.log('IMP putting episode nextup alert to queue')
		self.queue.put({'IMP_reports_nextup':{'showid':self.running_showid}})


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


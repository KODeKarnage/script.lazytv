import lazy_queries		as Q
import lazy_tools 		as T
import xbmc


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
						# duration   		= raw_details.get('runtime','')
						duration 		= T.runtime_converter(xbmc.getInfoLabel('Player.Duration'))
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


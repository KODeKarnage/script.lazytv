import lazy_queries		as Q
import lazy_tools 		as T
import xbmc


class LazyPlayer(xbmc.Player):

	def __init__(self, *args, **kwargs):

		xbmc.Player.__init__(self)

		self.queue = kwargs.get('queue','')
		self.log   = kwargs.get('log',  '')

		self.playing_episodes_showid = None
		self.playing_episodes_epid   = None

		self.log('LazyPlayer instantiated')


	def onPlayBackStarted(self):
		''' Checks if the show is an episode.
			Returns a dictionary of {allow_prev: x, showid: x, epid: x, duration: x} '''

		#check if an episode is playing
		self.ep_details = T.json_query(Q.whats_playing)

		raw_details = self.ep_details.get('item','')

		self.log(raw_details, 'raw details')

		allow_prev = True

		if raw_details:

			video_type = raw_details.get('type','')

			if video_type in ['unknown','episode']:

				showid    = raw_details.get('tvshowid', 'none')
				epid      = raw_details.get('id', 'none')

				try:
					showid = int(showid)
					epid   = int(epid)
				except:

					return # Either epid or showid is none

				if 'episode' not in raw_details:

					return # There is no episode number

				else:

					episode_np 		= T.fix_SE(raw_details.get('episode'), None)
					season_np  		= T.fix_SE(raw_details.get('season'),  None)

					if episode_np is None or season_np is None: 

						return # vital information is missing, exiting here

					showtitle  		= raw_details.get('showtitle','')
					# duration   	= raw_details.get('runtime','')
					duration 		= T.runtime_converter(xbmc.getInfoLabel('Player.Duration'))
					resume_details  = raw_details.get('resume',{})

					# allow_prev, show_npid, ep_id = iStream_fix(show_id, showtitle, episode, season) #FUNCTION: REPLACE ISTREAM FIX

					self.queue.put(	{'episode_is_playing': {
															'allow_prev': allow_prev,
															'showid'    : showid,
															'epid'      : epid,
															'duration'  : duration,
															'resume'    : resume_details
															}
									})

					# store the showid and epid locally
					self.playing_episodes_showid = showid
					self.playing_episodes_epid   = epid

			elif video_type == 'movie':
				# a movie might be playing in the random player, send the details to MAIN

				movieid = raw_details.get('movieid', None)

				if movieid is not None:

					self.queue.put({'movie_is_playing': {'movieid': movieid}})


	def onPlayBackStopped(self):

		self.onPlayBackEnded()


	def onPlayBackEnded(self):
		''' Send notification back to Main that the episode has ended. '''

		if all([self.playing_episodes_showid is not None, self.playing_episodes_epid is not None]):

			self.queue.put({'player_has_ended': 
											{
											'ended_showid': self.playing_episodes_showid,
											'ended_epid'  : self.playing_episodes_epid
											}
							})

		self.playing_episodes_showid = None
		self.playing_episodes_epid   = None

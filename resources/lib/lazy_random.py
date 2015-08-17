# KODI Modules
import xbmc
import xbmcaddon
import xbmcgui


# STANDARD mMdules
import random
from collections import defaultdict


# LAZY Modules
import lazy_queries as Q 
import lazy_tools   as T 


class LazyMovie(object):
	''' A movie object with a couple of TV show attributes to make sorting a list of movies and shows a bit easier. '''

	def __init__(self, parent, movieid):

		self.lastplayed = ''
		self.media_type = 'movie'
		self.showid 	= 'movie'
		self.episodeid  = movieid
		self.Resume 	= "false"
		self.TVshowTitle = 'movie'


class LazyRandomiser(object):
	''' Plays a randomised list of LazyTV shows, including movies where the user has specified to do so. '''


	def __init__(self, lazytv_service, episode_list, settings, log, lang):

		self.parent 			= lazytv_service
		self.episode_list 		= episode_list
		self.s 					= settings
		self.log 				= log
		self.lang 				= lang

		self.clear_playlist()
		self.construct_candidate_list()
		self.build_playlist()


	def clear_playlist(self):
		''' Clears the "now playing" playlist. '''

		T.json_query(Q.clear_playlist, False)


	def retrieve_movies(self, tvlist_length=0):
		''' Retrieves data on available movies and returns a list of movieids '''

		self.log('Retrieving Movies')

		# Construct the movie query
		movie_query = Q.get_movies

		if self.s.get('movies', False) and not self.s.get('moviesw', False):
			# restrict the movies to only UNWATCHED
			movie_query['params']['filter'] = {"field": "playcount", "operator": "is", "value": "0"}
			self.log('Retrieving only unwatched movies.')

		elif not self.s.get('movies', False) and self.s.get('moviesw', False):
			# restrict the movies to only WATCHED
			movie_query['params']['filter'] = {"field": "playcount", "operator": "is", "value": "1"}
			self.log('Retrieving only watched movies.')

		# Retrieve the movie information
		movie_data = T.json_query(movie_query, True)

		# Parse the movie data into a list of movie ids
		movie_list = [x['movieid'] for x in movie_data['movies']] if 'movies' in movie_data else []

		random.shuffle(movie_list)

		# reduce the movie_list down to an appropriate size given the user's specs
		if tvlist_length != 0.0: 

			movie_limit = min(max(int(round(tvlist_length * self.s['movieweight'],0)), 1), len(movie_list))

			self.log('Movies limited to %s' % movie_limit)

			movie_list = movie_list[:movie_limit]

		movie_list = [LazyMovie(self, x) for x in movie_list]

		return movie_list


	def construct_candidate_list(self):

		self.log('Constructing list of candidates.')

		# episode_list is a list of the LazyEpisodes provided by the service, this has been filtered according to the user's specs
		tv_list = self.episode_list if not noshow else [] # previous structure was [(lastwatched, tvshowid, episodeid), ...]

		# remove premieres if the user does not want them
		if not self.s['premieres']:
			tv_list = [x for x in tv_list if all([x.Episode == 1, x.Season == 1])]

		# retrieve list of movieids to weave into the playlist
		movie_list = self.retrieve_movies(len(tv_list)) if any([self.s.get('movies', False), self.s.get('moviesw', False)]) else []

		self.log('%s tv shows retrieved' % len(tv_list))
		self.log('%s movies retrieved' % len(movie_list))

		if not tv_list and not movie_list:
			self.log('No TV shows or movies.')
			return

		return tv_list + movie_list


	def build_playlist(self):

		self.log('Building lazyplaylist.')

		lazy_playlist = []

		candidates = self.construct_candidate_list()

		#clear the existing playlist
		self.clear_playlist()

		# dictionary to track the episodes that have been added to the playlist
		added_ep_dict = defaultdict(list)  # {showid: [epid, epid, ...], ...}

		# start the list with the lastplayed, partially watched episode
		if self.s['start_partials']:
			
			resumable_candidates = [x for x in candidates if any([x.Resume=='true', x.Resume==True])]
			
			partial_episode = sorted(resumable_candidates, key= lambda x: x.lastplayed, reverse=True)[:1]
			
			if partial_episode:
				
				candidate = partial_episode[0]

				self.add_item_to_playlist(candidate)
				
				candidates.remove(candidate)
				
				added_ep_dict[candidate.showid],append(candidate.epid)

				if self.s['multipleshows']:
					
					additional_episode = self.parent.retrieve_add_ep(candidate.showid, added_ep_dict[candidate.showid], respond_in_comms=False)
					
					if additional_episode is not None:
						candidates.append(additional_episode)

		# flag to tell the player to begin playing after the first item is added
		begin_playing = True

		count = 0
		
		while count < self.s['length'] and candidates: 		#while the list isnt filled, and all shows arent abandoned or movies added

			R = random.randint(0, len(candidates) -1 )	#get random number

			self.log('R = ' + str(R))

			# select a candidate at random
			candidate = candidates[R]

			# add the item to the playlist
			self.add_item_to_playlist(candidate)

			count += 1

			# update the added_ep_dict
			added_ep_dict[candidate.showid].append(candidate.episodeid)

			self.log('Episode added: %s, %s' % (candidate.TVshowTitle, candidate.episodeid))

			if begin_playing:
				begin_playing = False 
				self.log('Starting player with lazyplaylist')
				xbmc.Player().play(xbmc.PlayList(1))

			# remove the candidate from the list
			candidates.remove(candidate)

			# If the user does not want multiple shows, or the item is a movie, then remove it from the list and carry on
			if not self.s['multipleshows'] or candidate.media_type == 'movie':
				continue

			# If the user wants multiple episodes from the same show, then add an episode stand-in back into the candidates list
			additional_episode = self.parent.retrieve_add_ep(candidate.showid, added_ep_dict[candidate.showid], respond_in_comms=False)

			if additional_episode is not None:
				candidates.append(additional_episode)


		WINDOW.setProperty("%s.playlist_running"	% ('LazyTV'), 'true')		# notifies the service that a playlist is running
		WINDOW.setProperty("LazyTV.rando_shuffle", 'true')						# notifies the service to re-randomise the randos

		# xbmc.Player().play(xbmc.PlayList(1))
		#xbmc.executebuiltin('ActivateWindow(MyVideoPlaylist)')
		self.log('Building lazyplaylist Ended.')


	def add_item_to_playlist(self, candidate):
		''' Sends a query to Kodi to add this item to the "now playing" playlist. '''

		# add the candidate to the playlist
		item_key = candidate.media_type + 'id'
		query = Q.add_this_ep['params']['item'] = {[item_key]: int(candidate.episodeid)}
		T.json_query(query, False)

		
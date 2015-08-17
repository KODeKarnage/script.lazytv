# Standard Modules
import random

# LazyTV Modules
from   lazy_episode 	import LazyEpisode
import lazy_queries 	as Q 
import lazy_tools		as T


class LazyTVShow(object):
	''' These objects contain the tv episodes and all TV show 
		relevant information. They are stored in the LazyTV show_store. '''

	def __init__(self, showID, show_type, show_title, last_played, queue, log, window):

		# supplied data
		self.showID 		= showID
		self.show_type 		= show_type
		self.show_title 	= show_title
		self.last_played 	= last_played
		self.queue 			= queue
		self.log 			= log
		self.WINDOW 		= window

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


	def update_window_data(self, widget_order=None):
		''' Updates the Window(10000) data with the on_deck episode details.
			The format is lazytv.SHOWID.PROPERTY '''

		# grab the on_deck episode
		ode = self.eps_store.get('on_deck_ep', False)

		if not ode:
			
			# if no on_deck episode is available, then remove all data
			marker = self.showID
			
			# remove all data
			self.WINDOW.clearProperty("lazytv.%s.DBID"                 		% marker)
			self.WINDOW.clearProperty("lazytv.%s.Title"                		% marker)
			self.WINDOW.clearProperty("lazytv.%s.Episode"              		% marker)
			self.WINDOW.clearProperty("lazytv.%s.EpisodeNo"            		% marker)
			self.WINDOW.clearProperty("lazytv.%s.Season"               		% marker)
			self.WINDOW.clearProperty("lazytv.%s.Plot"                 		% marker)
			self.WINDOW.clearProperty("lazytv.%s.TVshowTitle"          		% marker)
			self.WINDOW.clearProperty("lazytv.%s.Rating"               		% marker)
			self.WINDOW.clearProperty("lazytv.%s.Runtime"              		% marker)
			self.WINDOW.clearProperty("lazytv.%s.Premiered"            		% marker)
			self.WINDOW.clearProperty("lazytv.%s.Art(thumb)"           		% marker)
			self.WINDOW.clearProperty("lazytv.%s.Art(tvshow.fanart)"   		% marker)
			self.WINDOW.clearProperty("lazytv.%s.Art(tvshow.poster)"   		% marker)
			self.WINDOW.clearProperty("lazytv.%s.Art(tvshow.banner)"   		% marker)
			self.WINDOW.clearProperty("lazytv.%s.Art(tvshow.clearlogo)" 	% marker)
			self.WINDOW.clearProperty("lazytv.%s.Art(tvshow.clearart)"  	% marker)
			self.WINDOW.clearProperty("lazytv.%s.Art(tvshow.landscape)" 	% marker)
			self.WINDOW.clearProperty("lazytv.%s.Art(tvshow.characterart)" 	% marker)
			self.WINDOW.clearProperty("lazytv.%s.Resume"               		% marker)
			self.WINDOW.clearProperty("lazytv.%s.PercentPlayed"        		% marker)
			self.WINDOW.clearProperty("lazytv.%s.File"                 		% marker)
			# self.WINDOW.clearProperty("lazytv.%s.Play"                 	% marker)
			self.WINDOW.clearProperty("lazytv.%s.lastplayed"              	% marker)
			self.WINDOW.clearProperty("lazytv.%s.Watched"              		% marker)

			return 'no_episode'

		if widget_order is None:

			# call is to update data for the showid
			marker = self.showID
			
		else:

			# call is to update data in the last_watched order list
			marker = 'widget.' + str(widget_order)

		self.WINDOW.setProperty("lazytv.%s.DBID"                		% marker, str(ode.EpisodeID))
		self.WINDOW.setProperty("lazytv.%s.Title"               		% marker, ode.Title)
		self.WINDOW.setProperty("lazytv.%s.Episode"             		% marker, str(ode.Episode))
		self.WINDOW.setProperty("lazytv.%s.EpisodeNo"           		% marker, ode.EpisodeNo)
		self.WINDOW.setProperty("lazytv.%s.Season"              		% marker, ode.Season)
		self.WINDOW.setProperty("lazytv.%s.Plot"                		% marker, ode.Plot)
		self.WINDOW.setProperty("lazytv.%s.TVshowTitle"         		% marker, ode.TVshowTitle)
		self.WINDOW.setProperty("lazytv.%s.Rating"              		% marker, ode.Rating)
		self.WINDOW.setProperty("lazytv.%s.Runtime"             		% marker, str(ode.Runtime))
		self.WINDOW.setProperty("lazytv.%s.Premiered"           		% marker, ode.Premiered)
		self.WINDOW.setProperty("lazytv.%s.Art(thumb)"          		% marker, ode.thumb)
		self.WINDOW.setProperty("lazytv.%s.Art(tvshow.fanart)"  		% marker, ode.fanart)
		self.WINDOW.setProperty("lazytv.%s.Art(tvshow.poster)"  		% marker, ode.poster)
		self.WINDOW.setProperty("lazytv.%s.Art(tvshow.banner)"  		% marker, ode.banner)
		self.WINDOW.setProperty("lazytv.%s.Art(tvshow.clearlogo)"		% marker, ode.clearlogo)
		self.WINDOW.setProperty("lazytv.%s.Art(tvshow.clearart)" 		% marker, ode.clearart)
		self.WINDOW.setProperty("lazytv.%s.Art(tvshow.landscape)"		% marker, ode.landscape)
		self.WINDOW.setProperty("lazytv.%s.Art(tvshow.characterart)"	% marker, ode.characterart)
		self.WINDOW.setProperty("lazytv.%s.Resume"              		% marker, ode.Resume)
		self.WINDOW.setProperty("lazytv.%s.PercentPlayed"       		% marker, ode.PercentPlayed)
		self.WINDOW.setProperty("lazytv.%s.File"                		% marker, ode.File)
		# self.WINDOW.setProperty("lazytv.%s.Play"                		% marker, ode.play)
		self.WINDOW.setProperty("lazytv.%s.lastplayed"             		% marker, str(ode.lastplayed))
		self.WINDOW.setProperty("lazytv.%s.Watched"             		% marker, 'false')


	def full_show_refresh(self):

		self.log('full show refresh called: %s' % self.show_title)

		# retrieve complete episode list
		self.create_new_episode_list()	

		# if no shows exist, then remove the show
		if not self.episode_list:
			self.log('no shows, removing show: %s' % self.show_title)
			self.queue.put({'remove_show': {'showid': self.showID}})
			return

		# continue refreshing
		self.partial_refresh()


	def partial_refresh(self):	
		''' Create a new od list and select a new ondeck ep '''

		self.log('partial_refresh called: %s' % self.show_title)

		# reform the od_list
		self.create_od_episode_list()

		# update the stats
		self.update_stats()

		# retrieve on_deck epid
		ondeck_epid = self.find_next_ep()

		# if there is no on_deck_epid, then replace the existing ondeck_ep with None
		if not ondeck_epid:
			self.eps_store['on_deck_ep'] = None
			self.queue.put({'update_smartplaylist': self.showID})
			return


		# check the current ondeck ep, return None if it is the
		# same as the new one
		curr_odep = self.eps_store.get('on_deck_ep','')
		if curr_odep:

			if ondeck_epid == curr_odep.epid:

				self.log('curr_odep == ondeck_epid')

				return None

		# create episode object
		on_deck_ep = self.create_episode(epid = ondeck_epid)

		# check if 'on_deck_ep' is populated in self.eps_store, if it isnt then just add the 
		# on_deck_ep, otherwise swap the __dict__

		if not self.eps_store.get('on_deck_ep', False):

			# put it in the eps_store
			self.eps_store['on_deck_ep'] = on_deck_ep

		else:

			# swap the __dict__ of the existing and replacement eps
			self.eps_store['on_deck_ep'].__dict__ = on_deck_ep.__dict__.copy()


		# update the data stored in the Home Window
		self.update_window_data()

		# puts a request for an update of the smartplaylist
		self.queue.put({'update_smartplaylist': self.showID})


	def update_last_played(self):
		''' Updates the last_played attribute to be the current time, and does this for all stored episodes as well. '''

		self.last_played = T.day_conv()

		for k, v in self.eps_store.iteritems():
			v.lastplayed = self.last_played



	def create_new_episode_list(self):
		''' returns all the episodes for the TV show, including
			the episodeid, the season and episode numbers,
			the playcount, the resume point, and the file location '''

		self.log('create_new_episode_list called: %s' % self.show_title)

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
									ep['file'],
									'w' if ep['playcount'] > 0 else 'u',
								] for ep in raw_episodes.get('episodes',[])]

			# sorts the list from smallest season10k-episode to highest
			self.episode_list.sort()

		self.log('create_new_episode_list result: %s' % self.episode_list)

		return self.episode_list


	def create_od_episode_list(self):
		''' identifies the on deck episodes and returns them in a list of epids'''

		self.log('create_od_episode_list called: %s' % self.episode_list)
		self.log('show_type: %s' % self.show_type)

		if self.show_type == 'randos':

			self.od_episodes = [x[1] for x in self.episode_list if x[-1] == 'u']

		else:

			latest_watched = [x for x in self.episode_list if x[-1] == 'w']
			
			if latest_watched:

				self.log('latest_watched: %s' % latest_watched)
				latest_watched = latest_watched[-1]
				position = self.episode_list.index(latest_watched)+1
			
			else:
				position = 0

			self.od_episodes = [x[1] for x in self.episode_list[position:]]

		self.log('create_od_episode_list result: %s' % self.od_episodes)
		
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

		self.log('update_stats called: %s' % self.show_watched_stats)

		return self.show_watched_stats


	def gimme_ep(self, epid_list = False):
		''' Returns an episode filename, this simply returns the on_deck episode in the 
			normal case. If a list of epids is provided then this indicates that the random
			player is requesting an additional show. Just send them the next epid.
			'''

		self.log('gimme_ep called: %s' % epid_list)

		if not epid_list:
			new_ep_obj = self.eps_store.get('on_deck_ep', None)

			if not new_ep_obj:
				return

			else:
				self.log('new filename provided %s' % new_filename)

				return new_ep_obj.File

		else:
			new_ep = self.find_next_ep(epid_list)

			try:
				new_filename = new_ep[4]

				self.log('new filename provided %s' % new_filename)

				return new_filename

			except:
				return False


	def tee_up_ep(self, epid):
		''' Identifies what the next on_deck episode should be.
			Then it checks whether that new on_deck ep is is already loaded into
			self.eps_store['temp_ep'], and if it isnt, it creates the new episode
			object and adds it to the store. 
			'''

		self.log('tee_up_ep called: %s' % epid)

		# turn the epid into a list
		epid_list = [epid]

		# find the next epid
		next_epid = self.find_next_ep(epid_list)

		# if there is no next_ep then return None
		if not next_epid:
			self.log('no next ep')
			return

		self.log('next_epid: %s' % next_epid)

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

		self.log('find_next_ep called: %s' % epid_list)

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
			self.queue.put({'update_smartplaylist': self.showID})

			return

		# if the show type is rando, then shuffle the list
		if self.show_type == 'randos':

			od_list = random.shuffle(od_list)

		# return the first item in the od list
		self.log('find_next_ep result: %s' % od_list)
		return od_list[0]


	def look_for_prev_unwatched(self, epid = False):
		''' Checks for the existence of an unwatched episode prior to the provided epid.
			Returns a tuple of showtitle, season, episode '''


		if not self.show_type == 'randos':

			self.log('look_for_prev_unwatched reached: %s' % epid)

			# if the epid is not in the list, then return None
			if epid not in [x[1] for x in self.episode_list]:

				self.log('epid is not in the list')

				return

			# on deck episode
			odep = self.eps_store.get('on_deck_ep',False)

			self.log('on deck episode: %s' % odep)

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
		''' Swaps the temp_ep __dict__ over to the on_deck_ep item in the eps_store. The temp_ep
			remains in place so the "notify of next available" function can refer to it '''

		self.log('swap_over_ep called')

		self.eps_store['on_deck_ep'].__dict__.update(self.eps_store['temp_ep'].__dict__)

		# update the data stored in the Home Window
		self.update_window_data()


	def create_episode(self, epid, ep_type = 'lazyepisode'):
		''' creates a new episode class '''

		self.log('create_episode called: %s' % epid)

		new_ep = LazyEpisode()
		new_ep.update_data(epid, self.showID, self.last_played, self.show_title, self.show_type, self.show_watched_stats)

		return new_ep


# XBMC modules
import xbmc
import xbmcaddon
import xbmcgui

# Standard Library Modules


# LazyTV Modules
import lazy_queries 	as Q
import lazy_tools   	as T
from   lazy_tvshow 		import LazyTVShow


class LazyWrangler(object):
	''' Class to control the show listings and interactions. '''

	def __init__(self, show_store, parent, settings_dict, log, lang):

		self.show_store 	= show_store
		self.parent 		= parent
		self.s 				= settings_dict
		self.log 			= log
		self.lang 			= lang
		self.WINDOW 		= xbmcgui.Window(10000)

		# show_base_info holds the id, name, lastplayed of all shows in the db
		# if nothing is found in the library, the existing show info is retained
		self.show_base_info = {}

		self.full_library_refresh()


	def grab_all_shows(self):
		''' gets all the base show info in the library '''
		# returns a dictionary with {show_ID: {showtitle, last_played}}

		self.log('grab_all_shows reached')

		raw_show_ids = T.json_query(Q.all_show_ids)

		show_ids = raw_show_ids.get('tvshows', False)

		self.log(show_ids, 'show ids: ')

		for show in show_ids:

			sid = show.get('tvshowid', '')

			self.show_base_info[sid] = {
										'show_title': show.get('title', ''),
										'last_played': show.get('lastplayed', '')
										}

	def establish_shows(self):
		''' creates the show objects if it doesnt already exist,
			if it does exist, then do nothing '''

		self.log('establish_shows reached')

		items = [{'object': self, 'args': {'showID': k}} for k, v in self.show_base_info.iteritems()]

		T.func_threader(items, 'create_show', self.log, threadcount=5, join=True)


	def create_show(self, showID):
		''' Creates the show, or merely updates the lastplayed stat if the
			show object already exists '''

		if showID not in self.show_store.keys():
			# show not found in store, so create the show now

			if showID in self.s['randos']:
				show_type = 'randos'
			else:
				show_type = 'normal'

			show_title  = self.show_base_info[showID].get('show_title','')
			last_played = self.show_base_info[showID].get('last_played','')

			if last_played:
				last_played = T.day_conv(last_played)

			self.log('creating show, showID: {}, \
				show_type: {}, show_title: {}, \
				last_played: {}'.format(showID, show_type, show_title, last_played))

			# this is the part that actually creates the show
			self.show_store[showID] = LazyTVShow(showID, show_type, show_title, last_played, self.parent.lazy_queue, self.log, self.WINDOW)
		
		else:
			
			# if show found then update when lastplayed
			last_played = self.show_store[showID].get('last_played','')

			self.log(showID, 'show found, updating last played: ')

			if last_played:
				self.show_store[showID].last_played = T.day_conv(last_played)


	def full_library_refresh(self):
		''' initiates a full refresh of all shows '''

		self.log('full_library_refresh reached')

		# refresh the show list
		self.grab_all_shows()

		# Establish any shows that are missing, each show is started with a full refresh.
		# The code blocks here until all shows are built.
		self.establish_shows()

		# update widget data in Home Window
		self.parent.update_widget_data()

		# calls for the GUI to be updated (if it exists)
		self.parent.Update_GUI()


	def remove_show(self, showid, update_spl = True):
		''' the show has no episodes, so remove it from show store '''

		self.log(showid, 'remove_show called: ')

		if showid in self.show_store.keys():

			del self.show_store[showid].eps_store['on_deck_ep']
			del self.show_store[showid].eps_store['temp_ep']

			if update_spl:
				self.parent.playlist_maintainer(showid = [showid])

			del self.show_store[showid]

			self.log('remove_show show removed')

			# calls for the GUI to be updated (if it exists)
			self.parent.Update_GUI()


	def refresh_single(self, showid):
		''' refreshes the data for a single show ''' 

		self.log(showid, 'refresh_single reached: ')

		self.show_store[showid].partial_refresh()


	def manual_watched_change(self, epid):
		''' change the watched status of a single episode '''

		self.log(epid, 'manual_watched_change reached: ')

		showid = self.reverse_lookup(epid)

		if showid:
			
			self.log(showid, 'reverse lookup returned: ')

			self.show_store[showid].update_watched_status(epid, True)

			# update widget data in Home Window
			self.parent.update_widget_data()

			# Update playlist with new information
			self.parent.playlist_maintainer.update_playlist([showid])

			# calls for the GUI to be updated (if it exists)
			self.parent.Update_GUI()


	def swap_triggered(self, showid):
		''' This process is called when the IMP announces that a show has past its trigger point.
			The boolean self.swapped is changed to the showID. '''				

		self.log(showid, 'swap triggered, initiated: ')

		self.show_store[showid].swap_over_ep()
		
		# calls for the GUI to be updated (if it exists)
		self.parent.Update_GUI()
		
		# update widget data in Home Window
		self.parent.update_widget_data()

		# Update playlist with new information
		self.parent.playlist_maintainer.update_playlist([showid])

		return showid


	def rando_change(self, show, new_rando_list, current_type):
		''' Calls the partial refresh on show where the show type has changed '''	

		self.log('%s: %s: %s' % (show.showID, current_type, show.showID in new_rando_list))

		if current_type == 'randos' and show.showID not in new_rando_list:

			show.show_type = 'normal'

			show.partial_refresh()

		elif current_type != 'randos' and show.showID in new_rando_list:

			show.show_type = 'randos'

			show.partial_refresh()

		# update widget data in Home Window
		self.parent.update_widget_data()


	def retrieve_add_ep(self, showid, epid_list, respond_in_comms=True):
		''' Retrieves one more episode from the supplied show. If epid_list is provided, then the episode after the last one in the
		list is returned. If respond_in_comms is true, the place the response in the queue for external communication, otherwise
		just return the new episode id from the function. '''

		show = self.show_store[showid]

		new_episode = show.find_next_ep(epid_list)

		if respond_in_comms:

			response = {'new_epid': new_episode}

			self.parent.comm_queue.put(response)

		else:

			return new_episode


	def pass_all_epitems(self, permitted_shows = []):
		''' Gets the on deck episodes from all shows and provides them
			in a list. Restricts shows to those in the show_id list, if provided '''

		if permitted_shows == 'all':
			permitted_shows = []

		all_epitems = [show.eps_store['on_deck_ep'] for k, show in self.show_store.iteritems() if any([not permitted_shows, show.showID in permitted_shows])]

		return all_epitems

import xbmc
import json

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

		#this only works for GOTHAM and later

		skip = False

		try:
			self.ndata = json.loads(data)
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


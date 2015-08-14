import xbmcgui


class LazyListItem(xbmcgui.ListItem):
	''' A Kodi listitem that takes a LazyEpisode (glorified dictionary) and merges in the information into the listitems __dict__.
		When it is initiated, it sets all the required ListItem values automatically.'''


	def __init__(self, *args, **kwargs):
		xbmcgui.ListItem.__init__(self, *args, **kwargs)


	def merge(self, LazyEpisode):

		self.__dict__.update(LazyEpisode.__dict__)

		self.set_others()
		self.set_properties()
		# self.set_art()
		self.set_info()

		return self


	def set_others(self):
		''' Sets labels and path for listitem '''

		self.setIconImage(self.poster)
		self.setThumbnailImage(self.poster)
		self.setPath(self.File)
		self.setLabel(str(self.TVshowTitle))
		self.setLabel2(self.Title)


	def set_properties(self):
		'''  Sets ad hoc properties for listitem '''

		self.setProperty("Fanart_Image", 	self.fanart)
		self.setProperty("Backup_Image", 	self.thumb)
		self.setProperty("numwatched", 		str(self.stats[0]))
		self.setProperty("numondeck", 		str(self.stats[3]))
		self.setProperty("numskipped", 		str(self.stats[2]))
		self.setProperty("lastwatched", 	str(self.lastplayed))
		self.setProperty("percentplayed", 	self.PercentPlayed)
		self.setProperty("watched",			'false')
		self.setProperty("showid", 			str(self.showid))


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

		self.setArt({'banner': 	self.banner,
				'clearart': 	self.clearart,
				'clearlogo': 	self.clearlogo,
				'fanart': 		self.fanart,
				'landscape': 	self.landscape,
				'poster': 		self.poster,
				'thumb': 		self.thumb })


	def set_info(self):
		''' Sets the built-in info for a video listitem '''

		infos = {'aired': 			'string',
				   # 'artist': 		'list',
				   # 'cast': 		'list',
				   # 'castandrole': 'list',
				   # 'code': 		'string',
				   # 'credits': 	'string',
				   'dateadded': 	'string',
				   # 'director': 	'string',
				   'duration': 		'string',
				   'episode': 		self.Episode,
				   'genre': 		'string',
				   # 'lastplayed':  'string',
				   # 'mpaa': 		'string',
				   # 'originaltitle': 'string',
				   # 'overlay': 	'integer',
				   'playcount': 	0,
				   'plot': 			self.Plot,
				   # 'plotoutline': 'string',
				   'premiered': 	'string',
				   'rating': 		float(self.Rating),
				   'season': 		self.Season ,
				   'sorttitle': 	self.OrderShowTitle,
				   # 'status': 		'string',
				   # 'studio': 		'string',
				   # 'tagline': 	'string',
				   'title': 		self.Title,
				   # 'top250': 		'integer',
				   # 'tracknumber': 'integer',
				   # 'trailer': 	'string',
				   'tvshowtitle': 	self.TVshowTitle
				   # 'votes': 		'string',
				   # 'writer': 		'string',
				   # 'year': 		'integer'
				   }

		self.setInfo('video', infos)



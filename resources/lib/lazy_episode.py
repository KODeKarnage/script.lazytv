# LazyTV Modules
import lazy_queries as Q 
import lazy_tools	as T


class LazyEpisode(object):
	''' An episode object that is kept in the eps_store of the show.
		This class handles retrieving the episode data from the database. Its dictionary is merged into the LazyListItem, 
		which then handles specific ListItem variable population. '''


	def __init__(self):

		pass


	def update_data(self, epid, showid, lastplayed, show_title, show_type, stats):

		self.epid 		= epid
		self.showid 	= showid 
		self.lastplayed = lastplayed
		self.show_title = show_title
		self.show_type	= show_type
		self.stats 		= stats 
		
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

		season  = "%.2d" % float(ep_details.get('season', 0))
		episode = "%.2d" % float(ep_details.get('episode',0))

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
		self.OrderShowTitle			= T.order_name(self.TVshowTitle)
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


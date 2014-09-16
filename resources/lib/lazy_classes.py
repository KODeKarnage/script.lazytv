import time
import xbmc

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


	def lang(self, id):

		return self.addon.getLocalizedString(id).encode( 'utf-8', 'ignore' )




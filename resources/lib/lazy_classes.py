import time
import xbmc
import ast

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

	def logging_switch(self, switch):

		self.keep_logs = switch

	def lang(self, id):

		return self.addon.getLocalizedString(id).encode( 'utf-8', 'ignore' )


class settings_handler(object):
	''' handles the retrieval and cleaning of addon settings '''

	def __init__(self, setting_function):

		self.setting_function = setting_function

		self.firstrun = True
		self.settings_dict = {}

		self.id_substitute = {
			'playlist_notifications': 'notify',
		}

		self.setting_strings = [
			'playlist_notifications', 
			'resume_partials',
			'keep_logs',
			'nextprompt',    
			'nextprompt_or', 
			'startup',       
			'promptduration', 
			'prevcheck',      
			'promptdefaultaction',  
			'moviemid',             
			'first_run',            
			'startup',              
			'maintainsmartplaylist'
		]


	def clean(self, setting_id):
		''' retrieves and changes the setting into a usable state '''

		if setting_id in self.id_substitute.keys():
			setting_id = self.id_substitute.get(setting_id,setting_id)

		value = self.setting_function(setting_id)

		if value == 'true':
			# convert string bool into real bool
			value = True 

		elif value == 'false':
			# convert string bool into real bool
			value = False

		elif setting_id == 'promptduration':
			# change a zero prompt duration to a non-zero instant
			if value == 0:
				value = 1 / 1000.0
			else:
				value = int(float(value))

		elif setting_id == 'randos':
			# turn the randos string into a real string
			value = ast.literal_eval(value)
			
		else:
			# convert number values into integers
			try:
				value = int(float(value))
			except:
				pass

		return value


	def get_settings_dict(self, current_dict={}):
		''' provides a dictionary of all the changed settings,
		    where there is no change, the full settings would be sent '''

		new_settings_dict = construct_settings_dict()

		delta_dict = {}

		for k, v in new_settings_dict.interitems():
			if v != current_dict.get(k,''):
				delta_dict[k] = v

		return delta_dict


	def construct_settings_dict(self):
		''' creates the settings dictionary '''

		s = {k: self.clean(k) for k in setting_strings}

		return s


	



		# # create the smartplaylist if the smartplaylist is switched on
		# if not s['maintainsmartplaylist']:
		# 	s['maintainsmartplaylist']  = True if __setting__('maintainsmartplaylist') == 'true' else False
		# 	if s['maintainsmartplaylist'] and not firstrun:
		# 		for neep in Main.nepl:
		# 			Main.update_smartplaylist(neep)
		# else:
		# 	s['maintainsmartplaylist']  = True if __setting__('maintainsmartplaylist') == 'true' else False

		# # apply the user selection of rando tv shows
		# try:
		# 	randos             = ast.literal_eval(__setting__('randos'))
		# except:
		# 	randos = []

		# try:
		# 	old_randos = ast.literal_eval(WINDOW.getProperty("LazyTV.randos"))
		# except:
		# 	old_randos = []

		# if old_randos != randos and not firstrun:
		# 	for r in randos:
		# 		if r not in old_randos:
		# 			log('adding rando')
		# 			# if new rando, then add new randos to nepl and shuffle
		# 			Main.add_to_nepl(r)
		# 			Main.reshuffle_randos(sup_rand = [r])

		# 	for oar in old_randos:
		# 		if oar not in randos:
		# 			log('removing rando')
		# 			# if rando removed then check if rando has ondeck, if not then remove from nepl,
		# 			try:
		# 				has_ond = ast.literal_eval(WINDOW.getProperty("%s.%s.odlist" 	% ('LazyTV', oar)))
		# 				log('odlist = ' + str(has_ond))
		# 			except:
		# 				has_ond = False

		# 			# if so, then store the next ep
		# 			if has_ond:
		# 				log('adding ondeck ep for removed rando')
		# 				retod    = WINDOW.getProperty("%s.%s.odlist" 						% ('LazyTV', oar))
		# 				retoff   = WINDOW.getProperty("%s.%s.offlist" 					% ('LazyTV', oar))
		# 				offd     = ast.literal_eval(retoff)
		# 				ond      = ast.literal_eval(retod)
		# 				tmp_wep  = int(WINDOW.getProperty("%s.%s.CountWatchedEps"         	% ('LazyTV', oar)).replace("''",'0')) + 1
		# 				tmp_uwep = max(0, int(WINDOW.getProperty("%s.%s.CountUnwatchedEps"  % ('LazyTV', oar)).replace("''",'0')) - 1)

		# 				Main.store_next_ep(ond[0], oar, ond, offd, tmp_uwep, tmp_wep)

		# 			else:
		# 				Main.remove_from_nepl(oar)

		# # finally, set the new stored randos
		# WINDOW.setProperty("LazyTV.randos", str(randos))

		# log('randos = ' + str(randos))

		# log('settings grabbed')
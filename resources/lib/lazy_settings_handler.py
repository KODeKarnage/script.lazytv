import ast

class LazySettingsHandler(object):
	''' Handles the retrieval and cleaning of addon settings. '''

	def __init__(self, setting_function):

		self.setting_function = setting_function

		self.firstrun = True
		self.settings_dict = {}

		self.id_substitute = {
			'playlist_notifications': 'notify',
			'keep_logs'				: 'logging',
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
			'randos',           
			'first_run',            
			'startup',              
			'maintainsmartplaylist',
			'trigger_postion_metric',
			'skinorno',
			'movieweight',
			'filterYN',
			'multipleshows',
			'premieres',
			'limitshows',
			'movies',
			'moviesw',
			'noshow',
			'excl_randos',
			'sort_reverse',
			'start_partials',
			'skin_return',
			'window_length',
			'length',
			'sort_by',
			'primary_function',
			'populate_by_d',
			'select_pl',
			'users_spl',
			'selection',
			'IGNORE',

		]


	def clean(self, setting_id):
		''' retrieves and changes the setting into a usable state '''

		if setting_id in self.id_substitute.keys():
			setting_id = self.id_substitute.get(setting_id,setting_id)

		try:
			# if the setting is not found, then just return None
			value = self.setting_function(setting_id)
		except:
			return None

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

		elif setting_id in ['randos', 'selection']:
			# turn the randos string into a real string
			if value == 'none':
				value = []
			else:
				value = ast.literal_eval(value)
			
		else:
			# convert number values into integers
			try:
				value = int(float(value))
			except:
				# otherwise just use the string
				pass

		return value


	def get_settings_dict(self, current_dict={}):
		''' provides a dictionary of all the changed settings,
			where there is no current dict, the full settings would be sent '''

		new_settings_dict = self.construct_settings_dict()

		delta_dict = {}

		for k, v in new_settings_dict.iteritems():
			if v != current_dict.get(k,''):
				if v is None:
					# do not return any settings that are None
					pass
				else:
					delta_dict[k] = v

		return delta_dict


	def construct_settings_dict(self):
		''' creates the settings dictionary '''

		s = {k: self.clean(k) for k in self.setting_strings}

		return s

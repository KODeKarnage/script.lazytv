# XBMC modules
import xbmc
import xbmcaddon
import xbmcgui

# STANDARD library modules
import ast
import datetime
import json
import os
import pickle
import Queue
import re
import socket
import threading
import time

# LAZYTV modules
import lazy_queries as Q


def iStream_fix(show_id, showtitle, episode, season, WINDOW):

	# streams from iStream dont provide the showid and epid for above
	# they come through as tvshowid = -1, but it has episode no and season no and show name
	# need to insert work around here to get showid from showname, and get epid from season and episode no's
	# then need to ignore self.s['prevcheck']

	redo = True
	count = 0

	while redo and count < 2: 				# this ensures the section of code only runs twice at most
		redo = False
		count += 1

		if show_id == -1 and showtitle and episode and season:

			raw_shows = json_query(show_request_all,True)

			if 'tvshows'in raw_shows:

				for x in raw_shows['tvshows']:

					if x['label'] == showtitle:

						show_id = x['tvshowid']
						eps_query['params']['tvshowid'] = show_id
						tmp_eps = json_query(eps_query,True)

						if 'episodes' in tmp_eps:

							for y in tmp_eps['episodes']:

								if fix_SE(y['season']) == season and fix_SE(y['episode']) == episode:

									ep_id = y['episodeid']

									# get odlist
									tmp_od    = ast.literal_eval(WINDOW.getProperty("%s.%s.odlist" 	% ('LazyTV', show_npid)))

									if show_npid in randos:

										tmpoff = WINDOW.getProperty("%s.%s.offlist" % ('LazyTV', show_npid))
										if tmp_off:
											tmp_od += ast.literal_eval(tmp_off)


									if ep_id not in tmp_od:

										Main.get_eps([show_npid])

										redo = True

	return False, show_npid, ep_npid		


def current_KODI_version():
	'''get the current version of XBMC'''

	versstr = xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "Application.GetProperties", "params": {"properties": ["version", "name"]}, "id": 1 }')
	vers = ast.literal_eval(versstr)

	verdict = reduce(dict.__getitem__,['result','version'], vers)
	
	if any([int(verdict['major']) > 12, all([int(verdict['major']) == 12, int(verdict['minor']) > 8])]):
		release            = "Gotham"
	else:
		release            = "Frodo"

	return release


def json_query(query):

	xbmc_request = json.dumps(query)
	raw = xbmc.executeJSONRPC(xbmc_request)
	clean = unicode(raw, 'utf-8', errors='ignore')
	response = json.loads(clean)
	result = response.get('result', response)

	return result


def stringlist_to_reallist(string):
	# this is needed because ast.literal_eval gives me EOF errors for no obvious reason
	real_string = string.replace("[","").replace("]","").replace(" ","").split(",")
	return real_string


def runtime_converter(time_string):
	if time_string == '':
		return 0
	else:
		x = time_string.count(':')

		if x ==  0:
			return int(time_string)
		elif x == 2:
			h, m, s = time_string.split(':')
			return int(h) * 3600 + int(m) * 60 + int(s)
		elif x == 1:
			m, s = time_string.split(':')
			return int(m) * 60 + int(s)
		else:
			return 0


def fix_SE(string):
	if len(str(string)) == 1:
		return '0' + str(string)
	else:
		return str(string)


def datetime_bug_workaround():

	try:
		throwaway = datetime.datetime.strptime('20110101','%Y%m%d')
	except:
		pass


def day_conv(date_string = None):
	''' If supplied with a date_string, it converts it to a time,
		otherwise it returns the current time as a float. '''

	# there is a common bug with this call which results in an
	# ImportError: Failed to import _strptime because the import lockis held by another thread.
	# This throw away line should eliminate it. It doesnt need to be run every time, but it cant hurt.
	datetime_bug_workaround()

	if date_string is not None:
		
		# op_format = '%Y-%m-%d %H:%M:%S'

		# time.strptime is not threadsafe
		# this is a workaround, and probably not robust
		pattern = '(\d\d\d\d)-(\d\d)-(\d\d) (\d\d):(\d\d):(\d\d)'
		
		m = re.match(pattern, date_string)

		extract = (int(x) for x in m.groups())

		lw_max    = datetime.datetime(*extract)

		date_num  = time.mktime(lw_max.timetuple())

	else:
		now = datetime.datetime.now()

		date_num = time.mktime(now.timetuple())
	
	return date_num


def order_name(raw_name):
	''' changes the raw name into an orderable name,
		removes 'The' and 'A' in a bunch of different languages'''

	name = raw_name.lower()
	language = xbmc.getInfoLabel('System.Language')

	if language in ['English', 'Russian','Polish','Turkish'] or 'English' in language:
		if name.startswith('the '):
			new_name = name[4:]
		else:
			new_name = name

	elif language == 'Spanish':
		variants = ['la ','los ','las ','el ','lo ']
		for v in variants:
			if name.startswith(v):
				new_name = name[len(v):]
			else:
				new_name = name

	elif language == 'Dutch':
		variants = ['de ','het ']
		for v in variants:
			if name.startswith(v):
				new_name = name[len(v):]
			else:
				new_name = name

	elif language in ['Danish','Swedish']:
		variants = ['de ','det ','den ']
		for v in variants:
			if name.startswith(v):
				new_name = name[len(v):]
			else:
				new_name = name

	elif language in ['German', 'Afrikaans']:
		variants = ['die ','der ','den ','das ']
		for v in variants:
			if name.startswith(v):
				new_name = name[len(v):]
			else:
				new_name = name

	elif language == 'French':
		variants = ['les ','la ','le ']
		for v in variants:
			if name.startswith(v):
				new_name = name[len(v):]
			else:
				new_name = name

	else:
		new_name = name

	return new_name


def playlist_selection_window(lang):
	''' Purpose: launch Select Window populated with smart playlists '''

	raw_playlist_files = json_query(Q.plf)

	playlist_files = raw_playlist_files.get('files',False)

	if playlist_files != None:

		plist_files   = dict((x['label'],x['file']) for x in playlist_files)

		playlist_list =  plist_files.keys()

		playlist_list.sort()

		inputchoice = xbmcgui.Dialog().select(lang(32104), playlist_list)

		return plist_files[playlist_list[inputchoice]]

	else:

		return 'empty'


def thread_actuator(thread_queue, func, log):
	''' This is the target function used in the thread creation by the func_threader.
		func = {'method as a string': {'named_arguments': na, ... }}
		method = True for  '''

	log('thread created, running {}'.format(func))

	# keep running while there are items in the queue
	while True:

		try:
			# grabs the item from the queue
			# q_item = thread_queue.pop() # alternative implementation
			# the get BLOCKS and waits 1 second before throwing a Queue Empty error
			q_item = thread_queue.get(True, 1)


			# split the func into the desired method and arguments
			o = q_item.get('object',False)
			a = q_item.get('args',False)

			if o:
				# call the function on each item (instance)
				getattr(o, func)(**a)

			thread_queue.task_done()

		except Queue.Empty:

			log('Queue.Empty error')

			break


	log('thread exiting, function: {}'.format(func))


def func_threader(items, func, log, threadcount = 3, join = True):
	''' func is the string of the method name.
		items is a list of dicts: {'object': x, 'args': y}
		object can be either self or the instance of another class
		args must be a dict of named arguments '''

	log('func_threader reached')

	# create the threading_queue
	#thread_queue = collections.deque()
	thread_queue = Queue.Queue()

	# spawn some workers
	for i in range(threadcount):

		t = threading.Thread(target=thread_actuator, args=(thread_queue, func, log))
		t.start()

	# adds each item from the items list to the queue
	# thread_queue.extendleft(items)
	[thread_queue.put(item) for item in items]
	log('{} items added to queue'.format(len(items)))

	# join = True if you want to wait here until all are completed
	if join:
		thread_queue.join()

	log('func_threader complete')


def convert_previous_settings(ignore, __setting__):
	''' Legacy from the first release of LazyTV. It ensured that the 
		user-selected IGNORE list for shows to ignore is respected in
		newer versions. The last thing we want is inappropriate episodes
		showing in childrens playlist. '''

	filter_genre        = True if __setting__('filter_genre') == 'true' else False
	filter_length       = True if __setting__('filter_length') == 'true' else False
	filter_rating       = True if __setting__('filter_rating') == 'true' else False
	filter_show         = True if __setting__('filter_show') == 'true' else False

	# convert the ignore list into a dict
	jkl = {}
	all_showids = []
	for ig in ignore.split("|"):
		if ig:
			k, v = ig.split(":-:")
			if k in jkl:
				jkl[k].append(v)
			else:
				jkl[k] = [v]
	if jkl:
		# create a list of permissable TV shows
		show_data = json_query({"jsonrpc": "2.0","id": 1, "method": "VideoLibrary.GetTVShows",  "params": { "properties" : ["mpaa","genre"] }}, True)

		if 'tvshows' in show_data and show_data['tvshows']:
			show_data = show_data['tvshows']
	
			all_showids = [x['tvshowid'] for x in show_data]

			for show in show_data:

				if filter_genre and "genre" in jkl:
					for gen in jkl['genre']:
						if gen in show['genre'] and show['tvshowid'] in all_showids:
							all_showids.remove(show['tvshowid'])

				if filter_rating and "rating" in jkl:
					if show['mpaa'] in jkl['rating'] and show['tvshowid'] in all_showids:
						all_showids.remove(show['tvshowid'])

				if filter_show and "name" in jkl:

					if str(show['tvshowid']) in jkl['name'] and show['tvshowid'] in all_showids:
						all_showids.remove(show['tvshowid'])

	if all_showids:
		spec_shows = [int(x) for x in all_showids]

		# save the new list to settings
		__addon__.setSetting('selection',str(spec_shows))
		# set the filterYN to be Y
		__addon__.setSetting('filterYN','true')
		filterYN = True


	# reset IGNORE to be null
	__addon__.setSetting('IGNORE','')


def service_request(request, log):
	''' Used by the gui to request data from the service.
		Returns python objects. '''

	address = ('localhost', 16458)

	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

	sock.connect(address)

	# serialise the request before sending to Main
	serialised_request = pickle.dumps(request)
	sock.send(serialised_request)

	# list to hold the parts of the response 
	msg = []

	# loop to collect the portions of the response
	# recv will throw a 'resource temporarily unavailable' error 
	# if there is no more data
	while True:
		try:
			response = sock.recv(8192)

			# this ensures the socket is only blocked once
			sock.setblocking(0)

			if not response:
				break

		except:
			break

		# add the part of the response to the list
		msg.append(response)

	# join the parts of the message together
	complete_msg = ''.join(msg)

	# if the message isnt empty, deserialise it with json.loads
	if complete_msg:
		deserialised_response = pickle.loads(complete_msg)
	else:
		deserialised_response = complete_msg

	# close the socket
	sock.close()

	return deserialised_response	


def inst_extend(instance, new_class):
	new_name = '%s_extended_with_%s' % (instance.__class__.__name__, new_class.__name__)
	instance.__class__ = type(new_name, (instance.__class__, new_class), {} )

	print new_name


def extend(instance, cls):
	print cls
	instance.__class__.__bases__ = (cls,)


def convert_pl_to_showlist(smart_playlist_name):
	''' Extract showids from smart playlist'''

	filename = os.path.split(smart_playlist_name)[1]
	clean_path = 'special://profile/playlists/video/' + filename

	#retrieve the shows in the supplied playlist, save their ids to a list
	Q.plf['params']['directory'] = clean_path
	playlist_contents = json_query(Q.plf, True)

	playlist_items = playlist_contents.get('files', [])

	if playlist_items:

		filtered_showids = [item.get('id', False) for item in playlist_items if item.get('type', False) == 'tvshow']
		log(filtered_showids, 'showids in playlist')
		if not filtered_showids:
			
			log('no tv shows in playlist')

			return 'all'

		#returns the list of all and filtered shows and episodes
		return filtered_showids

	else:
		log('no files in playlist')
		return 'all'


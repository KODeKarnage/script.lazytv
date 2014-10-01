# XBMC modules
import xbmc
import xbmcgui
import xbmcaddon

# STANDARD library modules
import ast
import json
import time
import datetime
import threading
import Queue
import select
import socket
import os
import sys
sys.path.append(xbmc.translatePath(os.path.join(xbmcaddon.Addon().getAddonInfo('path'), 'resources','lib')))

# LAZYTV modules
import lazy_classes as C
import lazy_queries as Q
import lazy_tools   as T



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


def day_conv(date_string = False):
	''' If supplied with a date_string, it converts it to a time,
		otherwise it returns the current time as a float. '''

	if date_string:
		op_format = '%Y-%m-%d %H:%M:%S'
		print date_string
		Y, M, D, h, mn, s, ux, uy, uz = time.strptime(date_string, op_format)
		lw_max    = datetime.datetime(Y, M, D, h ,mn, s)
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

	raw_playlist_files = T.json_query(Q.plf)

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

	filter_genre         = True if __setting__('filter_genre') == 'true' else False
	filter_length         = True if __setting__('filter_length') == 'true' else False
	filter_rating         = True if __setting__('filter_rating') == 'true' else False
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
	''' Used by the gui to request data from the service '''

	address = ('localhost', 16455)
	log(address)

	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

	#sock.setblocking(0)

	sock.connect(address)
	serialised_request = json.dumps(request) + 'LazyENDQQQ'
	sock.send(serialised_request)
	msg = []
	log('message sent')

	while True:

		r, _, _ = select.select([sock], [], [])
		log('r: ' + str(r))
		if not r: break

		response = sock.recv(8192)
		log('response: ' + response)
		if not response: break
		msg.append(response)
	complete_msg = ''.join(msg)
	deserialised_response = json.loads(complete_msg)
	sock.close()

	self.log('deserialised_response: ' + str(deserialised_response))
	
	return deserialised_response	



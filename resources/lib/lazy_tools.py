import ast
import xbmc
import xbmcgui
import json
import time
import datetime
import threading
import Queue


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


setting_strings = [
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


def func_threader(items, func, log, threadcount = 5, join = True):
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



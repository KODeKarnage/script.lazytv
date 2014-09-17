import ast
import xbmc
import json
import time
import datetime


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


def day_conv(date_string):

	op_format = '%Y-%m-%d %H:%M:%S'
	Y, M, D, h, mn, s, ux, uy, uz = time.strptime(date_string, op_format)
	lw_max    = datetime.datetime(Y, M, D, h ,mn, s)
	date_num  = time.mktime(lw_max.timetuple())
	
	return date_num


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

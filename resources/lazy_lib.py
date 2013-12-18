# declare file encoding
# -*- coding: utf-8 -*-

#  Copyright (C) 2013 KodeKarnage
#
#  This Program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2, or (at your option)
#  any later version.
#
#  This Program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with XBMC; see the file COPYING.  If not, write to
#  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
#  http://www.gnu.org/copyleft/gpl.html

import json
import xbmc
import xbmcaddon
import xbmcgui
import sys
import time
import datetime

_addon_   = xbmcaddon.Addon("script.lazytv")
_setting_ = _addon_.getSetting
lang      = _addon_.getLocalizedString
dialog    = xbmcgui.Dialog()

def proc_ig(ignore_list, ignore_by):
	il = ignore_list.split("|")
	return [i.replace(ignore_by+":-:","") for i in il if ignore_by+":-:" in i]


def log(message):
	logmsg       = '%s: %s' % ('lazytv: ', message)
	xbmc.log(msg = logmsg)

def gracefail(message):
	dialog.ok("LazyTV",message)
	sys.exit()

def json_query(query, ret):
	#try:
	xbmc_request = json.dumps(query)
	result = xbmc.executeJSONRPC(xbmc_request)
	log('RES ' + str(result))
	result = unicode(result, 'utf-8', errors='ignore')
	if ret:
		return json.loads(result)['result']
	else:
		return json.loads(result)
	#except:
	#	#failure notification
	#	gracefail(lang(32200))


def player_start():
	#the play list is now complete, this next part starts playing
	play_command = {'jsonrpc': '2.0','method': 'Player.Open','params': {'item': {'playlistid':1}},'id': 1}
	json_query(play_command, False)

def dict_engine(show, add_by):
	d = {}
	d['jsonrpc'] = '2.0'
	d['method'] = 'Playlist.Add'
	d['id'] = 1
	d['params'] = {}
	d['params']['item'] = {}
	d['params']['item'][add_by] = show
	d['params']['playlistid'] = 1
	return d

	"{ 'jsonrpc' : '2.0', 'method' : 'Playlist.Add', 'id' : 1, 'params' : {'item' : {'episodeid' : %d }, 'playlistid' : 1}}" % episodeid


def fix_name(name):
	try:
		str(name).lower
		n = name
	except:
		n = name.encode("utf-8")#.encode('latin').decode('latin').encode('utf-8')
	return n

def day_calc(date_string, todate, output):
	op_format = '%Y-%m-%d %H:%M:%S'
	lw = time.strptime(date_string, op_format)
	if output == 'diff':
		lw_date = datetime.date(lw[0],lw[1],lw[2])
		day_string = str((todate - lw_date).days) + " days)"
		return day_string
	else:
		lw_max = datetime.datetime(lw[0],lw[1],lw[2],lw[3],lw[4],lw[5])
		date_num = time.mktime(lw_max.timetuple())
		return date_num

def get_settings():
	settings = {}
	settings['premieres']        =_setting_('premieres')
	settings['multiples']        =_setting_('multipleshows')
	settings['ignore_list']      =_setting_('IGNORE')
	settings['streams']          =_setting_('streams')
	settings['expartials']       =_setting_('expartials')
	settings['filter_show']      =_setting_('filter_show')
	settings['filter_genre']     =_setting_('filter_genre')
	settings['filter_length']    =_setting_('filter_length')
	settings['filter_rating']    =_setting_('filter_rating')
	settings['first_run']        =_setting_('first_run')
	settings['primary_function'] =_setting_('primary_function')
	settings['populate_by']      =_setting_('populate_by')
	settings['smart_pl']         =_setting_('default_spl')
	settings['sort_list_by']     =_setting_('sort_list_by')
	settings['debug_type']       =_setting_('debug_type')
	settings['playlist_length']  =int(float(_setting_('length')))
	settings['debug']            =True if _setting_('debug')=="true" else False
	settings['notify']           =_setting_('notify')
	settings['resume_partials']  =_setting_('resume_partials')

	IGNORE_SHOWS   = proc_ig(settings['ignore_list'],'name') if settings['filter_show'] == 'true' else []
	IGNORE_GENRE   = proc_ig(settings['ignore_list'],'genre') if settings['filter_genre'] == 'true' else []
	IGNORE_RATING  = proc_ig(settings['ignore_list'],'rating') if settings['filter_rating'] == 'true' else []
	IGNORES        = [IGNORE_SHOWS,IGNORE_GENRE,IGNORE_RATING]

	if settings['debug_type'] == '1':
		_addon_.setSetting(id="debug",value="false")

	return settings, IGNORES

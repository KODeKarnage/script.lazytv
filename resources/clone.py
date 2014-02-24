#!/usr/bin/python
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



import os
import xbmc
import xbmcgui
import sys
import string
import distutils
import time
import traceback
import re


__addon__        = xbmcaddon.Addon()
__addonid__      = __addon__.getAddonInfo('id')
__addonversion__ = __addon__.getAddonInfo('version')
__setting__      = __addon__.getSetting
lang             = __addon__.getLocalizedString
dialog           = xbmcgui.Dialog()
scriptPath       = __addon__.getAddonInfo('path')
addon_path         = xbmc.translatePath('special://home/addons')

start_time       = time.time()
base_time        = time.time()


def sanitize_strings(string):

	string.strip()
	valid_chars = "-_.()%s%s " % (string.ascii_letters, string.digits)
	san_name = ''.join(c for c in string if c in valid_chars)
	san_name = san_name.replace(' ','_')
	return san_name


def log(message, label = '', reset = False):
	if keep_logs:
		global start_time
		global base_time
		new_time     = time.time()
		gap_time     = "%5f" % (new_time - start_time)
		start_time   = new_time
		total_gap    = "%5f" % (new_time - base_time)
		logmsg       = '%s : %s :: %s ::: %s - %s ' % (__addonid__, total_gap, gap_time, label, message)
		xbmc.log(msg = logmsg)
		base_time    = start_time if reset else base_time


def errorHandle(exception, trace):

		log('An error occurred while creating the clone.')
		log(str(exception))
		log(str(trace))

		dialog.ok('LazyTV', 'An error occurred while creating the clone.','Operation cancelled.')
		sys.exit()


def Main():
	first_q = dialog.yesno('LazyTV','This script creates a cloned version of the LazyTV user interface.','It will create a new folder in your addons directory.','Do you wish to continue?')
	if first_q != 1:
		sys.exit()
	else:
		keyboard = xbmc.Keyboard('Name the clone')
		keyboard.doModal()
		if (keyboard.isConfirmed()):
			clone_name = keyboard.getText()
		else:
			sys.exit()

	# if the clone_name is blank then use default name of 'Clone'
	if not clone_name:
		clone_name = 'Clone'

	comb_name = 'LazyTV - %s' % clone_name
	san_name = sanitize_strings(clone_name)
	new_path = os.path.join(addon_path, san_name)

	log('clone_name = ' + str(clone_name))
	log('san_name = ' + str(san_name))
	log('new_path = ' + str(new+path))
	log('script path = ' + str(scriptPath))

	#check if folder exists, if it does then abort
	if os.path.isdir(new_path):

		log('That name is in use. Please try another')

		dialog.ok('LazyTV','That name is in use. Please try another')
		__addon__.openSettings()
		sys.exit()

	try:

		# copy current addon to new location
		distutils.dir_util.copy_tree(scriptPath,new_path)

		# remove the unneeded files
		addon_file = os.path.join(new_path,'addon.xml')

		os.remove(os.path.join(new_path,'service.py'))
		os.remove(addon_file)
		os.remove(os.path.join(new_path,'resources','selector.py'))
		os.remove(os.path.join(new_path,'resources','settings.xml'))
		os.remove(os.path.join(new_path,'resources','clone.py'))

		# replace the settings file and addon file with the truncated one
		os.move( os.path.join(new_path,'resources','addon_clone.xml') , addon_file )
		os.move( os.path.join(new_path,'resources','settings_clone.xml') , os.path.join(new_path,'resources','settings.xml') )

	except Exception:
		ex_type, ex, tb = sys.exc_info()
		errorHandle(e, tb)

	# edit the addon.xml to point to the right folder
	with open(addon_file, 'r+') as af:
		data = af.read()
		substitutions = {'SANNAME': san_name, 'CLONENAME': clone_name, 'COMBNAME':comb_name}
		pattern = re.compile(r'%([^%]+)%')
		data = re.sub(pattern, lambda m: substitutions[m.group(1)], data)

	dialog.ok('LazyTV', 'Cloning successful.','Clone ready for use.')


if __name__ == "__main__":

	log('Cloning started')

	Main()

	log('Cloning complete')
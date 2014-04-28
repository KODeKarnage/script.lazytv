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

''' A script to copy all the latest episodes included in the LazyTV listview to a folder selected by the user'''

import os
import xbmc
import xbmcaddon
import xbmcgui
import sys
import string
import shutil
import time
import traceback
import fileinput
import ast


__addon__        = xbmcaddon.Addon('script.lazytv')
__addonid__      = __addon__.getAddonInfo('id')
__setting__      = __addon__.getSetting
lang             = __addon__.getLocalizedString
dialog           = xbmcgui.Dialog()
scriptPath       = __addon__.getAddonInfo('path')
addon_path       = xbmc.translatePath('special://home/addons')
keep_logs        = True if __setting__('logging') == 'true' else False

start_time       = time.time()
base_time        = time.time()


def log(message, label = '', reset = False):
	if keep_logs:
		global start_time
		global base_time
		new_time     = time.time()
		gap_time     = "%5f" % (new_time - start_time)
		start_time   = new_time
		total_gap    = "%5f" % (new_time - base_time)
		logmsg       = '%s : %s :: %s ::: %s - %s ' % ('LazyTV episode_exporter', total_gap, gap_time, label, message)
		xbmc.log(msg = logmsg)
		base_time    = start_time if reset else base_time


def Main():

	# open location selection window
	location = dialog.browse(3,lang(32180),'default')

	# store location for next time
	# TODO

	log("export location: " + str(location))

	# get nepl
	nepl_from_service = WINDOW.getProperty("LazyTV.nepl")

	if nepl_from_service:
		p = ast.literal_eval(nepl_from_service)
		nepl_stored = [int(x) for x in p]
	else:
		dialog.ok('LazyTV',lang(32115),lang(32116))
		log("nepl not available")
		sys.exit()

	# get file of selected shows
	file_list = [WINDOW.getProperty("%s.%s.File" % ('LazyTV', neep)) for neep in nepl_stored]

	failures = []

	for video_file in file_list:
		try:
			if not os.path.isfile(os.path.join(location, os.path.basename(videofile))):
				shutil.copyfile(videofile, os.path.join(location, os.path.basename(videofile)))
				log("file exported: " + str(os.path.basename(videofile)))
		except:
			failures.append(os.path.basename(videofile))
			log("file failed to export: " + str(os.path.basename(videofile)))


	if failures:
		ans = dialog.yesno('LazyTV', lang(32182),lang(32183))
		
		if ans:
			# populate list view with file names in alphabetical order

			failures.sort()

			dialog.select('LazyTV', failures)


if __name__ == "__main__":

	Main()


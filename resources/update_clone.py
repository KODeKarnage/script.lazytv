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

''' A script to update this cloned version of LazyTV from the main LazyTV install '''

import distutils
import xbmcgui
import re
import sys
import time

src_path   = sys.argv[1]
new_path   = sys.argv[2]
san_name   = sys.argv[3]
clone_name = sys.argv[4]
comb_name  = 'LazyTV - ' + clone_name

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
		logmsg       = '%s : %s :: %s ::: %s - %s ' % (__addonid__, total_gap, gap_time, label, message)
		xbmc.log(msg = logmsg)
		base_time    = start_time if reset else base_time



def errorHandle(exception, trace):

		log('An error occurred while creating the clone.')
		log(str(exception))
		log(str(trace))

		dialog.ok('LazyTV', 'An error occurred while updating the clone.','Operation cancelled.')
		sys.exit()


def Main():
	try:
		# copy current addon to new location
		distutils.dir_util.copy_tree(src_path,new_path)

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

	log('Updating started')

	Main()

	log('Updating complete')
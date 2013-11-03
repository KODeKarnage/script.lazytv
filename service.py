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

"""
Launch Monitor class to check for library updates
 add setting to specify how often to run the check in the background

Launch Player class to catch item starts and resume opportunities
 maybe use RequestNextItem as the trigger for both?
Have Default.py announce that it is running a playlist
Then have the Player (once it recognises that default has run) intermittently check if the player is still playing,
and if it isnt, then reset the announcement back to not running
Player checks for that announcement before allowing Resume or Notify


Service = waiting for signal or library update
LazyTV = started by user, random playlist selected, Resume and Notification in settings, sends Signal, sets LTV as active
Signal = [Resume, Notify, Resume Data, Notify Data]
Service = recieves signal, activates Player, provides data from Signal
Player = Notify and/or Resume with provided data, runs until player finishes, then ends setting LTV as inactive
		and lets Service know it can run

XBMC = updates library
Service = checks if LTV is active, if it is then do nothing, once LTV isnt active, wait 10 seconds
		 then generate the Next_List

		= if LTV is not active then generate full Next_List


OnInit for service, set LTV to inactive (this is to account for crashes while playing, where LTV would be left active)



"""

import xbmc
import xbmcgui
import xbmcaddon
import os
import datetime

__addonid__ = "script.lazytv"
__addon__  = xbmcaddon.Addon(__addonid__)
__scriptPath__        = __addon__.getAddonInfo('path')
__profile__ = xbmc.translatePath(__addon__.getAddonInfo('profile'))
__setting__ = __addon__.getSetting

def log(vname, message):
	#if settings['debug']:
	xbmc.log(msg=vname + " -- " + str(message))

class Main:
	def __init__(self):
		self.service_says = os.path.join(__profile__,'service_says')
		self.addon_says = os.path.join(__profile__,'addon_says')
		self.addon_says = os.path.join(__profile__,'last_scan')
		log('Yawn','HERE')
		self._comm('YAWN!')
		self.monitor = LazyMonitor()
		self.player = LazyPlayer()
		 #announces it is running
		# check if comm file exists, if it doesnt, make it
		# announce "Yawn!"

	def _daemon(self):
		pass
		while not xbmc.abortRequested:

			#check comm file
			#if comm file says "Gimme!" call scanalyse
			xbmc.sleep(100)


	def scanalyse(self):
		#gets complete list of ondeck shows
		#the addon can then work wih that list
		pass



	def _comm(self, comm_string):
		with open(self.service_says,"w") as f:
			f.write(comm_string)



class LazyPlayer(xbmc.Player):
	def __init__(self, *args, **kwargs):
		xbmc.Player.__init__(self)

	def onPlayBackStarted(self):
		pass

	def onPlayBackEnded(self):
		self.onPlayBackStopped()

	def onPlayBackStopped(self):
		pass



class LazyMonitor(xbmc.Monitor):
	def __init__(self, *args, **kwargs):

		# Set a window property that let's other scripts know we are running (window properties are cleared on XBMC start)
		xbmcgui.Window(10000).setProperty('%s_service_running' % __addon__, 'True')
		xbmc.executebuiltin('Notification("LazyTV Service has started",20000)')
		xbmc.log(msg="sssssssssssssss -- ssssssssssssssss")
		xbmc.log(msg=xbmcgui.Window(10000).getProperty('%s_service_running' % __addon__))
		xbmc.Monitor.__init__(self)

	def onDatabaseUpdated(self, database):
		xbmc.log('PONG!' + str(datetime.datetime.now()))

	def pop_your_head_up(self):
		pass
		xbmc.log('HEADSUP!' + str(datetime.datetime.now()))
		# check everything

		# check if SCANALYSE is being called by LazyTV addon
		# check if last SCANALYSE was more than TIME_BETWEEN ago
		# check if player is active
			# - track what is being played
			# - wait for player to finish
			# - on finish check if TV show
				# - if TV show, check if DB entry has changed
					# - if DB entry now watched, update entry in STORED LISTS
			
			# SCANALYSE
			#	- check type of list
			#	- check type of filter

if ( __name__ == "__main__" ):
	xbmc.sleep(3000)
	Main()
	del Main
'''
while not xbmc.abortRequested:
      xbmc.sleep(1000)
      xbmc.log('PING! READY!' + str(datetime.datetime.now()))


xbmc.log('PUNG! ENDED!' + str(datetime.datetime.now()))'''

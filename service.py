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
from resources.lazy_lib import *
from resources.lazy_queries import *

__addonid__ = "script.lazytv"
__addon__  = xbmcaddon.Addon(__addonid__)
__scriptPath__        = __addon__.getAddonInfo('path')
__profile__ = xbmc.translatePath(__addon__.getAddonInfo('profile'))
__setting__ = __addon__.getSetting
WINDOW = xbmcgui.Window(10000)

def log(vname, message):
	#if settings['debug']:
	xbmc.log(msg=vname + " -- " + str(message))


class LazyPlayer(xbmc.Player):
	def __init__(self, *args, **kwargs):
		xbmc.Player.__init__(self)

	def onPlayBackStarted(self):
		xbmc.log('PONG! started')

	def onPlayBackEnded(self):
		self.onPlayBackStopped()

	def onPlayBackStopped(self):
		xbmc.log('PONG! Stopped')


class LazyMonitor(xbmc.Monitor):
	def __init__(self, *args, **kwargs):

		# Set a window property that let's other scripts know we are running (window properties are cleared on XBMC start)
		WINDOW.setProperty('%s_service_running' % __addon__, 'True')
		xbmc.executebuiltin('Notification("LazyTV Service has started",20000)')
		xbmc.log(msg=xbmcgui.Window(10000).getProperty('%s_service_running' % __addon__))
		xbmc.Monitor.__init__(self)
		self.lzplayer = LazyPlayer()

		self.grab_settings()

		self.each_setting = 'a'
		self.each_setting = 'a'
		self.each_setting = 'a'
		self.each_setting = 'a'
		self.each_setting = 'a'
		self.each_setting = 'a'

		self._daemon()


	def _daemon(self):
		while not xbmc.abortRequested:
			xbmc.sleep(100)

	def onSettingsChanged(self):
		self.grab_settings()
		self.get_show_ids()


	def onDatabaseUpdated(self, database):
		xbmc.sleep(1000)
		self.get_show_ids()
		#call update tv show list
		#call update all shows


	def onNotification(self, sender, method, data):

		if method == 'VideoLibrary.OnUpdate':
			# playcount change
			# Method 		VideoLibrary.OnUpdate
			# data 			{"item":{"id":1,"type":"episode"},"playcount":4}
			if 'item' in data:
				if 'playcount' in data:
					if 'type' in data['item']:
						if data['item']['type'] == 'episode':
							if data['playcount'] < 2:
								pass
								#get showID and re-run getnextepisode for that show

		elif method == 'Player.OnPlay':
			# player started
			# Method 		Player.OnPlay
			# data 			{"item":{"id":1,"type":"episode"},"player":{"playerid":1,"speed":1}}
			if 'item' in data:
				if 'type' in data['item']:
					if data['item']['type'] == 'episode':
						if 'player' in data:
							pass
							#show notification if set

		elif method = 'VideoLibrary.OnScanFinished':
			# database finished updating
			# Method 		VideoLibrary.OnScanFinished
			self.onDatabaseUpdated()



		xbmc.log('PiNG Sender ' + str(sender))
		xbmc.log('PiNG Method ' + str(method))
		xbmc.log('PiNG Data ' + str(data))

	def get_show_ids(self):
		pass

	def grab_settings(self):
		pass

if ( __name__ == "__main__" ):
	xbmc.sleep(3000)
	LazyMonitor()
	del LazyMonitor


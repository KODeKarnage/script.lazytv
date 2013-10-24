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
import datetime


class myMonitor(xbmc.Monitor):
	def __init__(self, *args, **kwargs):
		xbmc.Monitor.__init__(self)
		xbmc.log('PENG! STARTED' + str(datetime.datetime.now()))
		self.keepalive()

	def onDatabaseUpdated(self, database):
		xbmc.log('PONG!' + str(datetime.datetime.now()))

	def keepalive(self):
		while not xbmc.abortRequested:
			xbmc.sleep(1000)




kbm = myMonitor()

while not xbmc.abortRequested:
      xbmc.sleep(10000)
      xbmc.log('PING! READY!' + str(datetime.datetime.now()))

xbmc.log('PUNG! ENDED!' + str(datetime.datetime.now()))
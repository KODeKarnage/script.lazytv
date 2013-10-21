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


















"""
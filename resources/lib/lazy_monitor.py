#!/usr/bin/python
# -*- coding: utf-8 -*-

#  Copyright (C) 2019 KodeKarnage
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

from __future__ import print_function

import xbmc
import json


class LazyMonitor(xbmc.Monitor):
    def __init__(self, *args, **kwargs):

        xbmc.Monitor.__init__(self)

        self.queue = kwargs.get("queue", "")
        self.log = kwargs.get("log", "")

    def onSettingsChanged(self):

        self.queue.put({"update_settings": {}})

    def onDatabaseUpdated(self, database):

        if database == "video":

            # update the entire list again, this is to ensure we have picked up
            # any new shows.
            self.queue.put({"full_library_refresh": []})

    def onNotification(self, sender, method, data):

        # this only works for GOTHAM and later

        self.log('METHOD: %s' % method)

        skip = False

        try:
            self.ndata = json.loads(data)
        except Exception as e:
            skip = True

        if skip == True:
            pass
            self.log(data, "Unreadable notification")

        elif method == "VideoLibrary.OnUpdate":
            # Method        VideoLibrary.OnUpdate
            # data          {"item":{"id":1,"type":"episode"},"playcount":4}
            self.log(self.ndata)
            item = self.ndata.get("item", False)
            playcount = self.ndata.get("playcount", False)
            itemtype = item.get("type", False)
            epid = item.get("id", False)

            if all([item, itemtype == "episode", playcount == 1]):

                return {"manual_watched_change": epid}

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

import xbmc
import json
import xbmcaddon
import xbmcgui

__addon__ = xbmcaddon.Addon("script.lazytv")
__addonid__ = __addon__.getAddonInfo("id")


def lang(id):
    san = __addon__.getLocalizedString(id).encode("utf-8", "ignore")
    return san


plf = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "Files.GetDirectory",
    "params": {"directory": "special://profile/playlists/video/", "media": "video"},
}


def json_query(query, ret):
    try:
        xbmc_request = json.dumps(query)
        result = xbmc.executeJSONRPC(xbmc_request)
        # print result
        # result = unicode(result, 'utf-8', errors='ignore')
        if ret:
            return json.loads(result)["result"]
        else:
            return json.loads(result)
    except:
        return {}


def playlist_selection_window():
    """ Purpose: launch Select Window populated with smart playlists """

    playlist_files = json_query(plf, True)["files"]

    if playlist_files != None:

        plist_files = dict((x["label"], x["file"]) for x in playlist_files)

        playlist_list = plist_files.keys()

        playlist_list.sort()

        inputchoice = xbmcgui.Dialog().select(lang(32104), playlist_list)

        return plist_files[playlist_list[inputchoice]]
    else:
        return "empty"


pl = playlist_selection_window()

__addon__.setSetting(id="users_spl", value=str(pl))

__addon__.openSettings()

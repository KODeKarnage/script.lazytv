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

import os
import xbmc


class LazyPlayListMaintainer(object):
    def __init__(self, settings, show_store, log):

        self.log = log

        self.s = settings
        self.show_store = show_store

        self.playlist_file = os.path.join(
            xbmc.translatePath("special://profile/playlists/video/"), "LazyTV.xsp"
        )
        self.log(self.playlist_file, "LazyTV Playlist_file location: ")

        self.first_line = '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?><smartplaylist type="episodes"><name>LazyTV</name><match>one</match>\n'
        self.last_line = '<order direction="ascending">random</order></smartplaylist>'

        self.rawshowline = '<!--%s--><rule field="filename" operator="is"> <value>%s</value> </rule><!--END-->\n'

    def _read_playlist(self):

        self._check_file()

        with open(self.playlist_file, "r") as f:
            lines = f.readlines()

        return lines

    def _check_file(self):

        # creates the file if it doesnt already exist
        if not os.path.isfile(self.playlist_file):
            self.log("Playlist file does not exist; creating new file")
            self._pave_file()

    def _pave_file(self):

        with open(self.playlist_file, "w") as f:
            f.write("")

    def _write_file(self, lines):
        """ Writes the provided lines to the file """

        self.log("Writing to the playlist file")

        with open(self.playlist_file, "w") as f:
            f.writelines(lines)

    def _ep_details(self, showid):
        """ takes a showid and returns the showname and the filename of the next ondeck episode """

        showname = self.show_store[showid].show_title
        ep_file = self.show_store[showid].eps_store.get("on_deck_ep", None)

        if ep_file:
            ep_file = os.path.basename(ep_file.File)

        return showname, ep_file

    def update_playlist(self, showid_list):
        """ takes a list of showids, looks through the playlist file, removes the show where it is found,
        replaces it with the next ondeck episode (if that exists)"""

        lines = self._read_playlist()

        for showid in showid_list:

            showname, ep_file = self._ep_details(showid)

            # remove all the lines relating to the showid
            lines = [x for x in lines if not x.startswith("<!--%s-->" % showname)]

            # add the new line to the end of the file (before the last line)
            if ep_file:
                lines.insert(-1, self.rawshowline % (showname, ep_file))

        # add in the first and last lines if they arent present
        if self.first_line not in lines:
            lines.insert(0, self.first_line)
        if self.last_line not in lines:
            lines.append(self.last_line)

        self._write_file(lines)

    def new_playlist(self):
        """ Creates a brand new playlist from everything in the show_store """

        showids = self.show_store.keys()

        self._pave_file()

        self.update_playlist(showids)

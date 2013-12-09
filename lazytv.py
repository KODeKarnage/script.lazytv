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


*************************************
********** Get Eps Machine **********
*************************************


Create a Machine (getnextep): ********** Can be called by skins **********

    takes:
        limit (def = 0)
        showIDs (def = [])
        caller_handle (sys.argv[1]???)
        type (def = user)   can be [user, latest_watched, random]

    actions:
        run query1
        remove ids not in received showIDs (accept all if no showIDs received)
        sort by latest
        accept first #limit# if limit = 0 accept all

        for each show:
            query2 with showID
            find last watched
            use to find next to watch
            add to 10000:
                id of details in 10000 must include showID (i.e. lazytv_ondeck_showID)
                    __ also include callerID (handle???) so skin list can differ from user list
                save to 10000 as plugin folder (when art available)

def next_episode_generator(limit = 0, showIDs = [], caller, type = 'user'):

    pass

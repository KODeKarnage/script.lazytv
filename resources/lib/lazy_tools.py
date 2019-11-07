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

# XBMC modules
import xbmc
import xbmcaddon
import xbmcgui

# STANDARD library modules
import ast
import datetime
import json
import os
import pickle
import Queue
import re
import socket
import threading
import time

# LAZYTV modules
import lazy_queries as Q






















def service_request(request, log):
    """ Used by the gui to request data from the service.
		Returns python objects. """

    address = ("localhost", 16458)

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    sock.connect(address)

    # serialise the request before sending to Main
    serialised_request = pickle.dumps(request)
    sock.send(serialised_request)

    # list to hold the parts of the response
    msg = []

    # loop to collect the portions of the response
    # recv will throw a 'resource temporarily unavailable' error
    # if there is no more data
    while True:
        try:
            response = sock.recv(8192)

            # this ensures the socket is only blocked once
            sock.setblocking(0)

            if not response:
                break

        except:
            break

        # add the part of the response to the list
        msg.append(response)

    # join the parts of the message together
    complete_msg = "".join(msg)

    # if the message isnt empty, deserialise it with json.loads
    if complete_msg:
        deserialised_response = pickle.loads(complete_msg)
    else:
        deserialised_response = complete_msg

    # close the socket
    sock.close()

    return deserialised_response


def inst_extend(instance, new_class):
    new_name = "%s_extended_with_%s" % (instance.__class__.__name__, new_class.__name__)
    instance.__class__ = type(new_name, (instance.__class__, new_class), {})

    print(new_name)


def extend(instance, cls):
    print(cls)
    instance.__class__.__bases__ = (cls,)


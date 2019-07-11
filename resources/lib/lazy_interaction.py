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

# XBMC modules
import xbmc
import xbmcaddon
import xbmcgui


class LazyInteraction(object):
    """ Class to handle interactions with the user for the service and launcher.
    """

    def __init__(self, settings, log, lang, release):

        self.s = settings
        self.log = log
        self.lang = lang
        self.release = release
        self.DIALOG = xbmcgui.Dialog()

    # ON STOP method
    def next_ep_prompt(self, next_ep):
        """ Displays the dialog for the next prompt, returns 0 or 1 for dont
        play or play
        """

        if xbmc.Player().isPlaying():

            self.internal_notification(next_ep)

        else:

            self.external_notification(next_ep)

    def internal_notification(self, next_ep):
        """ Displays the next up notification if the second trigger has been
        pulled and something is still playing."""

        self.log(
            "next_prompt dialog method reached, showtitle: {}, season: {}, episode: {}".format(
                next_ep.show_title, next_ep.Season, next_ep.Episode
            )
        )

        nextUpPage = NextUpInfo(
            "script-nextup-notification-NextUpInfo.xml",
            addonSettings.getAddonInfo("path"),
            "default",
            "720p",
        )
        nextUpPage.setItem(next_ep)

        # playMode = addonSettings.getSetting("autoPlayMode") # re-retrieve playmode

        # nextUpPage.setPlaymode(playMode)

        playTime, totalTime = xbmc.Player().getTime(), xbmc.Player().getTotalTime()

        nextUpPage.show()

        playTime, totalTime = xbmc.Player().getTime(), xbmc.Player().getTotalTime()

        while (
            xbmc.Player().isPlaying()
            and (totalTime - playTime > 1)
            and not nextUpPage.isCancel()
            and not nextUpPage.isWatchNow()
        ):

            xbmc.sleep(100)

            playTime, totalTime = xbmc.Player().getTime(), xbmc.Player().getTotalTime()

        nextUpPage.close()

        if (not nextUpPage.isCancel() and playMode == "0") or (
            nextUpPage.isWatchNow() and playMode == "1"
        ):
            self.logMsg("playing media episode id %s" % str(episode["episodeid"]), 2)
            # Play media
            xbmc.executeJSONRPC(
                '{ "jsonrpc": "2.0", "id": 0, "method": "Player.Open", "params": { "item": {"episodeid": '
                + str(episode["episodeid"])
                + "} } }"
            )

    def external_notification(self, next_ep):
        """ Displays the next up notification if the first trigger has been
        pulled the episode has stopped or has ended.
        """

        self.log(
            "next_prompt dialog method reached, showtitle: {}, season: {}, episode: {}".format(
                next_ep.show_title, next_ep.Season, next_ep.Episode
            )
        )
        self.log(self.release, "release: ")

        # setting this to catch error without disrupting UI
        prompt = -1

        # format the season and episode
        SE = str(int(next_ep.Season)) + "x" + str(int(next_ep.Episode))

        # if default is PLAY
        if self.s["promptdefaultaction"] == 0:
            ylabel = self.lang(32092)  # "Play"
            nlabel = self.lang(32091)  # "Dont Play

        # if default is DONT PLAY
        elif self.s["promptdefaultaction"] == 1:
            ylabel = self.lang(32091)  # "Dont Play
            nlabel = self.lang(32092)  # "Play"

        if self.release == "Frodo":
            if self.s["promptduration"]:
                prompt = self.DIALOG.select(
                    self.lang(32164),
                    [
                        self.lang(32165) % self.s["promptduration"],
                        self.lang(32166) % (next_ep.show_title, SE),
                    ],
                    autoclose=int(self.s["promptduration"] * 1000),
                )
            else:
                prompt = self.DIALOG.select(
                    self.lang(32164),
                    [
                        self.lang(32165) % self.s["promptduration"],
                        self.lang(32166) % (next_ep.show_title, SE),
                    ],
                )

        else:
            if self.s["promptduration"]:
                prompt = self.DIALOG.yesno(
                    self.lang(32167) % self.s["promptduration"],
                    self.lang(32168) % (next_ep.show_title, SE),
                    self.lang(32169),
                    yeslabel=ylabel,
                    nolabel=nlabel,
                    autoclose=int(self.s["promptduration"] * 1000),
                )
            else:
                prompt = self.DIALOG.yesno(
                    self.lang(32167) % self.s["promptduration"],
                    self.lang(32168) % (next_ep.show_title, SE),
                    self.lang(32169),
                    yeslabel=ylabel,
                    nolabel=nlabel,
                )

        self.log(prompt, "user prompt: ")

        # if the user exits, then dont play
        if prompt == -1:
            prompt = 0

        # if the default is DONT PLAY then swap the responses
        elif self.s["promptdefaultaction"] == 1:
            if prompt == 0:
                prompt = 1
            else:
                prompt = 0

        self.log(self.s["promptdefaultaction"], "default action: ")
        self.log(prompt, "final prompt: ")

        return prompt

    # USER INTERACTION
    def user_input_launch_action(self):
        """ If needed, asks the user which action they would like to perform """

        choice = self.DIALOG.yesno(
            "LazyTV",
            self.lang(32100),
            "",
            self.lang(32101),
            self.lang(32102),
            self.lang(32103),
        )

        return choice

    def display_prev_check(self, showtitle, season, episode):
        """ Displays the notification of there being a previous episode to watch
        before the current one.
        """

        return self.DIALOG.yesno(
            self.lang(32160),
            self.lang(32161) % (showtitle, season, episode),
            self.lang(32162),
        )

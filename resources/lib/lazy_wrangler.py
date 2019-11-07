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

# Standard Library Modules


# LazyTV Modules
import lazy_queries as Q
import lazy_tools as T
from lazy_tvshow import LazyTVShow, miniTVShow


Wrangler is charged with maintaining a list of TV Shows
- nothing talks to TV Shows directly other than wrangler, just like nothing
    talks to episodes other than TV Shows
- calling them to be created 
- setting their type 
- providing their lastplayed 
- providing their widget position
- messages can be passed from TV Show to Wrangler (via event loop?) to announce
    when a TV Show is nearly ended
- wrangler provides set of ListItems to GUI, and set of Episodes to RandomPlayer 
- wrangler recieves messages about updating entries

STARTING POINT
- check the wrangler matches the description above (that was the latest thinking on the topic)
- note: I added a self.complete flag to each TVSHow, better than removing them completely

class LazyWrangler(object):
    """ The Wrangler maintains the ShowStore (list of TV shows). Interaction with
    the TV Shows only takes place through the Wrangler. This object is passed the
    parent, and can call methods from the Parent such as those updating data in
    the Widget and the data in the GUI.

    Wrangler's methods include:
        - populate_from_kodi: gets all the TV Show information from the Library

        - establish_shows: creates the Show objects, threads the create show method

        - _create_TVShow: the method that actually does the Show creating

        - full_library_refresh: grabs all shows, establishes them, calls the
            Service's widget data update and GUI update methods

        - remove_show: removes a show from the ShowStore (if it has no episodes
            remaining) and calls the Parent GUIo update method

        - refresh_single: calls the partial refresh method on a specific TV Show

        - swap_triggered: swaps the temp episode in for the OnDeck episode, this
            occurs when the IMP says a show has been watched.

        - manual_watched_change: changes the watched status of a single show,
            without relying on a Library call (as in, when the IMP says a show
            has been watched). Calls parents widget and GUI update methods.

        - rando_change: calls the partial refresh on show where the show type
            has changed

        - retrieve_add_ep: retrieves one more episode from the supplied show

        - pass_all_epitems: Gets the on deck episodes from all shows and provides
            them in a list.

    """

    def __init__(self, parent, user_settings, log, lang):

        self.parent = parent
        self.user_settings = user_settings
        self.log = log
        self.lang = lang
        self.WINDOW = xbmcgui.Window(10000)

        self.TVShow_list = []

        # This maps the settings to the methods to call if they have changed.
        self.setting_action_map = {
            "excl_randos": None,
            "filterYN": None,
            "first_run": None,
            "IGNORE": None,
            "keep_logs": None,
            "length": None,
            "limitshows": None,
            "maintainsmartplaylist": None,
            "moviemid": None,
            "movies": None,
            "moviesw": None,
            "movieweight": None,
            "multipleshows": None,
            "nextprompt": None,
            "nextprompt_or": None,
            "nextup_timing": None,
            "noshow": None,
            "playlist_notifications": None,
            "populate_by_d": None,
            "premieres": None,
            "prevcheck": None,
            "primary_function": None,
            "promptdefaultaction": None,
            "promptduration": None,
            "randos": self.setShowType,
            "resume_partials": None,
            "select_pl": None,
            "selection": None,
            "skin_return": None,
            "skinorno": None,
            "sort_by": None,
            "sort_reverse": None,
            "start_partials": None,
            "startup": None,
            "trigger_position_metric": None,
            "users_spl": None,
            "window_length": None,
        }


    def clear_TVShow_List(self, *args, **kwargs):

        for show in self.TVShow_List:
            show.OnDeck.updateWindowProperties(clear=True)

        self.TVShow_List = []

    def populate_from_kodi(self):
        """ Populates the TVShow_List with show information extracted from Kodi.
        The only show information we get is the show name and the last time it was
        played. This is all the information we need to populate the show list and
        determine the order in which the shows will be in any widget.

        When creating the show, we provide the ShowId, the Show Title, the time
        lastplayed and the widget order.

        Calling this method is, in effect, a full refresh of the TVShow_List.
        
        If the show list is not empty, then actively clear it out. This entails
        clearing the window stored information.
        """

        if self.TVShow_List:
            self.clear_TVShow_List()

        raw_show_data = T.json_query(Q.all_show_ids)

        for show_data in raw_show_data.get("tvshows", []):

            showid = show_data.get('tvshowid', None)
            title = show_data.get('title', None)
            lastplayed = show_data.get('lastplayed', None)
            if (showid is None) | (title is None):
                continue
            
            self.TVShow_List.append(
                LazyTVShow(
                    showId=showid,
                    show_type=None,
                    show_title=title,
                    lastplayed=lastplayed,
                    widget_position=None,
                    )
                )

        self.setWidgetOrder()
        self.setShowType()

        self.populateTVShows()


    def updateUserSettings(self, new_user_settings):
        """ Method used to inform the Wrangler of new user settings becoming 
        available. The Wrangler will compare settings values here, and determine
        what needs changing.
        """

        for k, new_value in new_user_settings.iteritems():
            if new_value != self.user_settings.get(k, None):
                self.user_settings[k] = new_value
                func = self.setting_action_map.get(k, None)
                if update_method is not None:
                    update_method()


    def setWidgetOrder(self):
        """ Sets the widget order for each show in the TVShow_List. 
        """

        # Reorder the show list by the lastplayed
        self.TVShow_List = sorted(self.TVShow_List, key=lambda x: x.lastplayed, reverse=True)

        # Populate the widget order for each show
        self.TVShow_List = [shw.update_widget_position(i) for i, shw in enumerate(self.TVShow_List)]


    def setShowType(self, *args, **kwargs):
        """ Sets the show type (normal or random) for each show in the TVShow_List.
        """

        def getTypeFor(show):
            if show.showId in RandomPlay:
                return "Random"
            else:
                return "Normal"

        RandomPlay = self.user_settings.get("randos", [])
        _ = (shw.update_show_type(getTypeFor(show)) for show in self.TVShow_List)


    def populateTVShows(self):
        """ Calls each TV show and tells it to update its episode information, 
        including the assignment of the OnDeck and BelowDeck episodes.
        """

        (shw.populate_from_kodi() for shw in self.TVShow_List)


USER can set a list of Randos
and Select which shows get populated, either by 
    - manual selection (with the showid being a setting)
    - or through the use of a smart playlist
THE IMPORTANT THING IS THAT THE POPULATE FROM KODI AND POPULATE FROM DICT 
MUST FILTER OUT NON-SELECTED TVSHOWS
tHE QUESTION IS WHERE TO ACTUALLY DO THAT
answer: the items calling the wrangler can do their own exclusion checking
        , the reason being that clones will have their own exclusion list,
        but there is only one wrangler running
        Wrangler must remain agnostic to what a users selection criteria is
        But randos are universal


IS THE WIDGET EVEN NEEDED?

GOT TO HERE        : code below here hasnt been changed


    def establish_shows(self):
        """ creates the show objects if it doesnt already exist,
            if it does exist, then do nothing """

        self.log("establish_shows reached")

        items = [
            {"object": self, "args": {"showID": k}}
            for k, v in self.show_base_info.iteritems()
        ]


    def _create_TVShow(self, showID):
        """ Creates the show, or merely updates the lastplayed stat if the
            show object already exists """

        if showID not in self.show_store.keys():
            # show not found in store, so create the show now

            if showID in self.user_settings["randos"]:
                show_type = "randos"
            else:
                show_type = "normal"

            show_title = self.show_base_info[showID].get("show_title", "")
            last_played = self.show_base_info[showID].get("last_played", "")

            if last_played:
                last_played = T.day_conv(last_played)

            self.log(
                "creating show, showID: {}, \
                show_type: {}, show_title: {}, \
                last_played: {}".format(
                    showID, show_type, show_title, last_played
                )
            )

            # this is the part that actually creates the show
            self.show_store[showID] = LazyTVShow(
                showID,
                show_type,
                show_title,
                last_played,
                self.parent.lazy_queue,
                self.log,
                self.WINDOW,
            )

        else:

            # if show found then update when lastplayed
            last_played = self.show_store[showID].get("last_played", "")

            self.log(showID, "show found, updating last played: ")

            if last_played:
                self.show_store[showID].last_played = T.day_conv(last_played)

    def full_library_refresh(self):
        """ initiates a full refresh of all shows """

        self.log("full_library_refresh reached")

        # refresh the show list
        self.populate_from_kodi()

        # Establish any shows that are missing, each show is started with a full refresh.
        # The code blocks here until all shows are built.
        self.establish_shows()

        # update widget data in Home Window
        self.parent.update_widget_data()

        # calls for the GUI to be updated (if it exists)
        self.parent.Update_GUI()

    def remove_show(self, showid, update_spl=True):
        """ the show has no episodes, so remove it from show store """

        self.log(showid, "remove_show called: ")

        if showid in self.show_store.keys():

            del self.show_store[showid].eps_store["on_deck_ep"]
            del self.show_store[showid].eps_store["temp_ep"]

            if update_spl:
                self.parent.playlist_maintainer(showid=[showid])

            del self.show_store[showid]

            self.log("remove_show show removed")

            # calls for the GUI to be updated (if it exists)
            self.parent.Update_GUI()

    def refresh_single(self, showid):
        """ refreshes the data for a single show """

        self.log(showid, "refresh_single reached: ")

        self.show_store[showid].partial_refresh()

    def manual_watched_change(self, epid):
        """ change the watched status of a single episode """

        self.log(epid, "manual_watched_change reached: ")

        showid = self.reverse_lookup(epid)

        if showid:

            self.log(showid, "reverse lookup returned: ")

            self.show_store[showid].update_watched_status(epid, True)

            # update widget data in Home Window
            self.parent.update_widget_data()

            # Update playlist with new information
            self.parent.playlist_maintainer.update_playlist([showid])

            # calls for the GUI to be updated (if it exists)
            self.parent.Update_GUI()

    def swap_triggered(self, showid):
        """ This process is called when the IMP announces that a show has past its trigger point.
            The boolean self.swapped is changed to the showID. """

        self.log(showid, "swap triggered, initiated: ")

        self.show_store[showid].swap_over_ep()

        # calls for the GUI to be updated (if it exists)
        self.parent.Update_GUI()

        # update widget data in Home Window
        self.parent.update_widget_data()

        # Update playlist with new information
        self.parent.playlist_maintainer.update_playlist([showid])

        return showid

    def rando_change(self, show, new_rando_list, current_type):
        """ Calls the partial refresh on show where the show type has changed """

        self.log(
            "%s: %s: %s" % (show.showID, current_type, show.showID in new_rando_list)
        )

        if current_type == "randos" and show.showID not in new_rando_list:

            show.show_type = "normal"

            show.partial_refresh()

        elif current_type != "randos" and show.showID in new_rando_list:

            show.show_type = "randos"

            show.partial_refresh()

        # update widget data in Home Window
        self.parent.update_widget_data()

    def retrieve_add_ep(self, showid, epid_list, respond_in_comms=True):
        """ Retrieves one more episode from the supplied show. If epid_list is
        provided, then the episode after the last one in the list is returned.
        If respond_in_comms is true, then place the response in the queue for
        external communication, otherwise just return the new episode id from
        the function. """

        show = self.show_store[showid]

        new_episode = show.find_next_ep(epid_list)

        if respond_in_comms:

            response = {"new_epid": new_episode}

            self.parent.comm_queue.put(response)

        else:

            return new_episode

    def pass_all_epitems(self, permitted_shows=[]):
        """ Gets the on deck episodes from all shows and provides them
            in a list. Restricts shows to those in the show_id list, if provided.
        """

        if permitted_shows == "all":
            permitted_shows = []

        all_epitems = [
            show.eps_store["on_deck_ep"]
            for k, show in self.show_store.iteritems()
            if any([not permitted_shows, show.showID in permitted_shows])
        ]

        return all_epitems

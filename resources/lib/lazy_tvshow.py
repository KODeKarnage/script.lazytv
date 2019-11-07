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

# Standard Modules
import random

# LazyTV Modules
from lazy_episode import LazyEpisode, miniEpisode
import lazy_queries as Q
import lazy_tools as T

class LazyTVShow(object):
    """ The TV Show handles the construction and maintenance of a list of Episodes.

    TV Shows carry some of their own data, such as the showId and show title, 
    the last time an episode of the show was played, and the Type of show as 
    determined by the user. (Show types are either OnDeck or Random Unplayed).

    The TV Show selects the OnDeck episode (that is, the episode that will next
    be provided if the TV Show is asked for an episode) and a BelowDeck episode (which
    is the next episode after that.) When instructed to, it will swap the BelowDeck
    episode into the OnDeck slot and find a new BelowDeck episode.

    The TV Show maintains a list of all it's episodes, along with information
    necessary to select the OnDeck and BelowDeck episodes.

    When provided with an EpisodeId, the TV Show check whether the Episode has
    any unplayed episodes before it, in case the user wants a warning in that
    regard.

    The TV Show can be populated from either a call to the Kodi database, or
    by provision of a dictionary of properties.

    Episodes are xbmcgui.ListItems. 
    """

    def __init__(
        self,
        showId,
        show_type,
        show_title,
        lastplayed,
        widget_position,
        queue,
        log,
        *args,
        **kwargs
    ):

        self.showId = showId

        self.show_type = show_type
        self.show_title = show_title
        self.lastplayed = lastplayed
        self.widget_position = widget_position

        self.queue = queue
        self.log = log

        self.WINDOW = xbmcgui.Window(10000)

        self.OnDeck = None
        self.BelowDeck = None

        self.episode_list = []

        # This variable can be used by the Wrangler to ignore this TV Show.
        # The show can be reinstated if
        self.isComplete = False

    def populate_from_dict(self, tvshow_dictionary, *args, **kwargs):
        """ Populates the TV Show information from a provided dictionary.
        This is most likely to occur when refreshing from the exported data
        when LazyTV first starts. (As the full refresh takes a long time on
        weaker devices like the Pi.)
        """

        self.show_type = tvshow_dictionary.get("show_type", "")
        self.show_title = tvshow_dictionary.get("show_title", "")
        self.lastplayed = tvshow_dictionary.get("lastplayed", "")

        self.numwatched = tvshow_dictionary.get("numwatched", 0)
        self.numskipped = tvshow_dictionary.get("numskipped", 0)
        self.numondeck = tvshow_dictionary.get("numondeck", 0)

        self.episode_list = tvshow_dictionary.get("episode_list", [])

        on_deck_dictionary = tvshow_dictionary.get("OnDeck", {})
        below_deck_dictionary = tvshow_dictionary.get("BelowDeck", {})

        if not all([on_deck_dictionary, below_deck_dictionary, episode_list]):
            self.populate_from_kodi()

        self.OnDeck = self.create_episode_from_dict(on_deck_dictionary, episode_position="OnDeck")
        self.BelowDeck = self.create_episode_from_dict(
            below_deck_dictionary, episode_position="BelowDeck"
        )

    def as_dict(self):
        """ Returns the TV Show as a dictionary. This allows the show to be more
        easily pickled.
        """
        tvshow_dictionary = {}

        tvshow_dictionary["show_type"] = self.show_type
        tvshow_dictionary["showtitle"] = self.show_title
        tvshow_dictionary["lastplayed"] = self.lastplayed
        tvshow_dictionary["numwatched"] = self.numwatched
        tvshow_dictionary["numskipped"] = self.numskipped
        tvshow_dictionary["numondeck"] = self.numondeck
        tvshow_dictionary["episode_list"] = self.episode_list
        tvshow_dictionary["complete"] = self.isComplete
        tvshow_dictionary["OnDeck"] = self.OnDeck.as_dictionary()
        tvshow_dictionary["BelowDeck"] = self.BelowDeck.as_dictionary()

        return tvshow_dictionary

    def populate_from_kodi(self, *args, **kwargs):
        """ Populates the tv show episode list with data from kodi's database.
        Calling this method is, in effect, a full refresh of the TV Show.
        """

        Q.eps_query["params"]["tvshowid"] = self.showId
        raw_episodes = T.json_query(Q.eps_query)

        if "episodes" in raw_episodes:
            self.episode_list = [miniEpisode(ep) for ep in raw_episodes.get("episodes", [])]

            # Puts the episodes in order by Season-Episode
            self.episode_list.sort()

        self.setOnDeckEpisode()
        self.setBelowDeckEpisode()
        self.update_stats()

    def update_stats(self,):
        """ Updates the numwatched, numskipped, and numready for the TV Show.
        These are displayed in the GUI. 
        numwatched is the number of Episodes that have been watched
        numready is the number of episodes that can be played. For normal TV Shows
            this will be the number of unwatched episodes after the last watched,
            while for random is it merely the total number of unwatched episodes.
        numskipped is the number unwatched episodes that are not ready to be played.
            For a normal TV Show this will be the unwatched episodes before the
            last watched episode, while for random shows this will always be zero.

        These stats are passed to new LazyEpisodes, and must be updated on 
        existing ones (OnDeck and BelowDeck).
        """

        numwatched = sum(1 for x in self.episode_list if x.ep_watched_tag == "w")

        if self.show_type == "Random":
            numready = sum(1 for x in self.episode_list if x.ep_watched_tag != "w")
            numskipped = 0
        else:  # Normal TV show
            ready_episode_list = self._generateReadyList()
            numready = len(ready_episode_list)
            numskipped = sum(1 for x in self.episode_list[:idx] if x.ep_watched_tag != "w")

        properties = {"numwatched": numwatched, "numskipped": numskipped, "numready": numready}

        self.OnDeck.updateProperties(**properties)
        self.BelowDeck.updateProperties(**properties)

    def update_lastplayed(self):
        """ Updates the lastplayed attribute to be the current time, and does 
        this for the OnDeck and BelowDeck episodes as well.
        """

        self.lastplayed = T.day_conv()

        self.OnDeck.updateProperties(lastplayed=lastplayed)
        self.BelowDeck.updateProperties(lastplayed=lastplayed)

        return self

    def update_widget_position(self, widget_position, *args, **kwargs):
        """ Update the TV Shows widget position. This information gets updated
        in the OnDeck and BelowDeck episodes, with the OnDeck episode making
        the change in the Window properties automatically.
        """

        self.widget_position = widget_position
        self.OnDeck.updateProperties(widget_position=widget_position)
        self.BelowDeck.updateProperties(widget_position=widget_position)

        return self

    def update_show_type(self, show_type, *args, **kwargs):
        """ Updates the show type (normal or random) with the provided type.
        If the show type has not changed, then no actions need take place. But
        if the show type changes, we need to adjust the OnDeck and BelowDeck
        episodes, and update the stats.
        """

        if show_type != self.show_type:
            self.show_type = show_type

            self.OnDeck.updateProperties(show_type=show_type)
            self.BelowDeck.updateProperties(show_type=show_type)

            self.setOnDeckEpisode()
            self.setBelowDeckEpisode()
            self.update_stats()

        return self

    def _generateReadyList(self, episodeId=None, *args, **kwargs):
        """ Method returns a list of episodes ready to be played. This is derived
        from the episode_list and the population of episodes depends upon whether
        the TV Show is Random or Normal.
        If an episodeId is provided and the TV Show is normal then the Ready List
        will be everything past that episode.
        If an episodeId is provided as a list and the TV Show is Random, then the
        Ready List will exclude those specific episodes.
        For convenience, any single episodeId is changed to a list.
        
        Unless provided as the episodeId, the return Ready List will include
        the OnDeck and BelowDeck episodes.

        In effect, this method allows for populating the RandomPlayer via the
        Wrangler, with the Wrangler maintaining a list of episodes already added
        to the player, and calling this method to get another episode while
        providing the episodeId list.
        """

        if episodeId is None:
            episodeId_list = []

        if not isinstance(episodeId, list):
            episodeId_list = [episodeId]

        if self.show_type == "Random":
            return [
                x
                for x in self.episode_list
                if (x.ep_watched_tag != "w") & (x.ep_id not in episodeId_list)
            ]
        else:
            idx1 = max(i for i, x in enumerate(self.episode_list) if x.ep_watched_tag == "w")
            idx2 = max(i for i, x in enumerate(self.episode_list) if x.ep_id in episodeId_list)
            idx = max(idx1, idx2)
            return [self.episode_list[idx + 1 :]]

    def setOnDeckEpisode(self):
        """ Selects an episode from the episode list to be the OnDeck Episode.
        When the show is set to Random selection, the OnDeck episode can be any 
        unwatched episode.
        When the show is normal, the OnDeck episode must be the next unwatched
        episode after the last watched episode.
        """

        ready_list = self._generateReadyList()
        if not ready_list:
            self.setShowToComplete()
            return "Complete"

        # If we reach this point after a show refresh (either via a call to
        # populate_from_kodi or through the change of watched status) then the
        # show can be reactivated and included in activity by the Wrangler.
        self.isComplete = False

        if self.show_type == "Random":
            on_deck = random.choice(ready_list)
        else:  # TV Show is normal
            on_deck = ready_list[0]

        self.OnDeck = LazyEpisode(
            on_deck.ep_id,
            self.showId,
            self.lastplayed,
            self.show_title,
            self.show_type,
            self.widget_position,
            episode_position="OnDeck",
        )

    def setBelowDeckEpisode(self):
        """ Select an episode from the episode list to be the BelowDeck Episode.
        The BelowDeck episode is the one that is sitting ready to be converted
        to the OnDeck episode for quick changeover.
        When the show is Normal, this is the episode after the OnDeck episode.
        When the show is Random, this is any other unwatched episode.
        """

        ready_list = self._generateReadyList(episodeId=self.OnDeck.getProperty("EpisodeID"))
        if not ready_list:
            # If there are no more episodes, then set BelowDeck to None and
            # return a message saying so.
            self.BelowDeck = None
            return "Almost Complete"

        if self.show_type == "Random":
            below_deck = random.choice(ready_list)
        else:  # TV Show is normal
            below_deck = ready_list[0]

        self.BelowDeck = LazyEpisode(
            below_deck.ep_id,
            self.showId,
            self.lastplayed,
            self.show_title,
            self.show_type,
            self.widget_position,
            episode_position="BelowDeck",
        )

    def swapBelowDecktoOnDeck(self):
        """ Method puts the BelowDeck episode into the OnDeck slot, then sets
        a new BelowDeck episode.
        The new OnDeck episode handles updating the Window properties as soon
        as it's episode_position property is set to "OnDeck".
        """

        self.OnDeck = self.BelowDeck

        self.OnDeck.updateProperties(episode_position="OnDeck")

        self.setBelowDeckEpisode()

    def update_watched_status(self, epid, watched_status_changed_to="w"):
        """ Method updates the watched status of an episode in the episode_list.
        This will occur when the user sets an episode to watched manually in Kodi
        or when they do so in the GUI, or when a show has just been watched.

        We don't want to bother with any changes if the watched status update
        doesn't affect us, so we test whether the Ready List has changed when the
        episode watched status is updated.

        If the TV Show is Normal, then only a change in the Ready List will cause
        any change in OnDeck, etc.
        If the TV Show is Random, then the only thing that needs changing is if
        the watched status of the OnDeck or BelowDeck episodes has changed.
        """

        original_ready_list = self._generateReadyList()
        for x in self.episode_list:
            if x.ep_id == epid:
                x.ep_watched_tag = watched_status_changed_to
        new_ready_list = self._generateReadyList()

        if self.show_type == "Random":
            if self.OnDeck.getProperty("EpisodeID") == str(epid):
                self.swapBelowDecktoOnDeck()
            elif self.BelowDeck.getProperty("EpisodeID") == str(epid):
                self.setBelowDeckEpisode()

        else:
            if len(original_ready_list) != len(new_ready_list):
                self.setOnDeckEpisode()
                self.setBelowDeckEpisode()
                self.update_stats()

    def check_for_prev_unwatched(self, epid=None, *args, **kwargs):
        """ Checks for the existence of an unwatched episode prior to the 
        provided epid.
        Returns a tuple of showtitle, season, episode for display to the user
        along with a warning that they might be watching shows out of order.
        This is obviously meaningless for Random TV Shows.
        """

        if self.show_type != "Random":
            # If the episode is the OnDeck episode, don't do anything
            if self.OnDeck.getProperty("EpisodeID") != str(epid):
                # If the episode is in the Ready_List then send the warning to the user.
                for x in self.episode_list:
                    if str(x.ep_id) == str(epid):
                        return x.ep_id, self.showtitle, x.ep_season, x.ep_episode

    def setShowToComplete(self):
        """ When the show is complete, there are no more episodes to watch so
        we remove the information from the Window Properties and set the complete
        flag to True so the Wrangler skips this show in its activity.

        A future development could be to have a Kodi setting that calls the DB to
        set all episodes of the show to unwatched, and perhaps set the show type
        to Random.
        """
        self.OnDeck.updateWindowProperties(clear=True)
        self.isComplete = True

    def create_episode_from_dict(self, episode_dictionary, episode_position):
        """ Creates a new episode class from a dictionary.
        """

        episodeId = episode_dictionary.get("EpisodeID")

        new_episode = LazyEpisode(
            episodeId,
            self.showId,
            self.lastplayed,
            self.show_title,
            self.show_type,
            self.widget_position,
            episode_position,
        )

        new_episode.populate_properties_from_dict(episode_dictionary)

        return new_episode

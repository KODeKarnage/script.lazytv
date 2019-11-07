# LazyTV Modules
import lazy_queries as Q
import lazy_tools as T

import xbmcgui

PROPERTIES = [
    "File",
    "Episode",
    "Season",
    "EpisodeNo",
    "Resume",
    "PercentPlayed",
    "Runtime",
    "Premiered",
    "Rating",
    "Plot",
    "Title",
    "TVshowTitle",
    "OrderShowTitle",
    "fanart",
    "Fanart_Image",
    "thumb",
    "Backup_Image",
    "poster",
    "banner",
    "clearlogo",
    "clearart",
    "landscape",
    "characterart",
    "watched",
    "EpisodeID",
    "showId",
    "show_title",
    "show_type",
    "numwatched",
    "numskipped",
    "numready",
    "widget_position",
    "episode_position",
]


class miniEpisode(object):
    """ Takes the kodi episode data and forms it into an Episode namedtuple.
    Episodes contain the information needed to properly order the episodes
    of a TV Show.
    """

    def __init__(self, episode_details, *args, **kwargs):

        self.ep_ordering_metric = int(episode_details["season"]) * 1000000 + int(
            episode_details["episode"]
        )
        self.ep_id = episode_details["episodeid"]
        self.ep_season = int(episode_details["season"])
        self.ep_episode = int(episode_details["episode"])
        self.ep_file = episode_details["file"]
        self.ep_watched_tag = "w" if episode_details["playcount"] > 0 else "u"


class LazyEpisode(xbmcgui.ListItem):
    """ An episode is a ListItem that is kept in the eps_store of a TV Show.
    This subclass can be populated with episode information either by 
    retrieving the episode data from the database or from a supplied dictionary.
    All variables are stored as ListItem properties.
    The class includes a method to return show information in the form of a 
    dictionary for easy pickling.
    """

    def __init__(
        self,
        episodeId,
        showId,
        lastplayed,
        show_title,
        show_type,
        widget_position,
        episode_position,
        *args,
        **kwargs
    ):
        """ The Episode is initially populated with data that came from the
        parent TV Show.

        episode_position is either OnDeck or BelowDeck. When the episode is
        OnDeck, it is allowed to update the Window information.
        """
        xbmcgui.ListItem.__init__(self, *args, **kwargs)

        self.setProperty("media_type", "episode")

        self.setProperty("EpisodeID", episodeId)
        self.setProperty("showId", showId)
        self.setProperty("show_title", show_title)
        self.setProperty("show_type", show_type)

        self.setProperty("lastplayed", lastplayed)

        self.setProperty("widget_position", widget_position)

        self.WINDOW = xbmcgui.Window(10000)

        self.episode_position = episode_position

    def retrieve_details_from_kodi(self, resume_only=False):

        Q.ep_details_query["params"]["episodeid"] = self.getProperty("EpisodeID")

        kodi_episode_details = T.json_query(Q.ep_details_query)

        return kodi_episode_details.get("episodedetails", {})

    def _extract_resumePoint_resumePercent_from_kodi_data(
        self, kodi_episode_details, *args, **kwargs
    ):
        """ Produce a tuple of the resumePoint (timestamp of where to resume)
        and the resumePercent (resumePoint as a percentage of the total time
        of the file).
        """

        position = kodi_episode_details.get("resume", {}).get("position", 0)
        totaltime = kodi_episode_details.get("resume", {}).get("total", 0)
        if position and totaltime:
            resumePoint = "true"
            resumePercent = "%s%%" % int(float(position) / float(totaltime) * 100)
        else:
            resumePoint = "false"
            resumePercent = "0%"

        return resumePoint, resumePercent

    def updateProperties(self, *args, **kwargs):
        """ Method to update ListItem properties. It is possible for the setProperty
        method to just be called, but this function allows for updating a dict of
        properties all at once. It also allows for the Window data to be updated
        at the same time.
        """
        self.setProperties(kwargs)

        self.updateWindowProperties()

    def updateWindowProperties(self, clear=False, *args, **kwargs):
        """ Method handles updating the episode information in the Window
        Properties. These are used by various widgets.
        """

        if self.episode_position != "OnDeck":
            return

        window_property_map = {
            "DBID": "EpisodeID",
            "Title": "Title",
            "Episode": "Episode",
            "EpisodeNo": "EpisodeNo",
            "Season": "Season",
            "Plot": "Plot",
            "TVshowTitle": "TVshowTitle",
            "Rating": "Rating",
            "Runtime": "Runtime",
            "Premiered": "Premiered",
            "Art(thumb)": "thumb",
            "Art(tvshow.fanart)": "fanart",
            "Art(tvshow.poster)": "poster",
            "Art(tvshow.banner)": "banner",
            "Art(tvshow.clearlogo)": "clearlogo",
            "Art(tvshow.clearart)": "clearart",
            "Art(tvshow.landscape)": "landscape",
            "Art(tvshow.characterart)": "characterart",
            "Resume": "Resume",
            "PercentPlayed": "PercentPlayed",
            "File": "File",
            "lastplayed": "lastplayed",
            "Watched": "false",
        }

        if clear:
            updatefunc = self.WINDOW.clearProperty
        else:
            updatefunc = self.WINDOW.setProperty

        for marker in [self.getProperty("showId"), "widget." + self.getProperty("widget_position")]:

            for k, v in window_property_map.iteritems():
                property_key = "lazytv." + marker + "." + k
                updatefunc(property_key, self.getProperty(v))

    def _extract_season_episode_from_kodi_data(self, kodi_episode_details, *args, **kwargs):
        """ Returns properly formatted strings of the season and episode numbers, as well
        as their combined string representation. 
        Properly formatted in this context means the integers are zero padded.
        """
        season = "%.2d" % float(kodi_episode_details.get("season", 0))
        episode = "%.2d" % float(kodi_episode_details.get("episode", 0))
        episode_number = "s%se%s" % (season, episode)

        return season, episode, episode_number

    def populate_properties_from_kodi(self, kodi_episode_details, *args, **kwargs):

        season, episode, episode_number = self._extract_season_episode_from_kodi_data(
            kodi_episode_details
        )
        resumePoint, resumePercent = self._extract_resumePoint_resumePercent_from_kodi_data(
            kodi_episode_details
        )

        properties = {
            "File": kodi_episode_details.get("file", ""),
            "Episode": episode,
            "Season": season,
            "EpisodeNo": episode_number,
            "Resume": resumePoint,
            "PercentPlayed": resumePercent,
            "Runtime": int((ep_details.get("runtime", 0) / 60) + 0.5),
            "Premiered": ep_details.get("firstaired", ""),
            "Rating": str(round(float(kodi_episode_details.get("rating", 0)), 1)),
            "Plot": kodi_episode_details.get("plot", ""),
            "Title": kodi_episode_details.get("title", ""),
            "TVshowTitle": kodi_episode_details.get("showtitle", ""),
            "OrderShowTitle": T.order_name(self.TVshowTitle),
            "fanart": kodi_episode_details.get("art", {}).get("tvshow.fanart", ""),
            "Fanart_Image": kodi_episode_details.get("art", {}).get("tvshow.fanart", ""),
            "thumb": kodi_episode_details.get("art", {}).get("thumb", ""),
            "Backup_Image": kodi_episode_details.get("art", {}).get("thumb", ""),
            "poster": kodi_episode_details.get("art", {}).get("tvshow.poster", ""),
            "banner": kodi_episode_details.get("art", {}).get("tvshow.banner", ""),
            "clearlogo": kodi_episode_details.get("art", {}).get("tvshow.clearlogo", ""),
            "clearart": kodi_episode_details.get("art", {}).get("tvshow.clearart", ""),
            "landscape": kodi_episode_details.get("art", {}).get("tvshow.landscape", ""),
            "characterart": kodi_episode_details.get("art", {}).get("tvshow.characterart", ""),
        }

        self.setProperties(properties)

        # Some properties can be set at the ListItem level
        self.setIconImage(kodi_episode_details.get("art", {}).get("tvshow.poster", ""))
        self.setThumbnailImage(kodi_episode_details.get("art", {}).get("tvshow.poster", ""))
        self.setPath(kodi_episode_details.get("file", ""))
        self.setLabel(str(kodi_episode_details.get("showtitle", "")))
        self.setLabel2(kodi_episode_details.get("title", ""))

        # Very important Property
        self.setProperty("watched", "false")

        self.set_info()

        self.updateWindowProperties()

    def populate_properties_from_dict(self, dict_episode_details, *args, **kwargs):

        for k, v in dict_episode_details.iteritems():
            self.setProperty(k, v)

        # Some properties can be set at the ListItem level
        self.setIconImage(dict_episode_details.get("poster", ""))
        self.setThumbnailImage(dict_episode_details.get("poster", ""))
        self.setPath(dict_episode_details.get("File", ""))
        self.setLabel(dict_episode_details.get("TVshowTitle", ""))
        self.setLabel2(dict_episode_details.get("Title", ""))

        self.set_info()

        self.updateWindowProperties()

    def set_info(self, *args, **kwargs):
        """ Sets the built-in info for a video listitem """

        infos = {
            # "aired": 'string',
            # 'artist':      'list',
            # 'cast':        'list',
            # 'castandrole': 'list',
            # 'code':        'string',
            # 'credits':     'string',
            # "dateadded": "string",
            # 'director':    'string',
            # "duration": "string",
            "episode": self.getProperty("Episode"),
            # "genre": "string",
            # 'lastplayed':  'string',
            # 'mpaa':        'string',
            # 'originaltitle': 'string',
            # 'overlay':     'integer',
            "playcount": 0,
            "plot": "",
            # 'plotoutline': 'string',
            "premiered": self.getProperty("Premiered"),
            "rating": float(self.getProperty("Rating")),
            "season": self.getProperty("Season"),
            "sorttitle": self.getProperty("OrderShowTitle"),
            # 'status':      'string',
            # 'studio':      'string',
            # 'tagline':     'string',
            "title": self.getProperty("Title"),
            # 'top250':      'integer',
            # 'tracknumber': 'integer',
            # 'trailer':     'string',
            "tvshowtitle": self.getProperty("TVshowTitle")
            # 'votes':       'string',
            # 'writer':      'string',
            # 'year':        'integer'
        }

        self.setInfo("video", infos)

    def as_ListItem(self, *args, **kwargs):
        """ Returns the episode as an xbmcgui.ListIten.
        """
        return self

    def as_dictionary(self, *args, **kwargs):
        """ Return the episode as a dictionary of properties.
        """

        return {prop: self.getProperty(prop) for prop in PROPERTIES}



def convert_previous_settings(ignore, __setting__):
    """ Legacy from the first release of LazyTV. It ensured that the
		user-selected IGNORE list for shows to ignore is respected in
		newer versions. The last thing we want is inappropriate episodes
		showing in childrens playlist. """

    filter_genre = True if __setting__("filter_genre") == "true" else False
    filter_length = True if __setting__("filter_length") == "true" else False
    filter_rating = True if __setting__("filter_rating") == "true" else False
    filter_show = True if __setting__("filter_show") == "true" else False

    # convert the ignore list into a dict
    jkl = {}
    all_showids = []
    for ig in ignore.split("|"):
        if ig:
            k, v = ig.split(":-:")
            if k in jkl:
                jkl[k].append(v)
            else:
                jkl[k] = [v]
    if jkl:
        # create a list of permissable TV shows
        show_data = json_query(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "VideoLibrary.GetTVShows",
                "params": {"properties": ["mpaa", "genre"]},
            },
            True,
        )

        if "tvshows" in show_data and show_data["tvshows"]:
            show_data = show_data["tvshows"]

            all_showids = [x["tvshowid"] for x in show_data]

            for show in show_data:

                if filter_genre and "genre" in jkl:
                    for gen in jkl["genre"]:
                        if gen in show["genre"] and show["tvshowid"] in all_showids:
                            all_showids.remove(show["tvshowid"])

                if filter_rating and "rating" in jkl:
                    if (
                        show["mpaa"] in jkl["rating"]
                        and show["tvshowid"] in all_showids
                    ):
                        all_showids.remove(show["tvshowid"])

                if filter_show and "name" in jkl:

                    if (
                        str(show["tvshowid"]) in jkl["name"]
                        and show["tvshowid"] in all_showids
                    ):
                        all_showids.remove(show["tvshowid"])

    if all_showids:
        spec_shows = [int(x) for x in all_showids]

        # save the new list to settings
        __addon__.setSetting("selection", str(spec_shows))
        # set the filterYN to be Y
        __addon__.setSetting("filterYN", "true")
        filterYN = True

    # reset IGNORE to be null
    __addon__.setSetting("IGNORE", "")




def iStream_fix(show_id, showtitle, episode, season, WINDOW):

    # streams from iStream dont provide the showid and epid for above
    # they come through as tvshowid = -1, but it has episode no and season no and show name
    # need to insert work around here to get showid from showname, and get epid from season and episode no's
    # then need to ignore self.s['prevcheck']

    redo = True
    count = 0

    while (
        redo and count < 2
    ):  # this ensures the section of code only runs twice at most
        redo = False
        count += 1

        if show_id == -1 and showtitle and episode and season:

            raw_shows = json_query(show_request_all, True)

            if "tvshows" in raw_shows:

                for x in raw_shows["tvshows"]:

                    if x["label"] == showtitle:

                        show_id = x["tvshowid"]
                        eps_query["params"]["tvshowid"] = show_id
                        tmp_eps = json_query(eps_query, True)

                        if "episodes" in tmp_eps:

                            for y in tmp_eps["episodes"]:

                                if (
                                    fix_SE(y["season"]) == season
                                    and fix_SE(y["episode"]) == episode
                                ):

                                    ep_id = y["episodeid"]

                                    # get odlist
                                    tmp_od = ast.literal_eval(
                                        WINDOW.getProperty(
                                            "%s.%s.odlist" % ("LazyTV", show_npid)
                                        )
                                    )

                                    if show_npid in randos:

                                        tmpoff = WINDOW.getProperty(
                                            "%s.%s.offlist" % ("LazyTV", show_npid)
                                        )
                                        if tmp_off:
                                            tmp_od += ast.literal_eval(tmp_off)

                                    if ep_id not in tmp_od:

                                        Main.get_eps([show_npid])

                                        redo = True

    return False, show_npid, ep_npid
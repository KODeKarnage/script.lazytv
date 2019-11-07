import os
from ..Queries import plf

def convert_pl_to_showlist(smart_playlist_name):
    """ Extract showids from smart playlist"""

    filename = os.path.split(smart_playlist_name)[1]
    clean_path = "special://profile/playlists/video/" + filename

    # retrieve the shows in the supplied playlist, save their ids to a list
    Q.plf["params"]["directory"] = clean_path
    playlist_contents = json_query(plf, True)

    playlist_items = playlist_contents.get("files", [])

    if playlist_items:

        filtered_showids = [
            item.get("id", False)
            for item in playlist_items
            if item.get("type", False) == "tvshow"
        ]
        log(filtered_showids, "showids in playlist")
        if not filtered_showids:

            log("no tv shows in playlist")

            return "all"

        # returns the list of all and filtered shows and episodes
        return filtered_showids

    else:
        log("no files in playlist")
        return "all"

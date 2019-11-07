from .jsonquery import json_query
from ..Queries import plf
import xbmcgui

def playlist_selection_window(lang):
    """ Purpose: launch Select Window populated with smart playlists """

    raw_playlist_files = json_query(plf)

    playlist_files = raw_playlist_files.get("files", False)

    if playlist_files != None:

        plist_files = dict((x["label"], x["file"]) for x in playlist_files)

        playlist_list = plist_files.keys()

        playlist_list.sort()

        inputchoice = xbmcgui.Dialog().select(lang(32104), playlist_list)

        return plist_files[playlist_list[inputchoice]]

    else:

        return "empty"
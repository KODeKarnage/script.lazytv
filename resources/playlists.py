import xbmc
import json
import xbmcaddon
import xbmcgui

_addon_              = xbmcaddon.Addon('script.lazytv')
__addonid__          = _addon_.getAddonInfo('id')
lang             = _addon_.getLocalizedString

plf            = {"jsonrpc": "2.0","id": 1, "method": "Files.GetDirectory",         "params": {"directory": "special://profile/playlists/video/", "media": "video"}}


def json_query(query, ret):
    try:
        xbmc_request = json.dumps(query)
        result = xbmc.executeJSONRPC(xbmc_request)
        #print result
        #result = unicode(result, 'utf-8', errors='ignore')
        if ret:
            return json.loads(result)['result']
        else:
            return json.loads(result)
    except:
        return {}

def playlist_selection_window():
    ''' Purpose: launch Select Window populated with smart playlists '''

    playlist_files = json_query(plf, True)['files']

    if playlist_files != None:

        plist_files   = dict((x['label'],x['file']) for x in playlist_files)

        playlist_list =  plist_files.keys()

        playlist_list.sort()

        inputchoice = xbmcgui.Dialog().select(lang(32104), playlist_list)

        return plist_files[playlist_list[inputchoice]]
    else:
        return 'empty'



pl = playlist_selection_window()

_addon_.setSetting(id="users_spl",value=str(pl))

_addon_.openSettings()
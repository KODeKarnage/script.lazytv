
whats_playing          = {"jsonrpc": "2.0","method": "Player.GetItem",
						"params": {
							"properties": 
								["showtitle","tvshowid","episode", "season", "playcount", "runtime", "resume"]
							,"playerid": 1}
						,"id": "1"}


now_playing_details    = {"jsonrpc": "2.0",
						"method": "VideoLibrary.GetEpisodeDetails",
						"params": {
							"properties": 
								["playcount", "tvshowid"],
							"episodeid": "1"},
						"id": "1"}


ep_to_show_query       = {"jsonrpc": "2.0",
						"method": "VideoLibrary.GetEpisodeDetails",
						"params": {
							"properties": 
								["lastplayed","tvshowid"],
							"episodeid": "1"}
						,"id": "1"}


prompt_query           = {"jsonrpc": "2.0",
						"method": "VideoLibrary.GetEpisodeDetails",
						"params": {
							"properties": 
								["season","episode","showtitle","tvshowid"],
							"episodeid": "1"},
						"id": "1"}


show_request           = {"jsonrpc": "2.0",
						"method": "VideoLibrary.GetTVShows",
						"params": {
							"filter": 
								{"field": "playcount","operator": "is","value": "0"},
							"properties": 
								["genre","title","playcount","mpaa","watchedepisodes","episode","thumbnail"]}
						,"id": "1"}


all_show_ids	       = {"jsonrpc": "2.0",
						"method": "VideoLibrary.GetTVShows",
						"params": {
							"properties": 
								["title", "lastplayed"]},
						"id": "1"}


show_request_lw        = {"jsonrpc": "2.0",
						"method": "VideoLibrary.GetTVShows",
						"params": {
							"filter": 
								{"field": "playcount", "operator": "is", "value": "0" },
							"properties": 
								["lastplayed"],
							"sort":
								{"order": "descending", "method":"lastplayed"} }
						,"id": "1" }


eps_query              = {"jsonrpc": "2.0",
						"method": "VideoLibrary.GetEpisodes",
						"params": {
							"properties": 
								["season","episode","resume","playcount","tvshowid","lastplayed","file"],
							"tvshowid": "1"},
						"id": "1"}


ep_details_query       = {"jsonrpc": "2.0",
						"method": "VideoLibrary.GetEpisodeDetails",
						"params": {
							"properties": 
								["title","playcount","plot","season","episode","showtitle","file",
									"lastplayed","rating","resume","art","streamdetails","firstaired",
										"runtime","tvshowid"],
								"episodeid": 1},
						"id": "1"}


seek                   = {"jsonrpc": "2.0",
						"method": "Player.Seek",
						"params": {
							"playerid": 1, "value": 0 },
						"id": 1}


plf                    = {"jsonrpc": "2.0",
						"method": "Files.GetDirectory",
						"params": {
							"directory": "special://profile/playlists/video/", "media": "video"},
						"id": 1}


add_this_ep            = {'jsonrpc': '2.0',
						"method": 'Playlist.Add',
						"params": {
							'item' : {
								'episodeid' : 'placeholder' },
							'playlistid' : 1},
						'id': 1}

pause                   = {"jsonrpc":"2.0",
						"method":"Player.PlayPause",
						"params":{
							"playerid" : 1,
							"play" : "false"},
						"id":1}


unpause                 = {"jsonrpc":"2.0",
						"method":"Player.PlayPause",
						"params":{
							"playerid" : 1,
							"play" : "true"},
						"id":1}


clear_playlist          = {"jsonrpc": "2.0",
						"method": "Playlist.Clear",
						"params": {
							"playlistid": 1},
						"id": 1}						
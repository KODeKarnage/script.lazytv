
show_request = {
    "jsonrpc": "2.0",
    "method": "VideoLibrary.GetTVShows",
    "params": {
        "filter": {
            "field": "playcount",
            "operator": "is",
            "value": "0"
        },
        "properties": [
            "genre",
            "title",
            "playcount",
            "mpaa",
            "watchedepisodes",
            "episode",
            "thumbnail"
        ]
    },
    "id": "1"
}

plf = {
    "jsonrpc": "2.0",
    "method": "Files.GetDirectory",
    "params": {
        "directory": "placeholder",
        "media": "video"
    },
    "id": 1
}

clear_playlist = {
    "jsonrpc": "2.0",
    "method": "Playlist.Clear",
    "params": {
        "playlistid": 1
    },
    "id": "1"
}

eps_query = {
    "jsonrpc": "2.0",
    "method": "VideoLibrary.GetEpisodes",
    "params": {
        "properties": [
            "season",
            "episode",
            "runtime",
            "resume",
            "playcount",
            "tvshowid",
            "lastplayed",
            "file"
        ],
        "tvshowid": "1"
    },
    "id": "1"
}

ep_to_show_query = {
    "jsonrpc": "2.0",
    "method": "VideoLibrary.GetEpisodes",
    "params": {
        "properties": [
            "tvshowid"
        ],
        "episodeid": "1"
    },
    "id": "1"
}

seek = {
    "jsonrpc": "2.0",
    "method": "Player.Seek",
    "params": {
        "playerid": 1,
        "value": 0
    },
    "id": 1
}

play_command = {
    "jsonrpc": "2.0",
    "method": "Player.Open",
    "params": {
        "item": {
            "episodeid": "1"
        },
        "options": {
            "resume": "True"
        }
    },
    "id": 1
}

grab_all_shows = {
    "jsonrpc": "2.0",
    "method": "VideoLibrary.GetTVShows",
    "params": {
        "properties": [
            "genre",
            "title",
            "mpaa",
            "thumbnail"
        ]
    },
    "id": "allTVShows"
}

grab_genres = {
    "jsonrpc": "2.0",
    "method": "VideoLibrary.GetGenres",
    "params": {
        "type": "tvshow"
    },
    "id": "1"
}

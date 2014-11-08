


def random_playlist(population):
	global movies
	global movieweight

	#get the showids and such from the playlist
	stored_data_filtered = process_stored(population)

	log('random_playlist_started',reset = True)

	#clear the existing playlist
	json_query(clear_playlist, False)

	added_ep_dict   = {}
	count           = 0
	movie_list      = []


	if movies or moviesw:

		if movies and moviesw:
			mov = json_query(get_moviesa, True)
		elif movies:
			mov = json_query(get_movies, True)
		elif moviesw:
			mov = json_query(get_moviesw, True)

		movies = True

		if 'movies' in mov and mov['movies']:
			movie_list = [x['movieid'] for x in mov['movies']]
			log('all movies = ' + str(movie_list))
			if not movie_list:
				movies = False
			else:
				random.shuffle(movie_list)
		else:
			movies = False

	storecount = len(stored_data_filtered)
	moviecount = len(movie_list)

	if noshow:
		movieweight = 0.0
		stored_data_filtered = []

	if movieweight != 0.0:
		movieint = min(max(int(round(storecount * movieweight,0)), 1), moviecount)
	else:
		movieint = moviecount

	if movies:
		movie_list = movie_list[:movieint]
		log('truncated movie list = ' + str(movie_list))

	candidate_list = ['t' + str(x[1]) for x in stored_data_filtered] + ['m' + str(x) for x in movie_list]
	random.shuffle(candidate_list)

	watch_partial_now = False

	if start_partials:

		if candidate_list:
			red_candy = [int(x[1:]) for x in candidate_list if x[0] == 't']
		else:
			red_candy = []

		lst = []

		for showid in red_candy:

			if WINDOW.getProperty("%s.%s.Resume" % ('LazyTV',showid)) == 'true':
				temp_ep = WINDOW.getProperty("%s.%s.EpisodeID" % ('LazyTV',showid))
				if temp_ep:
					lst.append({"jsonrpc": "2.0","method": "VideoLibrary.GetEpisodeDetails","params": {"properties": ["lastplayed","tvshowid"],"episodeid": int(temp_ep)},"id": "1"})

		lwlist = []

		if lst:

			xbmc_request = json.dumps(lst)
			result = xbmc.executeJSONRPC(xbmc_request)

			if result:
				reslist = ast.literal_eval(result)
				for res in reslist:
					if 'result' in res:
						if 'episodedetails' in res['result']:
							lwlist.append((res['result']['episodedetails']['lastplayed'],res['result']['episodedetails']['tvshowid']))

			lwlist.sort(reverse=True)

		if lwlist:

			log(lwlist, label="lwlist = ")

			R = candidate_list.index('t' + str(lwlist[0][1]))

			watch_partial_now = True

			log(R,label="R = ")




	while count < length and candidate_list: 		#while the list isnt filled, and all shows arent abandoned or movies added
		log('candidate list = ' + str(candidate_list))
		multi = False

		if start_partials and watch_partial_now:
			watch_partial_now = False
		else:
			R = random.randint(0, len(candidate_list) -1 )	#get random number

		log('R = ' + str(R))

		curr_candi = candidate_list[R][1:]
		candi_type = candidate_list[R][:1]

		if candi_type == 't':
			log('tvadd attempt')

			if curr_candi in added_ep_dict.keys():
				log(str(curr_candi) + ' in added_shows')
				if multipleshows:		#check added_ep list if multiples allowed
					multi = True
					tmp_episode_id, tmp_details = next_show_engine(showid=curr_candi,epid=added_ep_dict[curr_candi][3],eps=added_ep_dict[curr_candi][2],Season=added_ep_dict[curr_candi][0],Episode=added_ep_dict[curr_candi][1])
					if tmp_episode_id == 'null':
						tg = 't' + str(curr_candi)
						if tg in candidate_list:
							candidate_list.remove('t' + str(curr_candi))
							log(str(curr_candi) + ' added to abandonded shows (no next show)')
						continue
				else:
					continue
			else:
				log(str(curr_candi) + ' not in added_showss')
				tmp_episode_id = int(WINDOW.getProperty("%s.%s.EpisodeID" % ('LazyTV',curr_candi)))
				if not multipleshows:		#check added_ep list if multiples allowed, if not then abandon the show
					tg = 't' + str(curr_candi)
					if tg in candidate_list:
						candidate_list.remove('t' + str(curr_candi))
					log(str(curr_candi) + ' added to abandonded shows (no multi)')


			if not premieres:
				if WINDOW.getProperty("%s.%s.EpisodeNo" % ('LazyTV',curr_candi)) == 's01e01':	#if desired, ignore s01e01
					tg = 't' + str(curr_candi)
					if tg in candidate_list:
						candidate_list.remove('t' + str(curr_candi))
					log(str(curr_candi) + ' added to abandonded shows (premieres)')
					continue

			#add episode to playlist
			if tmp_episode_id:
				add_this_ep['params']['item']['episodeid'] = int(tmp_episode_id)
				json_query(add_this_ep, False)
				log('episode added = ' + str(tmp_episode_id))
			else:
				tg = 't' + str(curr_candi)
				if tg in candidate_list:
					candidate_list.remove('t' + str(curr_candi))
				continue

			#add episode to added episode dictionary
			if not multi:
				if multipleshows:
					if curr_candi in randos:
						eps_list = ast.literal_eval(WINDOW.getProperty("%s.%s.odlist" % ('LazyTV',curr_candi))) + ast.literal_eval(WINDOW.getProperty("%s.%s.offlist" % ('LazyTV',curr_candi)))
					else:
						eps_list = ast.literal_eval(WINDOW.getProperty("%s.%s.odlist" % ('LazyTV',curr_candi)))
					added_ep_dict[curr_candi] = [WINDOW.getProperty("%s.%s.Season" % ('LazyTV', curr_candi)), WINDOW.getProperty("%s.%s.Episode" % ('LazyTV', curr_candi)),eps_list,WINDOW.getProperty("%s.%s.EpisodeID" % ('LazyTV', curr_candi))]
				else:
					added_ep_dict[curr_candi] = ''
			else:
				added_ep_dict[curr_candi] = [tmp_details[0],tmp_details[1],tmp_details[2],tmp_details[3]]

		elif candi_type == 'm':
			#add movie to playlist
			log('movieadd')
			add_this_movie['params']['item']['movieid'] = int(curr_candi)
			json_query(add_this_movie, False)
			candidate_list.remove('m' + str(curr_candi))
		else:
			count = 99999

		count += 1

	WINDOW.setProperty("%s.playlist_running"	% ('LazyTV'), 'true')		# notifies the service that a playlist is running
	WINDOW.setProperty("LazyTV.rando_shuffle", 'true')						# notifies the service to re-randomise the randos

	xbmc.Player().play(xbmc.PlayList(1))
	#xbmc.executebuiltin('ActivateWindow(MyVideoPlaylist)')
	log('random_playlist_End')


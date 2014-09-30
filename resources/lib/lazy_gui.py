
class yGUI(xbmcgui.WindowXMLDialog):

	def __init__(self, strXMLname, strFallbackPath, strDefaultName, data=[]):
		self.data = data
		self.selected_show = 'null'
		yGUI.context_order = 'null'
		yGUI.multiselect = False
		self.load_items = True
		WINDOW.setProperty('runninglist', '') 


	def onInit(self):
		if self.load_items:
			self.load_items = False
			log('window_init', reset = True)

			if skin == 0: 
				self.ok = self.getControl(5)
				self.ok.setLabel(lang(32105))

				self.hdg = self.getControl(1)
				self.hdg.setLabel('LazyTV')
				self.hdg.setVisible(True)

				self.ctrl6failed = False

				try:
					self.name_list = self.getControl(6)
					self.x = self.getControl(3)
					self.x.setVisible(False)
					self.ok.controlRight(self.name_list)

				except:
					self.ctrl6failed = True  #for some reason control3 doesnt work for me, so this work around tries control6
					self.close()             #and exits if it fails, CTRL6FAILED then triggers a dialog.select instead '''

			else:
				self.name_list = self.getControl(655)

			self.now = time.time()

			self.count = 0

			log('this is the data the window is using = ' + str(self.data))

			for i, show in enumerate(self.data):

				if self.count == 1000 or (limitshows == True and i == window_length):
					break

				self.pctplyd  = WINDOW.getProperty("%s.%s.PercentPlayed" % ('LazyTV', show[1]))

				if show[0] == 0:
					self.lw_time = lang(32112)
				else:
					self.gap = round((self.now - show[0]) / 86400.0, 1)
					if self.gap == 1.0:
						self.lw_time = ' '.join([str(self.gap),lang(32113)])
					else:
						self.lw_time = ' '.join([str(self.gap),lang(32114)])

				if self.pctplyd == '0%' and skin == 0:
					self.pct = ''
				elif self.pctplyd == '0%':
					self.pct = self.pctplyd
				else:
					self.pct = self.pctplyd + ', '

				self.label2 = self.pct if skin != 0 else self.pct + self.lw_time

				self.poster = WINDOW.getProperty("%s.%s.Art(tvshow.poster)" % ('LazyTV', show[1]))
				self.thumb  = WINDOW.getProperty("%s.%s.Art(thumb)" % ('LazyTV', show[1]))
				self.eptitle = WINDOW.getProperty("%s.%s.title" % ('LazyTV', show[1]))
				self.plot = WINDOW.getProperty("%s.%s.Plot" % ('LazyTV', show[1]))
				self.season = WINDOW.getProperty("%s.%s.Season" % ('LazyTV', show[1]))
				self.episode = WINDOW.getProperty("%s.%s.Episode" % ('LazyTV', show[1]))
				self.EpisodeID = WINDOW.getProperty("%s.%s.EpisodeID" % ('LazyTV', show[1]))
				self.file = WINDOW.getProperty("%s.%s.file" % ('LazyTV', show[1]))

				if skin != 0:
					self.title  = WINDOW.getProperty("%s.%s.TVshowTitle" % ('LazyTV', show[1]))
					self.fanart = WINDOW.getProperty("%s.%s.Art(tvshow.fanart)" % ('LazyTV', show[1]))
					self.numwatched = WINDOW.getProperty("%s.%s.CountWatchedEps" % ('LazyTV', show[1]))
					self.numondeck = WINDOW.getProperty("%s.%s.CountonDeckEps" % ('LazyTV', show[1]))
					try:
						self.numskipped = str(int(WINDOW.getProperty("%s.%s.CountUnwatchedEps" % ('LazyTV', show[1]))) - int(WINDOW.getProperty("%s.%s.CountonDeckEps" % ('LazyTV', show[1]))))
					except:
						self.numskipped = '0'
					self.tmp = xbmcgui.ListItem(label=self.title, label2=self.eptitle, thumbnailImage = self.poster)
					self.tmp.setProperty("Fanart_Image", self.fanart)
					self.tmp.setProperty("Backup_Image", self.thumb)
					self.tmp.setProperty("numwatched", self.numwatched)
					self.tmp.setProperty("numondeck", self.numondeck)
					self.tmp.setProperty("numskipped", self.numskipped)
					self.tmp.setProperty("lastwatched", self.lw_time)
					self.tmp.setProperty("percentplayed", self.pctplyd)
					self.tmp.setProperty("watched",'false')

				else:
					self.title  = ''.join([WINDOW.getProperty("%s.%s.TVshowTitle" % ('LazyTV', show[1])),' ', WINDOW.getProperty("%s.%s.EpisodeNo" % ('LazyTV', show[1]))])
					self.tmp = xbmcgui.ListItem(label=self.title, label2=self.label2, thumbnailImage = self.poster)

				self.tmp.setProperty("file",self.file)
				self.tmp.setProperty("EpisodeID",self.EpisodeID)

				# self.tmp.setProperty("season", self.season)
				# self.tmp.setProperty("episode", self.episode)
				# self.tmp.setProperty("plot", self.plot)

				self.tmp.setInfo('video',{'season': self.season, "episode": self.episode,'plot': self.plot, 'title':self.eptitle})

				self.tmp.setLabel(self.title)
				self.tmp.setIconImage(self.poster)

				self.name_list.addItem(self.tmp)
				self.count += 1

			#self.ok.controlRight(self.name_list)
			self.setFocus(self.name_list)

			log('window_init_End')


	def onAction(self, action):
		contextagogone = False

		actionID = action.getId()
		
		if (actionID in (10, 92)):
			log('closing due to action')
			self.load_show_id = -1
			global stay_puft
			stay_puft = False
			self.close()

		elif actionID in [117] and not contextagogone:
			contextagogone = True
			log(actionID)
			log('context menu via action')
	
			self.pos    = self.name_list.getSelectedPosition()

			myContext = contextwindow('contextwindow.xml', __scriptPath__, 'Default')

			myContext.doModal()

			if myContext.contextoption == 110:
				'''toggle'''
				log('multiselect toggled')
				self.toggle_multiselect()

			elif myContext.contextoption == 120:
				'''playsel'''
				log('play selection')
				self.play_selection()

			elif myContext.contextoption == 130:
				'''playfrom'''
				log('play from here')
				self.play_from_here()
			
			elif myContext.contextoption == 140:
				'''export'''
				log('export selection')
				self.export_selection()
			
			elif myContext.contextoption == 150:
				'''markwatched'''
				log('toggle watched')
				self.toggle_watched()
			
			elif myContext.contextoption == 160:
				'''ignore'''
				pass
			
			elif myContext.contextoption == 170:
				'''update library'''
				self.update_library()
			
			elif myContext.contextoption == 180:
				'''refresh'''
				self.refresh()

			log('context button: ' + str(myContext.contextoption))

			del myContext


	def onClick(self, controlID):

		contextagogone = False

		if controlID == 5:
			self.load_show_id = -1
			global stay_puft
			stay_puft = False
			self.close()

		else:
			self.pos    = self.name_list.getSelectedPosition()

			if yGUI.multiselect == False:
				self.playid = self.data[self.pos][2]

				self.selected_show = int(self.playid)
				log('setting epid = ' + str(self.selected_show))
				global play_now
				play_now = True
				self.close()

			else:
				selection = self.name_list.getSelectedItem()
				if selection.isSelected():
					selection.select(False)
					log(str(self.pos) + ' toggled off')
				else:
					selection.select(True)
					log(str(self.pos) + ' toggled on')


	def update_library(self):

		xbmc.executebuiltin('UpdateLibrary(video)') 


	def toggle_multiselect(self):
		if yGUI.multiselect:
			yGUI.multiselect = False

			for itm in range(self.name_list.size()):
				self.name_list.getListItem(itm).select(False)

		else:
			yGUI.multiselect = True


	def play_selection(self):
		self.selected_show = []
		self.pos    = self.name_list.getSelectedPosition()
		for itm in range(self.name_list.size()):
			if self.name_list.getListItem(itm).isSelected() or itm == self.pos:
				self.selected_show.append(self.data[itm][2])
		global play_now
		play_now = True
		self.close()        


	def play_from_here(self):
		self.pos    = self.name_list.getSelectedPosition()
		self.selected_show = []
		for itm in range(self.pos,self.name_list.size()):
			self.selected_show.append(self.data[itm][2])
		global play_now
		play_now = True
		self.close()            


	def toggle_watched(self):
		log('watch toggling')
		self.pos    = self.name_list.getSelectedPosition()
		q_batch = []
		count = 0
		for itm in range(self.name_list.size()):
			count += 1
			if itm == self.pos: 
				EpID = self.name_list.getListItem(itm).getProperty('EpisodeID')
				log(EpID)
				if EpID:
					if skin != 0:
						if self.name_list.getListItem(itm).getProperty('watched') == 'false':
							log('toggling from unwatched to watched')
							self.name_list.getListItem(itm).setProperty("watched",'true')

					tmp = mark_as_watched % (int(EpID),1)
					q_batch.append(ast.literal_eval(tmp))
		log(q_batch)
		T.json_query(Q.q_batch, False)


	def export_selection(self):
		self.pos    = self.name_list.getSelectedPosition()
		log(self.pos, label="exporting position")
		self.export_list = ''
		for itm in range(self.name_list.size()):
			log(self.name_list.getListItem(itm).isSelected())
			if self.name_list.getListItem(itm).isSelected() or itm == self.pos:
				filename = self.name_list.getListItem(itm).getProperty('file')
				if self.export_list:
					self.export_list = ''.join([self.export_list,':-exporter-:',filename])
				else:
					self.export_list = filename

		log(self.export_list, label='export list sent from LazyTV')
		script = os.path.join(__resource__,'episode_exporter.py')
		xbmc.executebuiltin('RunScript(%s,%s)' % (script,self.export_list)  ) 
		self.selected_show = []


	def refresh(self):
		log('refresh called')
		global refresh_now
		refresh_now = True
		self.close()


class contextwindow(xbmcgui.WindowXMLDialog):

	def onInit(self):
		self.contextoption = '' 

		log('init multiselect ' + str(yGUI.multiselect))
		if yGUI.multiselect:
			self.getControl(110).setLabel(lang(32200))
			self.getControl(120).setLabel(lang(32202))
			self.getControl(140).setLabel(lang(32203))
		else:
			self.getControl(110).setLabel(lang(32201))
			self.getControl(120).setLabel(lang(32204))
			self.getControl(140).setLabel(lang(32205))

		self.getControl(130).setLabel(lang(32206))
		self.getControl(150).setLabel(lang(32207)) # go to Show in Library?
		#self.getControl(160).setLabel('Ignore Show')    # open show info?
		self.getControl(170).setLabel(lang(32208))
		self.getControl(180).setLabel(lang(32209))

		self.setFocus(self.getControl(110))


	def onClick(self, controlID):

		self.contextoption = controlID

		if controlID == 110:
			if self.getControl(110).getLabel() == lang(32200):
				self.getControl(110).setLabel(lang(32201))
				xbmc.sleep(500)
			else:
				self.getControl(110).setLabel(lang(32200))
				xbmc.sleep(500)

		self.close()

#!/usr/bin/python
# -*- coding: utf-8 -*-

#  Copyright (C) 2013 KodeKarnage
#
#  This Program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2, or (at your option)
#  any later version.
#
#  This Program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with XBMC; see the file COPYING.  If not, write to
#  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
#  http://www.gnu.org/copyleft/gpl.html

'''
#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
#@@@@@@@@@@
#@@@@@@@@@@ - allow for next ep notification in LazyTV smartplaylist READY FOR TESTING
#@@@@@@@@@@ - suppress notification at start up READY FOR TESTING
#@@@@@@@@@@ - improve handling of specials
#@@@@@@@@@@ - improve refreshing of LazyTV Show Me window
#@@@@@@@@@@
#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@'''

# XBMC modules
import xbmc
import xbmcaddon
import xbmcgui

# Standard Library Modules
import ast
import datetime
import json
import os
import threading

# LazyTV Modules
import lazy_queries 	as Q
import lazy_tools   	as T
from   lazy_logger 		import LazyLogger
from   lazy_listitem 	import LazyListItem

# addon structure variables
__addon__               = xbmcaddon.Addon()
__addonversion__        = tuple([int(x) for x in __addon__.getAddonInfo('version').split('.')])
__scriptPath__          = __addon__.getAddonInfo('path')


class LazyList(threading.Thread):
	''' A thread to instantiate and launch the gui window. '''

	def __init__(self, xmlfile, __scriptPath__, epitems, settings, log, lang):

		threading.Thread.__init__(self)	
		self.wait_evt = threading.Event()

		self.s = settings
		self.log  = log 
		self.lang = lang

		# variable to keep the window live until it is exited (if the user want this)
		self.stay_puft = self.s.get('skin_return', False)

		# variable to force a pass through the while loop
		self.first_entry = True

		# convert all the lazy_episodes into list items, using the LazyListItem class
		self.listitems = self.convert_LzEps_to_LzItms(epitems)

		# process the order and rando inclusion of the provided list items
		self.process_listitems()

		# instantiate the gui
		self.gui = LazyListGui(xmlfile, __scriptPath__, 'Default', parent=self, listitems=self.listitems, settings=settings, log=self.log, lang=self.lang)

		# player to track if something is playing
		self.gui_player = LazyListPlayer(parent = self)

		self.item_is_playing = False


	def convert_LzEps_to_LzItms(self, epitems):
		''' convert all the lazy_episodes into list items, using the LazyListItem class '''
		
		LLI = [(LazyListItem(), lazy_episode) for lazy_episode in epitems]

		return [ep_pair[0].merge(ep_pair[1]) for ep_pair in LLI if ep_pair[1] is not None]


	def update_GUI(self, epitems):
		''' Updates the GUI with the latest information. '''

		self.log('Updating gui data')

		self.listitems = self.convert_LzEps_to_LzItms(epitems)
		self.process_listitems()

		self.gui.listitems = self.listitems


	def process_listitems(self):
		''' Puts the listitems in a specific order, as determined by the user.
				0 "Show Name"
				1 "Last Watched"
				2 "# Unwatched Episodes"
				3 "# Watched Episodes"
				4 "Season"

			Excludes random shows if the user doesnt want them. '''

		order 		= self.s['sort_by']
		reverse 	= self.s['sort_reverse']

		if self.s['excl_randos']:	self.listitems = filter(lambda x: x.show_type != 'randos', self.listitems)

		if order == 0:

			self.listitems = sorted(self.listitems, key= lambda x: x.OrderShowTitle, reverse=reverse)

		elif order == 1:

			self.listitems = sorted(self.listitems, key= lambda x: x.lastplayed, reverse=reverse)

		elif order == 2:

			self.listitems = sorted(self.listitems, key= lambda x: x.stats[3], reverse=reverse)

		elif order == 3:

			self.listitems = sorted(self.listitems, key= lambda x: x.stats[0], reverse=reverse)

		elif order == 4:

			self.listitems = sorted(self.listitems, key= lambda x: x.Season, reverse=reverse)			


	def run(self):
		''' Displays the gui modal '''


		while any([all([self.stay_puft, not xbmc.abortRequested]), self.first_entry]):

			self.first_entry = False

			# loop to catch process when item is playing
			if self.item_is_playing:
				xbmc.sleep(100)
				continue
			
			self.gui.doModal()

			# the refresh function in the GUI changes the self.first_entry variable if the user want to
			# refresh the window. This will ensure the window is closed and then reopened.
			if self.first_entry:
				self.first_entry = False
				continue

			play_this = self.gui.selected_show

			if all([play_this, play_this != 'null', self.gui.play_now]):
				self.log('play_this not null, and play_now')

				self.gui.play_now = False
				# this fix clears the playlist, adds the episode to the playlist, and then starts the playlist
				# it is needed because .strms will not start if using the executeJSONRPC method

				# WINDOW.setProperty("%s.playlist_running"    % ('LazyTV'), 'listview')

				T.json_query(Q.clear_playlist)

				try:
					for ep in play_this:
						Q.add_this_ep['params']['item'] = {'episodeid': int(ep)}
						T.json_query(Q.add_this_ep)
				except:
					Q.add_this_ep['params']['item'] = {'episodeid': int(play_this)}
					T.json_query(Q.add_this_ep)

				xbmc.sleep(50)
				self.gui_player.play(xbmc.PlayList(1))
				xbmc.executebuiltin('ActivateWindow(12005)')
				self.gui.play_this = 'null'
				self.item_is_playing = True

		xbmc.sleep(500)


	def stop(self):

		del self.gui.myContext
		del self.gui
		del self.gui_player


class LazyListPlayer(xbmc.Player):

	def __init__(self, parent, *args, **kwargs):
		xbmc.Player.__init__(self)
		self.parent = parent

	def onPlayBackStarted(self):
		self.parent.item_is_playing = True

	def onPlayBackStopped(self):
		self.onPlayBackEnded()

	def onPlayBackEnded(self):
		self.parent.item_is_playing = False


class LazyListGui(xbmcgui.WindowXMLDialog):

	def __init__(self, strXMLname, strFallbackPath, strDefaultName, parent, listitems, settings, log, lang):
		self.parent 	= parent
		self.listitems 	= listitems
		self.s 			= settings
		self.log 		= log 
		self.lang 		= lang

		self.selected_show = 'null'
		self.play_now = False
		self.multiselect = False
		self.myContext = LazyContextWindow('script-lazytv-contextwindow.xml', strFallbackPath, 'Default', parent=self)


	def onInit(self):

		self.log('window_init')

		# if the skin is the default xbmc list window, then relabel the controls
		if self.s['skinorno'] == 0: 
			self.ok = self.getControl(5)
			self.ok.setLabel(self.lang(32105))

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
				self.close()             #and exits if it fails, CTRL6FAILED then triggers a Dialog.select instead '''

		else:
			self.name_list = self.getControl(655)

		self.load_data(self.listitems)


	def load_data(self, new_listitems):
		''' Loads listitems into the appropriate list control '''

		self.log('Loading data into addon gui')

		# clear the existing listitems
		self.name_list.reset()

		# add the new_listitems to the namelist control
		for i, listitem in enumerate(new_listitems):

			if listitem == None:
				continue

			# abort if there are too many shows, or the desired window length is reached
			if i == 1000 or (self.s.get('limitshows', False) == True and i == self.s.get('window_length', -1)):
				break

			# change the label if the default view is selected
			if self.s['skinorno'] == 0:

				listitem.label  = ' '.join([listitem.TVshowTitle, listitem.EpisodeNo])
				listitem.label2 = listitem.PercentPlayed if self.s['skinorno'] != 0 else str(listitem.PercentPlayed) + str(listitem.lastplayed)

			else:

				listitem.label  = listitem.TVshowTitle
				listitem.label2 = listitem.Title				

			# add this item to the name list control
			self.name_list.addItem(listitem)

		#self.ok.controlRight(self.name_list)
		self.setFocus(self.name_list)

		self.log('window_init_End')


	def onAction(self, action):
		contextagogone = False

		actionID = action.getId()
		
		if (actionID in (10, 92)):
			self.log('closing due to action')
			self.parent.stay_puft = False
			self.close()

		elif actionID in [117] and not contextagogone:
			# open lazy_context window

			contextagogone = True
			self.log(actionID)
			self.log('context menu via action')
	
			self.pos = self.name_list.getSelectedPosition()

			self.myContext.doModal()

			if self.myContext.contextoption == 110:
				'''toggle'''
				self.log('multiselect toggled')
				self.toggle_multiselect()

			elif self.myContext.contextoption == 120:
				'''playsel'''
				self.log('play selection')
				self.play_selection()

			elif self.myContext.contextoption == 130:
				'''playfrom'''
				self.log('play from here')
				self.play_from_here()
			
			elif self.myContext.contextoption == 140:
				'''export'''
				self.log('export selection')
				self.export_selection()
			
			elif self.myContext.contextoption == 150:
				'''markwatched'''
				self.log('toggle watched')
				self.toggle_watched()
			
			elif self.myContext.contextoption == 160:
				'''ignore'''
				pass
			
			elif self.myContext.contextoption == 170:
				'''update library'''
				self.update_library()
			
			elif self.myContext.contextoption == 180:
				'''refresh'''
				self.refresh()

			self.log('context button: ' + str(self.myContext.contextoption))


	def onClick(self, controlID):

		contextagogone = False

		if controlID == 5:
			self.parent.stay_puft = False
			self.close()

		else:
			self.pos    = self.name_list.getSelectedPosition()

			if self.multiselect == False:
				self.playid = self.listitems[self.pos].EpisodeID

				self.selected_show = int(self.playid)
				self.log('setting epid = ' + str(self.selected_show))
				self.play_now = True
				self.close()

			else:
				selection = self.name_list.getSelectedItem()
				if selection.isSelected():
					selection.select(False)
					self.log(str(self.pos) + ' toggled off')
				else:
					selection.select(True)
					self.log(str(self.pos) + ' toggled on')


	def update_library(self):

		xbmc.executebuiltin('UpdateLibrary(video)') 
		# self.parent.first_entry = True
		# self.close()


	def toggle_multiselect(self):
		if self.multiselect:
			self.multiselect = False

			for itm in range(self.name_list.size()):
				self.name_list.getListItem(itm).select(False)

		else:
			self.multiselect = True


	def play_selection(self):
		self.selected_show = []
		self.pos = self.name_list.getSelectedPosition()
		for itm in range(self.name_list.size()):
			if self.name_list.getListItem(itm).isSelected() or itm == self.pos:
				self.selected_show.append(self.listitems[itm].EpisodeID)
		self.play_now = True
		self.close()        


	def play_from_here(self):
		self.pos    = self.name_list.getSelectedPosition()
		self.selected_show = []
		for itm in range(self.pos,self.name_list.size()):
			self.selected_show.append(self.listitems[itm].EpisodeID)
		self.play_now = True
		self.close()            


	def toggle_watched(self):
		self.log('watch toggling')
		self.pos    = self.name_list.getSelectedPosition()
		q_batch = []
		count = 0
		for itm in range(self.name_list.size()):
			count += 1
			if itm == self.pos: 
				EpID = self.name_list.getListItem(itm).EpisodeID
				self.log(EpID)
				if EpID:
					if self.s['skinorno'] != 0:
						if self.name_list.getListItem(itm).getProperty('watched') == 'false':
							self.log('toggling from unwatched to watched')
							self.name_list.getListItem(itm).setProperty("watched",'true')

					tmp = mark_as_watched % (int(EpID),1)
					q_batch.append(ast.literal_eval(tmp))
		self.log(q_batch)
		T.json_query(Q.q_batch, False)


	def export_selection(self):
		self.pos    = self.name_list.getSelectedPosition()
		self.log(self.pos, label="exporting position")
		self.export_list = ''
		for itm in range(self.name_list.size()):

			self.log(self.name_list.getListItem(itm).isSelected())

			if self.name_list.getListItem(itm).isSelected() or itm == self.pos:
				filename = self.name_list.getListItem(itm).File
				if self.export_list:
					self.export_list = ''.join([self.export_list,':-exporter-:',filename])
				else:
					self.export_list = filename

		self.log(self.export_list, label='export list sent from LazyTV')
		script = os.path.join(__resource__,'episode_exporter.py')
		xbmc.executebuiltin('RunScript(%s,%s)' % (script,self.export_list)  ) 
		self.selected_show = []


	def refresh(self):
		self.log('refresh called')
		self.parent.first_entry = True
		self.close()


class LazyContextWindow(xbmcgui.WindowXMLDialog):
	''' A context window for use within lazy_gui '''

	def __init__(self, strXMLname, strFallbackPath, strDefaultName, parent):
		self.parent = parent

	def onInit(self):
		self.parent.contextoption = '' 

		self.log('init multiselect ' + str(self.parent.multiselect))

		# if multiselect is active, then change the wording in the context menu
		if self.parent.multiselect:
			self.getControl(110).setLabel(self.lang(32200))
			self.getControl(120).setLabel(self.lang(32202))
			self.getControl(140).setLabel(self.lang(32203))
		else:
			self.getControl(110).setLabel(self.lang(32201))
			self.getControl(120).setLabel(self.lang(32204))
			self.getControl(140).setLabel(self.lang(32205))

		self.getControl(130).setLabel(self.lang(32206))
		self.getControl(150).setLabel(self.lang(32207)) # go to Show in Library?
		#self.getControl(160).setLabel('Ignore Show')    # open show info?
		self.getControl(170).setLabel(self.lang(32208))
		self.getControl(180).setLabel(self.lang(32209))

		self.setFocus(self.getControl(110))


	def onClick(self, controlID):
		''' Passes back to the parent the context menu item that was selected '''

		self.parent.contextoption = controlID

		if controlID == 110:
			if self.getControl(110).getLabel() == self.lang(32200):
				self.getControl(110).setLabel(self.lang(32201))
				xbmc.sleep(100)
			else:
				self.getControl(110).setLabel(self.lang(32200))
				xbmc.sleep(100)

		self.close()

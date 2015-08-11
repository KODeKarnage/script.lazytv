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
import collections
import datetime
import json
import os
import pickle
import pprint
import Queue
import random
import re
import sys
import threading
import time
sys.path.append(xbmc.translatePath(os.path.join(xbmcaddon.Addon().getAddonInfo('path'), 'resources','lib')))

try:
    from cStringIO import StringIO
except:
    from StringIO import StringIO


# LazyTV Modules
import lazy_classes as C
import lazy_queries as Q
import lazy_tools   as T
import lazy_gui     as G
import lazy_random  as R 


# This is a throwaway variable to deal with a python bug
T.datetime_bug_workaround()

# addon structure variables
__addon__               = xbmcaddon.Addon()
__addonid__             = __addon__.getAddonInfo('id')
__addonversion__        = tuple([int(x) for x in __addon__.getAddonInfo('version').split('.')])
__scriptPath__          = __addon__.getAddonInfo('path')
__profile__             = xbmc.translatePath(__addon__.getAddonInfo('profile'))
__setting__             = __addon__.getSetting
__release__			 	= T.current_KODI_version()

# creates the logger & translator
keep_logs = True if __setting__('logging') == 'true' else False
logger    = C.lazy_logger(__addon__, __addonid__ + ' gui', keep_logs)
log       = logger.post_log
lang      = logger.lang
log('Running: ' + str(__release__))


class gui(threading.Thread):
	''' A thread to instantiate and launch the gui window. '''

	def __init__(self, xmlfile, __scriptPath__, epitems, settings):

		# not sure I need this, but oh well
		self.wait_evt = threading.Event()

		# queues to handles passing items to and recieving from the service
		# self.to_Parent_queue = to_Parent_queue
		# self.from_Parent_queue = from_Parent_queue

		threading.Thread.__init__(self)	

		# variable to keep the window live until it is exited (if the user want this)
		self.stay_puft = settings.get('skin_return', False)

		# variable to force a pass through the while loop
		self.first_entry = True

		# convert all the lazy_episodes into list items, using the LazyListItem class
		self.listitems = self.convert_LzEps_to_LzItms(epitems)

		# process the order and rando inclusion of the provided list items
		self.process_listitems()

		# instantiate the gui
		self.lzg = lazy_gui_class(xmlfile, __scriptPath__, 'Default', parent=self, listitems=self.listitems, settings=settings)

		# player to track if something is playing
		self.gui_player = gui_player(parent = self)

		self.item_is_playing = False


	def convert_LzEps_to_LzItms(self, epitems):
		''' convert all the lazy_episodes into list items, using the LazyListItem class '''
		
		return [C.LazyListItem(lazy_episode) for lazy_episode in epitems]


	def update_GUI(self, epitems):
		''' Updates the GUI with the latest information. '''

		self.listitems = self.convert_LzEps_to_LzItms(epitems)
		self.process_listitems()

		self.lzg.load_data(self.listitems)


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

		if self.s['excl_randos']:	self.listitems = filter(lambda x: x.show_type == 'randos', self.listitems)

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
			
			self.lzg.doModal()

			# the refresh function in the GUI changes the self.first_entry variable if the user want to
			# refresh the window. This will ensure the window is closed and then reopened.
			if self.first_entry:
				self.first_entry = False
				continue

			play_this = self.lzg.selected_show

			if all([play_this, play_this != 'null', self.lzg.play_now]):
				log('play_this not null, and play_now')

				self.lzg.play_now = False
				# this fix clears the playlist, adds the episode to the playlist, and then starts the playlist
				# it is needed because .strms will not start if using the executeJSONRPC method

				# WINDOW.setProperty("%s.playlist_running"    % ('LazyTV'), 'listview')

				T.json_query(Q.clear_playlist)

				try:
					for ep in play_this:
						Q.add_this_ep['params']['item']['episodeid'] = int(ep)
						T.json_query(Q.add_this_ep)
				except:
					Q.add_this_ep['params']['item']['episodeid'] = int(play_this)
					T.json_query(Q.add_this_ep)

				xbmc.sleep(50)
				self.gui_player.play(xbmc.PlayList(1))
				xbmc.executebuiltin('ActivateWindow(12005)')
				self.lzg.play_this = 'null'

		xbmc.sleep(500)


	def stop(self):

		del self.lzg.myContext
		del self.lzg
		del self.gui_player


class gui_player(xbmc.Player):

	def __init__(self, parent, *args, **kwargs):
		xbmc.Player.__init__(self)
		self.parent = parent

	def onPlayBackStarted(self):
		self.parent.item_is_playing = True

	def onPlayBackStopped(self):
		self.onPlayBackEnded()

	def onPlayBackEnded(self):
		self.parent.item_is_playing = False



class lazy_gui_class(xbmcgui.WindowXMLDialog):

	def __init__(self, strXMLname, strFallbackPath, strDefaultName, parent, listitems, settings):
		self.parent = parent
		self.listitems = listitems
		self.s = settings
		self.selected_show = 'null'
		self.play_now = False
		self.multiselect = False
		self.myContext = lazy_context('script-lazytv-contextwindow.xml', strFallbackPath, 'Default', parent=self)


	def onInit(self):
		skin = self.s['skinorno']

		log('window_init')

		# if the skin is the default xbmc list window, then relabel the controls
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
				self.close()             #and exits if it fails, CTRL6FAILED then triggers a Dialog.select instead '''

		else:
			self.name_list = self.getControl(655)

		self.load_data(self.listitems)


	def load_data(new_listitems):
		''' Loads listitems into the appropriate list control '''

		log('this is the data the window is using = ' + str(new_listitems))

		# add the new_listitems to the namelist control
		for i, listitem in enumerate(new_listitems):

			if listitem == None:
				continue

			# abort if there are too many shows, or the desired window length is reached
			if i == 1000 or (self.s.get('limitshows', False) == True and i == self.s.get('window_length', -1)):
				break

			# change the label if the default view is selected
			if skin == 0:

				listitem.label  = ' '.join([listitem.TVshowTitle, listitem.EpisodeNo])
				listitem.label2 = listitem.PercentPlayed if skin != 0 else str(listitem.PercentPlayed) + str(listitem.lastplayed)

			else:

				listitem.label  = listitem.TVshowTitle
				listitem.label2 = listitem.Title				

			# add this item to the name list control
			self.name_list.addItem(listitem)

		#self.ok.controlRight(self.name_list)
		self.setFocus(self.name_list)

		log('window_init_End')


	def onAction(self, action):
		contextagogone = False

		actionID = action.getId()
		
		if (actionID in (10, 92)):
			log('closing due to action')
			self.parent.stay_puft = False
			self.close()

		elif actionID in [117] and not contextagogone:
			# open lazy_context window

			contextagogone = True
			log(actionID)
			log('context menu via action')
	
			self.pos = self.name_list.getSelectedPosition()

			self.myContext.doModal()

			if self.myContext.contextoption == 110:
				'''toggle'''
				log('multiselect toggled')
				self.toggle_multiselect()

			elif self.myContext.contextoption == 120:
				'''playsel'''
				log('play selection')
				self.play_selection()

			elif self.myContext.contextoption == 130:
				'''playfrom'''
				log('play from here')
				self.play_from_here()
			
			elif self.myContext.contextoption == 140:
				'''export'''
				log('export selection')
				self.export_selection()
			
			elif self.myContext.contextoption == 150:
				'''markwatched'''
				log('toggle watched')
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

			log('context button: ' + str(self.myContext.contextoption))


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
				log('setting epid = ' + str(self.selected_show))
				self.play_now = True
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
		log('watch toggling')
		self.pos    = self.name_list.getSelectedPosition()
		q_batch = []
		count = 0
		for itm in range(self.name_list.size()):
			count += 1
			if itm == self.pos: 
				EpID = self.name_list.getListItem(itm).EpisodeID
				log(EpID)
				if EpID:
					if self.s['skinorno'] != 0:
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
				filename = self.name_list.getListItem(itm).File
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
		self.parent.first_entry = True
		self.close()


class lazy_context(xbmcgui.WindowXMLDialog):
	''' A context window for use within lazy_gui '''

	def __init__(self, strXMLname, strFallbackPath, strDefaultName, parent):
		self.parent = parent

	def onInit(self):
		self.parent.contextoption = '' 

		log('init multiselect ' + str(self.parent.multiselect))

		# if multiselect is active, then change the wording in the context menu
		if self.parent.multiselect:
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
		''' Passes back to the parent the context menu item that was selected '''

		self.parent.contextoption = controlID

		if controlID == 110:
			if self.getControl(110).getLabel() == lang(32200):
				self.getControl(110).setLabel(lang(32201))
				xbmc.sleep(100)
			else:
				self.getControl(110).setLabel(lang(32200))
				xbmc.sleep(100)

		self.close()

# declare file encoding
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

import xbmcgui
import xbmcaddon
import ast

_addon_              = xbmcaddon.Addon("script.lazytv")
_setting_            = _addon_.getSetting
lang                 = _addon_.getLocalizedString
scriptPath           = _addon_.getAddonInfo('path')

ACTION_PREVIOUS_MENU = 10
ACTION_NAV_BACK      = 92
SAVE                 = 5
HEADING              = 1
ACTION_SELECT_ITEM   = 7

show_request         = {"jsonrpc": "2.0","method": "VideoLibrary.GetTVShows","params": {"properties": ["title", "tvshowid", "thumbnail"]},"id": "1"}

def json_query(query, ret):
    try:
        xbmc_request = json.dumps(query)
        result = xbmc.executeJSONRPC(xbmc_request)
        if ret:
            return json.loads(result)['result']
        else:
            return json.loads(result)
    except:
        return {}


class xGUI(xbmcgui.WindowXMLDialog):

    def onInit(self):

        # Save button
        self.ok = self.getControl(SAVE)
        self.ok.setLabel('Save')

        # Heading
        self.hdg = self.getControl(HEADING)
        self.hdg.setLabel('LazyTV')
        self.hdg.setVisible(True)

        # Hide unused list frame
        self.x = self.getControl(3)
        self.x.setVisible(False)

        # Populate the list frame
        self.name_list      = self.getControl(6)
        self.uo             = user_options
        self.new_rando_list = []


        self.ea = xbmcgui.ListItem('Select All')
        self.ia = xbmcgui.ListItem('Deselect All')

        self.name_list.addItem(self.ea)
        self.name_list.addItem(self.ia)

        # Start the window with the first item highlighted
        self.name_list.getListItem(0).select(True)

        # Set action when clicking right from the Save button
        self.ok.controlRight(self.name_list)

        self.item_count = 2

        for i in self.uo:
            # populate the random list
            self.tmp = xbmcgui.ListItem(i[0],thumbnailImage=i[2])
            self.name_list.addItem(self.tmp)

            # highlight the already selection randos
            if i[1] in rando_list:
                self.name_list.getListItem(self.item_count).select(True)  
          
            self.item_count += 1

        self.setFocus(self.name_list)

    def onAction(self, action):
        actionID = action.getId()
        if (actionID in (ACTION_PREVIOUS_MENU, ACTION_NAV_BACK)):
            self.close()

    def onClick(self, controlID):

        if controlID == SAVE:
            for itm in range(self.item_count):
                if itm != 0 and itm != 1 and self.name_list.getListItem(itm).isSelected():
                    self.new_rando_list.append(itm)
            self.close()

        else:
            selItem = self.name_list.getSelectedPosition()
            if selItem == 0:
                self.process_itemlist(True)
            elif selItem == 1:
                self.process_itemlist(False)
            else:
                if self.name_list.getSelectedItem().isSelected():
                    self.name_list.getSelectedItem().select(False)
                else:
                    self.name_list.getSelectedItem().select(True)

    def process_itemlist(self, set_to):
        for itm in range(self.item_count):
            if itm != 0 and itm != 1:
                if set_to == True:
                    self.name_list.getListItem(itm).select(True)
                else:
                    self.name_list.getListItem(itm).select(False)


def select_randos_script():

    global primary_list
    global rando_list
    global user_options

    all_variables  = []
    rando_list     = []
    rando_list_int = []
    add_setting    = []
    carry_on       = []
    primary_list   = []
    user_options   = []

    all_shows = json_query(show_request, True)
    if 'tvshows' in all_shows:
        all_s = all_shows['tvshows']
        all_variables = [(x['title'],str(x['tvshowid']),x['thumbnail']) for x in all_s]
    else:
        all_variables = []

    all_variables.sort()

    rando_list = ast.literal_eval(_setting_('randos'))

    #rando_list is the list of items that are currently ignored

    for var in all_variables:
        primary_list.append(var[1])
        user_options.append(var[0])

    #primary_list is the list of items as they will be saved to the settings
    #user_options is the list of items as they will be seen on the screen
    #primary_list and user_options are in the same order


    # create and launch the custom window
    creation = xGUI("DialogSelect.xml", scriptPath, 'Default')
    creation.doModal()
    
    new_rando_list = creation.new_rando_list
    del creation

    _addon_.setSetting(id="randos",value=str(new_rando_list))

select_randos_script()
_addon_.openSettings()
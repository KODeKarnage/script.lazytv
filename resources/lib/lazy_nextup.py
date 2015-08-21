
import xbmc
import xbmcgui
import xbmcaddon
import json as json

ACTION_PLAYER_STOP = 13
    
class NextUpInfo(xbmcgui.WindowXMLDialog):

    item = None
    cancel = False
    watchnow = False
    
    def __init__(self, *args, **kwargs, next_ep):
        xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)

        self.next_ep = next_ep

    def onInit(self):
        self.action_exitkeys_id = [10, 13]

        episodeInfo = str(self.next_epSeason) + "x" + str(self.next_ep.EpisodeNo) + "."
        
        rating = str(round(float(self.next_ep.Rating)))

        # set the dialog data
        self.getControl(3000).setLabel(self.next_ep.Title)
        self.getControl(3001).setText(self.next_ep.plot)
        self.getControl(3002).setLabel(episodeInfo)
        self.getControl(3004).setLabel(self.next_ep.Premiered)
        
        self.getControl(3009).setImage(self.poster)
        try:
            thumbControl = self.getControl(3008)
            if(thumbControl != None):
                self.getControl(3008).setImage(self.next_ep.thumb)
        except:
            pass
        self.getControl(3006).setImage(self.next_ep.clearart)
        
        if rating != None:
            self.getControl(3003).setLabel(rating)
        else:
            self.getControl(3003).setVisible(False)
        
        
    def setItem(self, item):
        self.item = item
    
    def setCancel(self, cancel):
        self.cancel = cancel

    def setPlaymode(self, mode):
        self.playmode = mode
        
    def isCancel(self):
        return self.cancel
            
    def setWatchNow(self, watchnow):
        self.watchnow = watchnow
    
    def isWatchNow(self):
        return self.watchnow
    
    def onFocus(self, controlId):
        pass
        
    def doAction(self):
        pass

    def closeDialog(self):
        self.close()   

    # def toggleplaymode(self):
    #     if self.getControl(3014).getLabel() == "Default: Play"
    #         self.getControl(3014).setLabel("Default: Dont Play")
    #         xbmcaddon.Addon(id='service.nextup.notification').setSetting("autoPlayMode", '1')
    #     else:
    #         self.getControl(3014).setLabel("Default: Play")
    #         xbmcaddon.Addon(id='service.nextup.notification').setSetting("autoPlayMode", '0')
        
    def onClick(self, controlID):
        
        xbmc.log("nextup info onclick: "+str(controlID))

        if(controlID == 3012):
            # watch now
            self.setWatchNow(True)
            self.close()
        
        elif(controlID == 3013):
            #cancel
            self.setCancel(True)
            self.close()

        # elif(controlID) == 3014):
        #     #toggle default
        #     self.toggleplaymode()

    
    def onAction(self, action):
        
        xbmc.log("nextup info action: "+str(action.getId()))
        if action == ACTION_PLAYER_STOP:
            self.close()
     

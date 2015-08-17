# XBMC modules
import xbmc
import xbmcaddon
import xbmcgui



class LazyInteraction(object):
	''' Class to handle interactions with the user for the service and launcher. '''

	def __init__(self, settings, log, lang, release):

		self.s = settings
		self.log = log
		self.lang = lang
		self.release = release
		self.DIALOG = xbmcgui.Dialog()


	# ON STOP method
	def next_ep_prompt(self, showtitle, season, episode):
		''' Displays the dialog for the next prompt, returns 0 or 1 for dont play or play '''

		self.log('next_prompt dialog method reached, showtitle: {}, season: {}, episode: {}'.format(showtitle, season, episode))
		self.log(release, 'release: ')
		# setting this to catch error without disrupting UI
		prompt = -1

		# format the season and episode
		SE = str(int(season)) + 'x' + str(int(episode))

		# if default is PLAY
		if self.s['promptdefaultaction'] == 0:
			ylabel = self.lang(32092) 	#"Play"
			nlabel = self.lang(32091)	#"Dont Play

		# if default is DONT PLAY
		elif self.s['promptdefaultaction'] == 1:
			ylabel = self.lang(32091)	#"Dont Play
			nlabel = self.lang(32092)	#"Play"

		if release == 'Frodo':
			if self.s['promptduration']:
				prompt = self.DIALOG.select(self.lang(32164), [self.lang(32165) % self.s['promptduration'], self.lang(32166) % (showtitle, SE)], autoclose=int(self.s['promptduration'] * 1000))
			else:
				prompt = self.DIALOG.select(self.lang(32164), [self.lang(32165) % self.s['promptduration'], self.lang(32166) % (showtitle, SE)])

		else:
			if self.s['promptduration']:
				prompt = self.DIALOG.yesno(self.lang(32167) % self.s['promptduration'], self.lang(32168) % (showtitle, SE), self.lang(32169), yeslabel = ylabel, nolabel = nlabel, autoclose=int(self.s['promptduration'] * 1000))
			else:
				prompt = self.DIALOG.yesno(self.lang(32167) % self.s['promptduration'], self.lang(32168) % (showtitle, SE), self.lang(32169), yeslabel = ylabel, nolabel = nlabel)

		self.log(prompt, 'user prompt: ')

		# if the user exits, then dont play
		if prompt == -1:
			prompt = 0

		# if the default is DONT PLAY then swap the responses
		elif self.s['promptdefaultaction'] == 1:
			if prompt == 0:
				prompt = 1
			else:
				prompt = 0

		self.log(self.s['promptdefaultaction'], 'default action: ')
		self.log(prompt, 'final prompt: ')

		return prompt


	# USER INTERACTION
	def user_input_launch_action(self):
		''' If needed, asks the user which action they would like to perform '''

		choice = self.DIALOG.yesno('LazyTV', self.lang(32100),'',self.lang(32101), self.lang(32102),self.lang(32103))

		return choice


	def display_prev_check(self, showtitle, season, episode):
		''' Displays the notification of there being a previous episode to watch before the current one. '''

		return self.DIALOG.yesno(self.lang(32160), self.lang(32161) % (showtitle, season, episode), self.lang(32162))
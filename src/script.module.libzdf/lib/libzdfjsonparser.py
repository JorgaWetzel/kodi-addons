# -*- coding: utf-8 -*-
import json
import requests
import hashlib
import re
import random
import string
import copy

import libmediathek4utils as lm4utils

#profiles: 
#default
#player
#player-3
#video-app
#video-app-teaser
#current-video-type
#mit-xperts-2 - referenced in the hbbtv mediathek

log = lm4utils.log


class parser:
	def __init__(self):
		self.result = {'items':[],'pagination':{'currentPage':0}}
		self.template = {'params':{}, 'metadata':{'art':{}}, 'type':'video'}
		self.playerId = 'ngplayer_2_3'
		#self.playerId = 'ngplayer_2_4'
		#self.playerId = 'ngplayer_2_5'
		#self.playerId = 'ngplayer_2_2_modul'
		#self.playerId = 'chromecast_1'
		#self.playerId = 'android_native_1'
		#self.playerId = 'android_native_2'
		#self.playerId = 'android_native_3'
		#self.playerId = 'smarttv_1'
		#self.playerId = 'smarttv_2'
		#self.playerId = 'smarttv_3'
		#self.playerId = 'smarttv_4'
		#self.playerId = 'smarttv_5'
		#self.playerId = 'ios_native_1'
		#self.playerId = 'ios_native_2'
		#self.playerId = 'voice_1'
		#self.playerId = 'portal'

	def _getTokenFromUrl(self):
		r = requests.get(self.tokenUrl)
		token = r.json()['token']
		lm4utils.f_mkdir(lm4utils.pathUserdata(''))
		lm4utils.f_write(lm4utils.pathUserdata('token'), token)
		return token

	def _getTokenFromPage(self):
		# Der Sender liefert das API-Token in der Konfiguration seiner eigenen Webseite
		# aus. Der früher genutzte Token-Endpunkt (zdf-cdn.live.cellular.de) ist
		# abgeschaltet, sein Hostname löst nicht mehr auf.
		r = requests.get(self.tokenPageUrl, headers={'user-agent': self.userAgent})
		# Der Token steht im RSC-Payload der Seite, dort als JavaScript-String eingebettet:
		# die Anführungszeichen sind escaped. Ein Ausdruck für reines JSON findet nichts.
		treffer = re.compile(r'videoToken\\?"\s*:\s*\{\s*\\?"apiToken\\?"\s*:\s*\\?"([A-Za-z0-9_-]{16,})').findall(r.text)
		if not treffer:
			treffer = re.compile(r'\\?"apiToken\\?"\s*:\s*\\?"([A-Za-z0-9_-]{16,})').findall(r.text)
		if not treffer:
			raise RuntimeError('kein apiToken in %s (status %s, %s Zeichen, Anfang: %s)'
				% (self.tokenPageUrl, r.status_code, len(r.text), repr(r.text[:200])))
		lm4utils.f_mkdir(lm4utils.pathUserdata(''))
		lm4utils.f_write(lm4utils.pathUserdata('token'), treffer[0])
		return treffer[0]

	def _getTokenFromAPI(self):
		headers = {'user-agent': self.userAgent,'Host':self.baseApi.split('/')[2]}
		r = requests.get(f'{self.baseApi}/oauth/getApiToken',headers=headers)
		wwwAuth = r.headers['WWW-Authenticate']

		realm      = re.compile('Digest realm="(.+?)"', re.DOTALL).findall(wwwAuth)[0]
		qop        = re.compile('qop="(.+?)"', re.DOTALL).findall(wwwAuth)[0]
		nonce      = re.compile('nonce="(.+?)"', re.DOTALL).findall(wwwAuth)[0]
		uri        = f'{self.baseApi}/oauth/getApiToken'
		nonceCount = '00000002'
		cnonce     = ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(16))

		HA1        = hashlib.md5(f'{self.API_CLIENT_ID}:{realm}:{self.API_CLIENT_KEY}'.encode('utf-8')).hexdigest()
		HA2        = hashlib.md5(f'GET:{uri}'.encode('utf-8')).hexdigest()
		response   = hashlib.md5(f'{HA1}:{nonce}:{nonceCount}:{cnonce}:{qop}:{HA2}'.encode('utf-8')).hexdigest()

		headers['authorization'] = f'Digest username="{self.API_CLIENT_ID}", realm="{realm}", nonce="{nonce}", uri="{uri}", response="{response}", opaque="null", qop={qop}, nc={nonceCount}, cnonce="{cnonce}"'

		j = requests.get(f'{self.baseApi}/oauth/getApiToken',headers=headers).json()

		token = j['apiToken']
		lm4utils.f_mkdir(lm4utils.pathUserdata(''))
		lm4utils.f_write(lm4utils.pathUserdata('token'), token)
		return token

	def _getU(self,url,Menu=False):
		token = lm4utils.f_open(lm4utils.pathUserdata('token'))
		if token == '':
			token = self._getToken()
		header = {'Api-Auth': f'Bearer {token}', 'Accept-Encoding': 'gzip, deflate'}
		response = requests.get(url,headers=header)
		# Abgelaufenes oder ungültiges Token: neu beschaffen und einmal wiederholen.
		# Vorher wurde dieselbe Token-Datei nur erneut gelesen - der Aufruf scheiterte
		# damit genauso wie zuvor.
		if response.status_code in (401, 403, 404) or response.text == '':
			token = self._getToken()
			header = {'Api-Auth': f'Bearer {token}', 'Accept-Encoding': 'gzip, deflate'}
			response = requests.get(url,headers=header)
		return response.text

	def _getToken(self):
		if self.tokenUrl:
			return self._getTokenFromUrl()
		elif getattr(self, 'tokenPageUrl', False):
			return self._getTokenFromPage()
		else:
			return self._getTokenFromAPI()

	def parsePage(self,url):
		response = self._getU(url,True)
		j = json.loads(response)
		if   j['profile'] == 'http://zdf.de/rels/search/result':
			return self._parseSearch(j)
		elif j['profile'] == 'http://zdf.de/rels/search/result-page':
			return self._parseSearchPage(j)
		elif j['profile'] in ['http://zdf.de/rels/content/page-index','http://zdf.de/rels/content/page-index-video-app']:
			#return self._parsePageIndex(j)
			return self._parsePageIndex2(j)
		elif j['profile'] in ['http://zdf.de/rels/content/content-filter','http://zdf.de/rels/content/content-filter-page-video_episode_vod']:
			return self._parseContentFilter(j)
		#elif j['profile'] in ['http://zdf.de/rels/content/page-index-teaser','http://zdf.de/rels/content/page-index-video-app-teaser']:
		#	return self._parseTeaser(j)#not implemented atm
		elif j['profile'] == 'http://zdf.de/rels/content/special-page-live-tv-video-app':
			return self._parseTV(j)
		elif j['profile'] == 'http://zdf.de/rels/cmdm/resultpage-broadcasts':
			return self._parseBroadcast(j)
		elif j['profile'] == 'http://zdf.de/rels/content/special-page-broadcast-missed':
			# "Sendung verpasst" lief früher über das Profil page-index. Seit dem
			# 03.11.2026 vergibt das ZDF dafür ein eigenes Profil, ohne den Inhalt zu
			# ändern: die Sendungen stehen weiter unter broadcasts-page und haben dort
			# denselben Aufbau wie eine resultpage-broadcasts.
			seite = j.get('http://zdf.de/rels/broadcasts-page')
			if isinstance(seite, dict) and 'http://zdf.de/rels/cmdm/broadcasts' in seite:
				return self._parseBroadcast(seite)
			log('special-page-broadcast-missed ohne verwertbare broadcasts-page: %s'
				% (sorted(seite.keys()) if isinstance(seite, dict) else type(seite).__name__))
			lm4utils.displayMsg('ZDF Mediathek', 'Der Sender hat den Aufbau dieser Rubrik geändert')
			return self.result
		elif j['profile'] in ['http://zdf.de/rels/gone','http://zdf.de/rels/not-found']:
			# Das ZDF schaltet einzelne Dokumente ab, ohne die Adresse zu entfernen.
			lm4utils.displayMsg('ZDF Mediathek', 'Diese Rubrik gibt es beim Sender nicht mehr')
			log('Dokument abgeschaltet: ' + j['profile'])
			return self.result
		else:
			# Vorher stand hier ein nacktes `raise` ausserhalb eines except-Blocks; das
			# ergab die irreführende Meldung "No active exception to reraise".
			log('Unknown profile: ' + j['profile'])
			# Den Aufbau mitschreiben. Das ZDF vergibt einem Dokument gelegentlich ein
			# neues Profil, ohne den Inhalt zu ändern; dann genügt ein weiterer Zweig
			# oben. Ohne diese Zeilen muss man dafür erst einen Token besorgen und das
			# Dokument von Hand abrufen.
			log('  Schlüssel oberste Ebene: %s' % sorted(j.keys()))
			for schluessel in ('module', 'cluster', 'stage', 'teaser'):
				if schluessel in j and isinstance(j[schluessel], list) and j[schluessel]:
					log('  %s[0]: %s' % (schluessel, sorted(j[schluessel][0].keys())))
			lm4utils.displayMsg('ZDF Mediathek', 'Unbekanntes Antwortformat des Senders')
			return self.result

	def getAZ(self,uri='/content/documents/sendungen-100.json?contentTypes=teaser'):
		response = self._getU(self.baseApi+uri,True)
		j = json.loads(response)
		for brand in j['brand']:
			if 'title' in brand:
				if 'teaser' in brand:
					for teaser in brand['teaser']:
						target = teaser['http://zdf.de/rels/target']
						self._grepItem(target)
		return self.result
		
	def _parseSearch(self,j):
		for module in j['module']:
			for result in module['filterRef']['resultsWithVideo']['http://zdf.de/rels/search/results']:
				target = result['http://zdf.de/rels/target']
				self.template['metadata']['views'] = result['viewCount']
				self._grepItem(target)
		return self.result
				
	def _parseSearchPage(self,j):
		for result in j['http://zdf.de/rels/search/results']:
			target = result['http://zdf.de/rels/target']
			if not target['profile'] == 'http://zdf.de/rels/cmdm/broadcast-teaser':#filters out future broadcasts
				self._grepItem(target)
		return self.result
		
	def _parsePageIndex(self,j):
		for module in j['module']:
			if 'teaser' in module:
				for teaser in module['teaser']:
					self._grepItem(teaser['http://zdf.de/rels/target'])
		return self.result

	def _parsePageIndex2(self,j):
		for result in j['module'][0]['filterRef']['resultsWithVideo']['http://zdf.de/rels/search/results']:
			target = result['http://zdf.de/rels/target']
			self.template['metadata']['views'] = result['viewCount']
			self._grepItem(target)
		return self.result
		
	def _parseContentFilter(self,j):
		for result in j['resultsWithVideo']['http://zdf.de/rels/search/results']:
			target = result['http://zdf.de/rels/target']
			self.template['metadata']['views'] = result['viewCount']
			self._grepItem(target)
		return self.result
		
	def _parseBroadcast(self,j):
		for broadcast in j['http://zdf.de/rels/cmdm/broadcasts']:
			if 'http://zdf.de/rels/content/video-page-teaser' in broadcast:
				target = broadcast['http://zdf.de/rels/content/video-page-teaser']
				if broadcast['effectiveAirtimeBegin'] is not None:#TODO: find alternative for videos without this field
					self.template['metadata']['aired'] = {'ISO8601':broadcast['effectiveAirtimeBegin']}
					self._grepItem(target,'date')
		return self.result

	def _parseTV(self,j):
		for broadcast in j['tvService'][0]['http://zdf.de/rels/broadcasts-page']['http://zdf.de/rels/cmdm/broadcasts']:
			if 'http://zdf.de/rels/content/video-page-teaser' in broadcast:
				target = broadcast['http://zdf.de/rels/content/video-page-teaser']
				if broadcast['effectiveAirtimeBegin'] is not None:#TODO: find alternative for videos without this field
					self.template['metadata']['aired'] = {'ISO8601':broadcast['effectiveAirtimeBegin']}
					self._grepItem(target,'date')
		return self.result

	def _grepItem(self,target,forcedType=False):
		if target['profile'] in ['http://zdf.de/rels/not-found','http://zdf.de/rels/gone']:
			return False
		else:
			# Die Mediathek-API ändert ihr JSON ohne Ankündigung. Fehlt einem einzelnen
			# Eintrag ein erwartetes Feld, wird er übersprungen statt die ganze Liste
			# mit einem KeyError leer zu lassen.
			try:
				self._grepItemDefault(target,forcedType)
			except (KeyError, TypeError, IndexError) as e:
				log('übersprungen: %s (%s: %s)' % (target.get('teaserHeadline', target.get('profile', '?')), type(e).__name__, e))
				return False

	def _grepItemDefault(self,target,forcedType=False):

		self.d = copy.deepcopy(self.template)
		self.d['metadata']['name'] = target['teaserHeadline']
		self.d['metadata']['plot'] = target['teasertext']
		self._grepArt(target)
		self._grepActors(target)

		if target['contentType'] == 'topic':
			if target['hasVideo'] == False: return False

			self.d['params']['url'] = self.baseApi + target['self']+'&limit=100'
			self.d['params']['mode'] = 'libZdfListPage'
			self.d['type'] = 'dir'

		elif target['contentType'] in ['brand','category','topic']:
			if target['hasVideo'] == False: return False

			self.d['params']['url'] = self.baseApi + target['http://zdf.de/rels/search/page-video-counter-with-video']['self'].replace('&limit=0','&limit=100')
			self.d['params']['mode'] = 'libZdfListPage'
			self.d['type'] = 'dir'

		elif target['contentType'] == 'clip':
			try:
				self.d['params']['url'] = self.baseApi + target['mainVideoContent']['http://zdf.de/rels/target']['http://zdf.de/rels/streams/ptmd-template'].replace('{playerId}',playerId)
				if 'duration' in target['mainVideoContent']['http://zdf.de/rels/target']:
					self.d['metadata']['duration'] = target['mainVideoContent']['http://zdf.de/rels/target']['duration']
				self.d['params']['mode'] = 'libZdfPlay'
				#d['type'] = 'clip'
				self.d['type'] = 'video'
			except: self.d = False

		elif target['contentType'] == 'episode':# or target['contentType'] == 'clip':
			if not target['hasVideo']:
				pass
				#return False
			#if target['mainVideoContent']['http://zdf.de/rels/target']['showCaption']:
			#	d['suburl'] = self.baseApi + target['mainVideoContent']['http://zdf.de/rels/target']['captionUrl']
			if 'mainVideoContent' in target:
				content = target['mainVideoContent']['http://zdf.de/rels/target']
			elif 'mainContent' in target:
				content = target['mainContent'][0]['videoContent'][0]['http://zdf.de/rels/target']
			else: return False
				
			if 'duration' in content:
				self.d['metadata']['duration'] = content['duration']
			#if 'programmeItem' in target and len(target['programmeItem']) >= 1 and 'http://zdf.de/rels/target' in target['programmeItem'][0] and target['programmeItem'][0]['http://zdf.de/rels/target']['http://zdf.de/rels/cmdm/season'] is not None:
			#	self.d['metadata']['season'] = target['programmeItem'][0]['http://zdf.de/rels/target']['http://zdf.de/rels/cmdm/season']['seasonNumber']
			#	self.d['metadata']['episode'] = target['programmeItem'][0]['http://zdf.de/rels/target']['episodeNumber']
			#self.d['metadata']['tvshowtitle'] = 'ListItem.TVShowTitle'#target['teaserHeadline']

			if not 'http://zdf.de/rels/streams/ptmd-template' in content: return False
			self.d['params']['url'] = self.baseApi + content['http://zdf.de/rels/streams/ptmd-template'].replace('{playerId}',self.playerId)
			self.d['params']['mode'] = 'libZdfPlay'

			self.d['type'] = 'episode'

		else:
			log('Unknown target type: ' + target['contentType'])
			self.d = False


		if self.d:
			if forcedType:
				self.d['type'] = forcedType
			self.result['items'].append(self.d)
			return True
		else:
			return False
		
	def _grepArt(self,target,isVideo=False):
		art = {}
		if not isVideo:
			if 'layouts' in target['teaserImageRef']:
				if '384xauto' in target['teaserImageRef']['layouts']:
					self.d['metadata']['art']['thumb'] = target['teaserImageRef']['layouts']['384xauto']
				elif '1920x1080' in target['teaserImageRef']['layouts']:
					self.d['metadata']['art']['thumb'] = target['teaserImageRef']['layouts']['1920x1080']

	def _grepActors(self,target):
		if 'programmeItem' in target:
			for item in target['programmeItem']:
				if item['profile'] == 'http://zdf.de/rels/content-reference/programme-item':
					if 'actorDetails' in item['http://zdf.de/rels/target'] and item['http://zdf.de/rels/target']['actorDetails']:
						actors = []
						for actor in item['http://zdf.de/rels/target']['actorDetails']['actorDetail']:
							if actor['name'] != '':
								actors.append(actor)
						self.d['metadata']['actors'] = actors
					if 'crewDetails' in item['http://zdf.de/rels/target'] and item['http://zdf.de/rels/target']['crewDetails'] != None:
						writers = []
						directors = []
						artists = []
						for crew in item['http://zdf.de/rels/target']['crewDetails']['crewDetail']:
							if crew['function'] == 'autor':
								writers.append(crew['name'])
							elif crew['function'] == 'kamera':
								directors.append(crew['name'])
							elif crew['function'] == 'musik':
								artists.append(crew['name'])
							elif crew['function'] == 'regie':
								directors.append(crew['name'])
						if len(writers) != 0: self.d['metadata']['writers'] = writers
						if len(directors) != 0: self.d['metadata']['directors'] = directors
						if len(artists) != 0: self.d['metadata']['artists'] = artists
					if 'text' in item['http://zdf.de/rels/target'] and item['http://zdf.de/rels/target']['text'] != None:
						self.d['metadata']['plot'] = item['http://zdf.de/rels/target']['text'].replace('<br/>','\n').replace('<b>','[B]').replace('</b>','[/B]')
					if 'originalTitle' in item['http://zdf.de/rels/target'] and item['http://zdf.de/rels/target']['originalTitle'] != None:
						self.d['metadata']['tvshowtitle'] = item['http://zdf.de/rels/target']['originalTitle']

	def getVideoUrlById(self,id):
		url = self.baseApi + '/content/documents/' + id + '.json?profile=player'
		response = self._getU(url,True)
		j = json.loads(response)
		url = self.baseApi + j['mainVideoContent']['http://zdf.de/rels/target']['http://zdf.de/rels/streams/ptmd-template'].replace('{playerId}',self.playerId)
		d = getVideoUrl(url)
		d['metadata'] = {}
		d['metadata']['name'] = f'{j["title"]} - {j["subtitle"]}'
		d['metadata']['plot'] = j['teasertext']
		d['metadata']['thumb'] = _grepArt(j['teaserImageRef'])
		d['metadata']['duration'] = str(j['mainVideoContent']['http://zdf.de/rels/target']['duration'])
		return d
		
	def getVideoUrl(self,url):
		d = {'media':[],'subtitle':[]}
		response = self._getU(url,False)
		j = json.loads(response)
		for caption in j.get('captions',[]):
			if caption['format'] == 'ebu-tt-d-basic-de':
				d['subtitle'].append({'url':caption['uri'], 'type':'ttml', 'lang':'de', 'colour':True})
			#elif caption['format'] == 'webvtt':
			#	d['subtitle'].append({'url':caption['uri'], 'type':'webvtt', 'lang':'de', 'colour':False})
		# Das ZDF bietet pro Video mehrere Varianten mit unterschiedlicher Regions-
		# freigabe an (geoLocation: world, ebu, dach, de). Vorher wurde blind die erste
		# genommen; ist die nur in DACH freigegeben, antwortet das CDN mit 403 und die
		# Wiedergabe bricht ohne Meldung ab. Jetzt zuerst die weitest freigegebene.
		reichweite = {'world': 0, 'ebu': 1, 'dach': 2, 'de': 3}
		varianten = []
		for item in j.get('priorityList', []):
			for formitaet in item.get('formitaeten', []):
				if formitaet.get('type') != 'h264_aac_ts_http_m3u8_http':
					continue
				for quality in formitaet.get('qualities', []):
					if quality.get('quality') != 'auto':
						continue
					for track in quality.get('audio', {}).get('tracks', []):
						if not track.get('uri'):
							continue
						geo = track.get('geoLocation') or formitaet.get('geoLocation') or item.get('geoLocation') or '?'
						varianten.append((reichweite.get(geo, 8), geo, track['uri']))
		varianten.sort(key=lambda v: v[0])
		log('Stream-Varianten (geoLocation): %s' % ', '.join(v[1] for v in varianten))
		for _, geo, uri in varianten:
			d['media'].append({'url':uri, 'type': 'video', 'stream':'HLS'})
		return d



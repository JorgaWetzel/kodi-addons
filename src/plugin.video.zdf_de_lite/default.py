# -*- coding: utf-8 -*-
import libzdf

class zdf(libzdf.libzdf):
	def __init__(self):
		self.apiVersion = 2
		self.baseApi = 'https://api.zdf.de'
		self.userAgent = 'Mozilla/5.0 (X11; Linux x86_64; rv:66.0) Gecko/20100101 Firefox/66.0'
		self.channels =	['ZDF','ZDFinfo','ZDFneo',]
		# Der früher genutzte Token-Endpunkt ist abgeschaltet (Hostname löst nicht mehr
		# auf). Das Token steht in der Konfiguration der ZDF-Webseite.
		self.tokenUrl = False
		self.tokenPageUrl = 'https://www.zdf.de/'
		self.API_CLIENT_ID = False
		self.API_CLIENT_KEY = False
		libzdf.libzdf.__init__(self)

	def libZdfListMain(self):
		# Gegenüber der Vorlage ist "Meistgesehen" ersetzt: das Dokument
		# meist-gesehen-100.json ist beim ZDF abgeschaltet (profile .../rels/gone).
		l = []
		l.append({'metadata':{'name':'Sendung verpasst'}, 'params':{'mode':'libZdfListPage','url':f'{self.baseApi}/content/documents/sendung-verpasst-100.json?profile=default'}, 'type':'dir'})
		l.append({'metadata':{'name':self.translation(32132)}, 'params':{'mode':'libZdfListShows'}, 'type':'dir'})
		l.append({'metadata':{'name':self.translation(32133)}, 'params':{'mode':'libZdfListChannel'}, 'type':'dir'})
		l.append({'metadata':{'name':self.translation(32134)}, 'params':{'mode':'libZdfListPage', 'url':f'{self.baseApi}/search/documents?q=%2A&contentTypes=category'}, 'type':'dir'})
		l.append({'metadata':{'name':self.translation(32139)}, 'params':{'mode':'libMediathekSearch', 'searchMode':'libZdfListSearch'}, 'type':'dir'})
		return {'items':l,'name':'root'}

o = zdf()
o.action()
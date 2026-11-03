"""Installiert Add-ons und Repositories nach einer Paketliste.

Ein Kodi-Gerät vollständig nachzubauen heisst, zwei Dinge zu lösen:

1. **Woher kommen die Add-ons?** Nicht als mitgelieferte Dateien - ein Gerät
   trägt schnell 500 MB an Add-ons, und mitgelieferte Fassungen veralten. Der
   Weg hier: Das Paket nennt nur die **Kataloge** (die `addons.xml` jedes
   Repositories) und die gewünschten Add-on-Kennungen. Alles Weitere - welche
   Fassung die neueste ist, wo ihr ZIP liegt, was sie ihrerseits braucht - steht
   in diesen Katalogen und wird zur Laufzeit gelesen. Das Paket bleibt dadurch
   wenige Kilobyte gross und bringt immer den aktuellen Stand.

2. **Das Henne-Ei-Problem der Repositories.** Ein Repository ist selbst ein
   Add-on und müsste eigentlich installiert sein, bevor man daraus installieren
   kann. Hier entfällt das: Die Kataloge werden direkt über ihre Adresse
   gelesen, nicht über ein installiertes Repository. Die Repository-Add-ons
   selbst stehen in diesen Katalogen mit drin und werden wie jedes andere
   Add-on eingespielt - danach holt Kodi künftige Aktualisierungen von allein.

Warum nicht der Builtin `InstallAddon`? Der öffnet je Add-on einen Ja/Nein-
Dialog, der von aussen nicht zu beantworten ist (am Gerät gemessen, siehe
einrichtung.setze_skin für denselben Mechanismus beim Skin). Bei über hundert
Add-ons wäre das unbrauchbar. Das ZIP selbst zu holen und zu entpacken ist der
Weg, den Kodi intern ebenso geht.
"""

import gzip
import io
import json
import os
import re
import shutil
import time
import zipfile
import xml.etree.ElementTree as ET

try:                                     # Kodi bringt Python 3 mit
    from urllib.request import Request, urlopen
except ImportError:                      # pragma: no cover - nur zur Sicherheit
    from urllib2 import Request, urlopen

import xbmc
import xbmcvfs

from einrichtung import log, rpc


ADDONS = xbmcvfs.translatePath('special://home/addons/')

# Diese Kennungen beschreiben Kodi selbst, nicht installierbare Add-ons. Sie
# tauchen in jeder Abhängigkeitsliste auf und werden übergangen.
KODI_EIGEN = re.compile(r'^(xbmc|kodi)\.')

# Sehr grosse Kataloge ohne Begrenzung zu lesen, hängt Kodi bei einer kaputten
# Gegenstelle auf. 40 MB ist weit mehr als jeder echte Katalog braucht.
MAX_KATALOG = 40 * 1024 * 1024
MAX_ZIP = 400 * 1024 * 1024


def _hole(url, grenze):
    """Lädt eine Adresse und gibt die Bytes zurück. Entpackt gzip selbst."""
    anfrage = Request(url, headers={'User-Agent': 'Kodi/21 Jorga-Build'})
    with urlopen(anfrage, timeout=30) as antwort:
        roh = antwort.read(grenze + 1)
    if len(roh) > grenze:
        raise ValueError('Antwort über %d Bytes: %s' % (grenze, url))
    # Kataloge liegen oft als .gz vor, auch wenn die Adresse das nicht sagt.
    if roh[:2] == b'\x1f\x8b':
        roh = gzip.GzipFile(fileobj=io.BytesIO(roh)).read()
    return roh


def _hoehere_fassung(a, b):
    """True, wenn a neuer ist als b. Vergleicht Zahlenblöcke, Rest alphabetisch."""
    def teile(v):
        return [int(t) if t.isdigit() else t for t in re.split(r'[.\-~+]', v or '0')]
    try:
        return teile(a) > teile(b)
    except TypeError:          # Zahl gegen Text - dann hilft nur der Textvergleich
        return str(a) > str(b)


def lies_katalog(katalog):
    """Liest eine addons.xml und gibt {kennung: eintrag} zurück.

    Ein Eintrag hält Fassung, Herunterladeadresse und Abhängigkeiten.
    """
    roh = _hole(katalog['addons_xml'], MAX_KATALOG)
    wurzel = ET.fromstring(roh)
    datadir = katalog['datadir'].rstrip('/')
    inhalt = {}
    for addon in wurzel.iter('addon'):
        kennung = addon.get('id')
        fassung = addon.get('version')
        if not kennung or not fassung:
            continue
        braucht = [i.get('addon') for i in addon.iter('import')
                   if i.get('addon') and not KODI_EIGEN.match(i.get('addon'))
                   and i.get('optional') != 'true']
        inhalt[kennung] = {
            'version': fassung,
            'url': '%s/%s/%s-%s.zip' % (datadir, kennung, kennung, fassung),
            'braucht': braucht,
            'quelle': katalog.get('id', katalog['addons_xml']),
        }
    return inhalt


def sammle_kataloge(kataloge, fortschritt=None, von=0, bis=20):
    """Liest alle Kataloge zu einem Gesamtangebot zusammen.

    Bietet mehr als ein Katalog dasselbe Add-on an, gewinnt die höhere Fassung.
    Ein Katalog, der nicht antwortet, lässt die übrigen unberührt - so bleibt
    eine Einrichtung brauchbar, wenn eine Fremdquelle verschwindet.
    """
    angebot, ausgefallen = {}, []
    for i, katalog in enumerate(kataloge):
        if fortschritt:
            fortschritt.update(von + int((bis - von) * i / max(len(kataloge), 1)),
                               'Lese Katalog: %s' % katalog.get('id', ''))
        try:
            inhalt = lies_katalog(katalog)
        except Exception as fehler:       # Netz, DNS, kaputtes XML
            log('Katalog nicht lesbar (%s): %s' % (katalog.get('id'), fehler),
                xbmc.LOGWARNING)
            ausgefallen.append(katalog.get('id', katalog['addons_xml']))
            continue
        for kennung, eintrag in inhalt.items():
            vorhanden = angebot.get(kennung)
            if not vorhanden or _hoehere_fassung(eintrag['version'], vorhanden['version']):
                angebot[kennung] = eintrag
    return angebot, ausgefallen


def kodi_hat(kennung):
    """True, wenn Kodi dieses Add-on kennt - auch ein eingebautes.

    Reicht nicht über den Add-on-Ordner zu gehen: einige Module liefert Kodi im
    eigenen Paket mit und sie liegen nicht im Profil (gemessen: script.module.pil
    ist auf Android eingebaut). Die würden sonst als fehlend gemeldet, obwohl
    sie da sind.
    """
    return bool(xbmc.getCondVisibility('System.HasAddon(%s)' % kennung))


def loese_auf(wunschliste, angebot, schon_da=()):
    """Ergänzt die Wunschliste um alles, was sie ihrerseits braucht.

    Gibt (reihenfolge, unauffindbar) zurück. Die Reihenfolge stellt sicher,
    dass eine Abhängigkeit vor dem Add-on steht, das sie braucht - sonst meldet
    Kodi das Add-on beim Einlesen als defekt.

    schon_da nennt Add-ons, die gerade erst aus dem Paket entpackt wurden. Kodi
    kennt sie noch nicht (das tut es erst nach UpdateLocalAddons), sie dürfen
    aber nicht als fehlend gelten.
    """
    reihenfolge, erledigt, unauffindbar = [], set(), []
    schon_da = set(schon_da)

    def besuche(kennung, pfad):
        if kennung in erledigt or KODI_EIGEN.match(kennung):
            return
        if kennung in pfad:               # Ringschluss - kommt bei Add-ons vor
            return
        eintrag = angebot.get(kennung)
        if not eintrag:
            # Nur melden, was wirklich fehlt - nicht, was Kodi mitbringt oder
            # was gerade aus dem Paket kam.
            if kennung not in schon_da and not kodi_hat(kennung):
                unauffindbar.append(kennung)
            erledigt.add(kennung)
            return
        for gebraucht in eintrag['braucht']:
            besuche(gebraucht, pfad | {kennung})
        erledigt.add(kennung)
        reihenfolge.append(kennung)

    for kennung in wunschliste:
        besuche(kennung, frozenset())
    return reihenfolge, unauffindbar


def _entpacke_addon(roh, kennung):
    """Entpackt ein Add-on-ZIP nach addons/. Gibt True bei Erfolg.

    Ein Add-on-ZIP trägt als obersten Ordner immer die Add-on-Kennung. Alles,
    was woanders hin zeigt, wird verworfen - ein ZIP aus dem Netz darf nicht
    bestimmen, wohin geschrieben wird.
    """
    ziel_wurzel = os.path.join(ADDONS, kennung)
    with zipfile.ZipFile(io.BytesIO(roh)) as z:
        namen = z.namelist()
        if not all(n.replace('\\', '/').split('/')[0] == kennung for n in namen if n.strip()):
            log('ZIP von %s enthält fremde Pfade, übersprungen' % kennung, xbmc.LOGWARNING)
            return False
        # Die alte Fassung weicht, sonst bleiben Dateien zurück, die es in der
        # neuen nicht mehr gibt (und die Kodi weiter lädt).
        if os.path.isdir(ziel_wurzel):
            shutil.rmtree(ziel_wurzel, ignore_errors=True)
        for name in namen:
            sauber = os.path.normpath(name).replace('\\', '/').lstrip('/')
            if sauber.startswith('..') or os.path.isabs(name):
                log('Pfad verlässt addons/, übersprungen: %s' % name, xbmc.LOGWARNING)
                continue
            ziel = os.path.join(ADDONS, sauber)
            if name.endswith('/'):
                os.makedirs(ziel, exist_ok=True)
                continue
            os.makedirs(os.path.dirname(ziel), exist_ok=True)
            with z.open(name) as quelle, open(ziel, 'wb') as datei:
                shutil.copyfileobj(quelle, datei)
    return True


def ist_installiert(kennung):
    return os.path.isdir(os.path.join(ADDONS, kennung))


def installiere(reihenfolge, angebot, fortschritt=None, von=20, bis=85,
                auch_vorhandene=False):
    """Lädt und entpackt die Add-ons. Gibt (neu, vorhanden, fehler) zurück."""
    neu, vorhanden, fehler = [], [], []
    for i, kennung in enumerate(reihenfolge):
        if fortschritt:
            fortschritt.update(von + int((bis - von) * i / max(len(reihenfolge), 1)),
                               'Add-on %d von %d: %s' % (i + 1, len(reihenfolge), kennung))
            if fortschritt.iscanceled():
                break
        if ist_installiert(kennung) and not auch_vorhandene:
            vorhanden.append(kennung)
            continue
        eintrag = angebot[kennung]
        try:
            roh = _hole(eintrag['url'], MAX_ZIP)
            if _entpacke_addon(roh, kennung):
                neu.append(kennung)
            else:
                fehler.append((kennung, 'ZIP-Aufbau unerwartet'))
        except Exception as problem:
            log('%s nicht installierbar: %s' % (kennung, problem), xbmc.LOGWARNING)
            fehler.append((kennung, str(problem)))
    return neu, vorhanden, fehler


def einlesen(kennungen, fortschritt=None, bei=88):
    """Lässt Kodi die neu entpackten Add-ons einlesen und schaltet sie ein."""
    if fortschritt:
        fortschritt.update(bei, 'Kodi liest die neuen Add-ons ein')
    xbmc.executebuiltin('UpdateLocalAddons')
    xbmc.sleep(3000)
    eingeschaltet = 0
    for kennung in kennungen:
        # Frisch entpackte Add-ons stehen gelegentlich als deaktiviert in der
        # Datenbank, wenn dort noch ein alter Eintrag lag.
        if rpc('Addons.SetAddonEnabled', addonid=kennung, enabled=True) is not None:
            eingeschaltet += 1
    return eingeschaltet


# ------------------------------------------------------- Ein ganzes Gerät einspielen

PAKET_DATEI = 'paket.json'


def lies_paket(pfad):
    """Liest eine Paketdatei. Nimmt ein ZIP oder einen entpackten Ordner."""
    if os.path.isdir(pfad):
        with open(os.path.join(pfad, PAKET_DATEI), 'r', encoding='utf-8') as f:
            return json.load(f), None
    with zipfile.ZipFile(pfad) as z:
        if PAKET_DATEI not in z.namelist():
            raise ValueError('%s enthält keine %s' % (os.path.basename(pfad), PAKET_DATEI))
        return json.loads(z.read(PAKET_DATEI).decode('utf-8')), pfad


def hole_paket(adresse, ziel_ordner):
    """Lädt ein Paket von einer Adresse, wenn es nicht schon lokal liegt."""
    if '://' not in adresse or adresse.startswith('file://'):
        return adresse.replace('file://', '')
    os.makedirs(ziel_ordner, exist_ok=True)
    ziel = os.path.join(ziel_ordner, 'paket-geladen.zip')
    roh = _hole(adresse, MAX_ZIP)
    with open(ziel, 'wb') as f:
        f.write(roh)
    return ziel


def menue_neu_bauen_lassen(skin):
    """Löscht die erzeugte Menüdatei des Skins, damit sie neu entsteht.

    Das Startmenü von script.skinshortcuts steht an drei Stellen: den DATA-Dateien
    und den Skin-Properties im Profil (die das Paket mitbringt) und einer daraus
    erzeugten Include-Datei im Skin-Ordner - und aus der rendert Kodi tatsächlich.
    Bleibt sie stehen, zeigt das Gerät trotz eingespielter Dateien das alte Menü.
    Am 03.11.2026 am Gerät gemessen. Gelöscht wird sie neu aufgebaut.
    """
    if not skin:
        return False
    erzeugt = xbmcvfs.translatePath(
        'special://home/addons/%s/xml/script-skinshortcuts-includes.xml' % skin)
    if os.path.isfile(erzeugt):
        try:
            os.remove(erzeugt)
            log('erzeugte Menüdatei von %s entfernt, Kodi baut sie neu' % skin)
            return True
        except OSError as fehler:
            log('Menüdatei nicht löschbar: %s' % fehler, xbmc.LOGWARNING)
    return False


# ---------------------------------------------------- Ein Gerät als Paket erfassen

# Kodi benennt jede Generation nach einem Namen; das offizielle Repository ist
# darunter abgelegt. Die Zahl ist die Hauptversion aus System.BuildVersion.
KODI_GENERATION = {19: 'matrix', 20: 'nexus', 21: 'omega', 22: 'piers', 23: 'quincy'}


def offizieller_katalog(hauptversion):
    """Das offizielle Kodi-Repository als Katalog.

    Es muss von Hand ergänzt werden: repository.xbmc.org ist in Kodi eingebaut
    und liegt nicht im Add-on-Ordner des Profils, lässt sich dort also nicht
    auslesen. Ohne diesen Eintrag fehlen einem Paket rund drei Dutzend Add-ons -
    inputstream.adaptive, die Metadaten-Scraper, pvr.iptvsimple und alles
    andere, was aus der offiziellen Quelle stammt (am 03.11.2026 gemessen:
    37 von 120 waren unauffindbar).
    """
    name = KODI_GENERATION.get(hauptversion)
    if not name:
        log('unbekannte Kodi-Generation %s, offizielles Repository ausgelassen'
            % hauptversion, xbmc.LOGWARNING)
        return None
    basis = 'https://mirrors.kodi.tv/addons/%s' % name
    return {'id': 'repository.xbmc.org',
            'addons_xml': basis + '/addons.xml.gz',
            'datadir': basis}


def _kataloge_des_geraets():
    """Liest aus den installierten Repositories deren Bezugsadressen.

    Ein Repository-Add-on nennt in seiner addon.xml je Zweig ein Paar aus
    Katalog (`info`) und Ablage der ZIPs (`datadir`). Mehrere Zweige dienen
    verschiedenen Kodi-Generationen; mitgenommen werden alle, die zur laufenden
    Fassung passen - die übrigen würden veraltete Add-ons liefern.
    """
    eigene = int(xbmc.getInfoLabel('System.BuildVersion').split('.')[0] or 0)
    kataloge = [k for k in (offizieller_katalog(eigene),) if k]
    for kennung in sorted(os.listdir(ADDONS)):
        datei = os.path.join(ADDONS, kennung, 'addon.xml')
        if not kennung.startswith('repository.') or not os.path.isfile(datei):
            continue
        try:
            wurzel = ET.parse(datei).getroot()
        except ET.ParseError as fehler:
            log('addon.xml von %s nicht lesbar: %s' % (kennung, fehler), xbmc.LOGWARNING)
            continue
        for verzeichnis in wurzel.iter('dir'):
            info = verzeichnis.findtext('info')
            datadir = verzeichnis.find('datadir')
            if not info or datadir is None or not datadir.text:
                continue
            min_v = verzeichnis.get('minversion')
            max_v = verzeichnis.get('maxversion')
            if min_v and eigene and int(min_v.split('.')[0]) > eigene:
                continue
            if max_v and eigene and int(max_v.split('.')[0]) < eigene:
                continue
            kataloge.append({'id': kennung, 'addons_xml': info.strip(),
                             'datadir': datadir.text.strip()})
        # Ältere Repositories führen info/datadir ohne dir-Block direkt im extension
        if not any(k['id'] == kennung for k in kataloge):
            info = wurzel.findtext('.//info')
            datadir = wurzel.find('.//datadir')
            if info and datadir is not None and datadir.text:
                kataloge.append({'id': kennung, 'addons_xml': info.strip(),
                                 'datadir': datadir.text.strip()})
    return kataloge


def installierte_addons():
    """Alle Add-ons, die im Profil liegen - also nicht die von Kodi mitgelieferten."""
    return sorted(k for k in os.listdir(ADDONS)
                  if k not in ('packages', 'temp')
                  and os.path.isfile(os.path.join(ADDONS, k, 'addon.xml')))


def abweichende_einstellungen(profil):
    """Liest aus guisettings.xml die Werte, die vom Kodi-Standard abweichen.

    Kodi markiert unveränderte Werte mit default="true". Nur der Rest ist eine
    bewusste Entscheidung des Nutzers und gehört in ein Paket - alles andere
    würde fremde Geräte ohne Not verstellen.
    """
    datei = os.path.join(profil, 'guisettings.xml')
    if not os.path.isfile(datei):
        return {}
    werte = {}
    for element in ET.parse(datei).getroot().iter('setting'):
        kennung = element.get('id')
        if not kennung or element.get('default') == 'true':
            continue
        werte[kennung] = element.text or ''
    return werte


# Was ein Paket nie mitnimmt: Werte, die am Gerät hängen oder es unbrauchbar
# machen, und solche, die jedes Gerät selbst erzeugt.
NICHT_UEBERNEHMEN = {
    'services.devicename': 'je Gerät eigen',
    'services.deviceuuid': 'je Gerät eigen, Kodi erzeugt sie selbst',
    'services.webserverpassword': 'Passwort',
    'services.webserverusername': 'Zugangsdaten',
    'services.esallinterfaces': 'Fernzugriff gehört pro Gerät entschieden',
    'videoscreen.resolution': 'hängt am Bildschirm, falscher Wert = schwarzes Bild',
    'videoscreen.screenmode': 'hängt am Bildschirm',
    'videoscreen.whitelist': 'hängt am Bildschirm',
    'videoscreen.monitor': 'hängt am Bildschirm',
    'audiooutput.audiodevice': 'hängt an der angeschlossenen Anlage',
    'audiooutput.passthroughdevice': 'hängt an der angeschlossenen Anlage',
    'debug.showloginfo': 'Diagnose-Rest, blendet Text über das Bild',
    'debug.extralogging': 'Diagnose-Rest',
    'general.addonupdates': 'ein Paket darf Add-on-Updates nie abschalten',
    'lookandfeel.skin': 'setzt der Assistent gezielt zuletzt',
}


def erfasse_geraet(profil, name=None):
    """Baut die Paketbeschreibung des laufenden Geräts (ohne die Dateien)."""
    werte = abweichende_einstellungen(profil)
    for kennung in list(werte):
        if kennung in NICHT_UEBERNEHMEN:
            del werte[kennung]
    haut = rpc('Settings.GetSettingValue', setting='lookandfeel.skin')
    return {
        'name': name or 'Kodi-Einrichtung',
        'erstellt': time.strftime('%Y-%m-%d %H:%M'),
        'kodi': xbmc.getInfoLabel('System.BuildVersion'),
        'skin': haut.get('value') if haut else '',
        'kataloge': _kataloge_des_geraets(),
        'addons': installierte_addons(),
        'einstellungen': werte,
        'nicht_uebernommen': sorted(NICHT_UEBERNEHMEN),
    }


# ------------------------------------- Add-ons, die aus keiner Quelle kommen

def packe_addon(kennung):
    """Packt einen installierten Add-on-Ordner als ZIP-Bytes.

    Gebraucht für die wenigen Add-ons, die in keinem Katalog mehr stehen, weil
    ihre Quelle verschwunden ist. Die müssen mitreisen, sonst fehlen sie auf dem
    neuen Gerät - und niemand findet sie wieder.
    """
    quelle = os.path.join(ADDONS, kennung)
    puffer = io.BytesIO()
    with zipfile.ZipFile(puffer, 'w', zipfile.ZIP_DEFLATED) as z:
        for wurzel, _, namen in os.walk(quelle):
            for name in namen:
                if name.endswith(('.pyc', '.pyo')):
                    continue              # Bytecode gehört dem alten Gerät
                absolut = os.path.join(wurzel, name)
                innen = os.path.relpath(absolut, ADDONS).replace(os.sep, '/')
                z.write(absolut, innen)
    return puffer.getvalue()


def entpacke_mitgelieferte(zipdatei, fortschritt=None, bei=16):
    """Entpackt die im Paket mitgelieferten Add-on-ZIPs. Gibt die Kennungen."""
    if zipdatei is None:
        return []
    eingespielt = []
    with zipfile.ZipFile(zipdatei) as z:
        namen = [n for n in z.namelist()
                 if n.startswith('addons/') and n.endswith('.zip')]
        for name in namen:
            kennung = os.path.basename(name)[:-4]
            if fortschritt:
                fortschritt.update(bei, 'Mitgeliefert: %s' % kennung)
            try:
                if _entpacke_addon(z.read(name), kennung):
                    eingespielt.append(kennung)
            except Exception as problem:
                log('mitgeliefertes %s nicht entpackbar: %s' % (kennung, problem),
                    xbmc.LOGWARNING)
    return eingespielt

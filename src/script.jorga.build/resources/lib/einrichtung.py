"""Spielt eine Kodi-Einrichtung ein, sichert die bestehende und holt sie zurück.

Eine Kodi-Einrichtung besteht aus zwei Dingen, die sich grundlegend verschieden
verhalten:

1. **Kodis eigene Einstellungen** (sonst in userdata/guisettings.xml). Die hält
   Kodi im Speicher und schreibt sie beim Beenden zurück. Wer nur die Datei
   ersetzt, verliert alles beim nächsten Beenden - Kodi überschreibt sie mit dem
   Stand aus dem Speicher. Solche Werte müssen deshalb über JSON-RPC gesetzt
   werden; dann stehen sie im Speicher und Kodi schreibt sie selbst korrekt weg.

2. **Dateien, die Kodi erst bei Bedarf liest** - Startmenü, Favoriten, Quellen,
   Skin-Einstellungen. Die lassen sich direkt ersetzen.

Daraus ergibt sich die Reihenfolge in spiele_ein(): zuerst die Dateien, dann die
Einstellungen, der Skin zuletzt.
"""

import json
import os
import shutil
import time
import zipfile

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

ADDON = xbmcaddon.Addon()
NAME = ADDON.getAddonInfo('name')
WURZEL = xbmcvfs.translatePath(ADDON.getAddonInfo('path'))
PROFIL = xbmcvfs.translatePath('special://profile/')
VORLAGE = os.path.join(WURZEL, 'resources', 'build')
SICHERUNGEN = os.path.join(PROFIL, 'jorga-sicherungen')

# Was zur Einrichtung gehört und damit gesichert und eingespielt wird.
# Bewusst nicht dabei: Database/ und Thumbnails/ - die baut Kodi selbst neu auf
# und sie machen den Löwenanteil der Datenmenge aus.
KONFIG_DATEIEN = [
    'guisettings.xml',
    'favourites.xml',
    'sources.xml',
    'advancedsettings.xml',
    'profiles.xml',
    'RssFeeds.xml',
]
KONFIG_ORDNER = [
    'keymaps',
    'playlists',
    os.path.join('addon_data', 'script.skinshortcuts'),
    os.path.join('addon_data', 'skin.mimic.lr'),
]


def log(text, stufe=xbmc.LOGINFO):
    xbmc.log('[%s] %s' % (ADDON.getAddonInfo('id'), text), stufe)


def melde(text, zeit=5000):
    xbmcgui.Dialog().notification(NAME, text, xbmcgui.NOTIFICATION_INFO, zeit)


def rpc(methode, **params):
    """Ruft JSON-RPC auf und gibt das Ergebnis zurück, oder None bei Fehler."""
    antwort = json.loads(xbmc.executeJSONRPC(json.dumps({
        'jsonrpc': '2.0', 'id': 1, 'method': methode, 'params': params,
    })))
    if 'error' in antwort:
        log('%s: %s' % (methode, antwort['error']), xbmc.LOGDEBUG)
        return None
    return antwort.get('result')


# ---------------------------------------------------------------- Einstellungen

def _passe_typ_an(kennung, wert_text):
    """Wandelt einen Textwert in den Typ, den diese Einstellung bei Kodi hat.

    Der Typ lässt sich nicht aus der XML-Datei ablesen - dort ist alles Text.
    Verlässlich ist nur Kodi selbst: der aktuelle Wert verrät den Typ.
    """
    ist = rpc('Settings.GetSettingValue', setting=kennung)
    if ist is None or 'value' not in ist:
        return None                      # Einstellung kennt dieses Kodi nicht
    vorbild = ist['value']

    if isinstance(vorbild, bool):
        return wert_text.lower() == 'true'
    if isinstance(vorbild, int):
        try:
            return int(wert_text)
        except ValueError:
            return None
    if isinstance(vorbild, list):
        if wert_text == '':
            return []
        teile = [t for t in wert_text.split(',') if t != '']
        # Kodi führt Zahlenlisten (etwa die Sprungweiten) als Liste von Integern
        if vorbild and isinstance(vorbild[0], int):
            try:
                return [int(t) for t in teile]
            except ValueError:
                return None
        return teile
    return wert_text


def setze_einstellungen(werte, fortschritt=None, von=0, bis=100):
    """Setzt Kodi-Einstellungen über JSON-RPC. Gibt (gesetzt, offen) zurück."""
    gesetzt, offen = 0, []
    posten = sorted(werte.items())
    for i, (kennung, wert_text) in enumerate(posten):
        if fortschritt:
            fortschritt.update(von + int((bis - von) * i / max(len(posten), 1)),
                               'Einstellungen: %s' % kennung)
            if fortschritt.iscanceled():
                break
        wert = _passe_typ_an(kennung, wert_text)
        if wert is None:
            offen.append(kennung)
            continue
        if rpc('Settings.SetSettingValue', setting=kennung, value=wert) is None:
            offen.append(kennung)
        else:
            gesetzt += 1
    return gesetzt, offen


# ---------------------------------------------------------------------- Dateien

def _konfig_pfade():
    """Alle vorhandenen Konfigurationsdateien als (absolut, relativ-zum-Profil)."""
    for name in KONFIG_DATEIEN:
        p = os.path.join(PROFIL, name)
        if os.path.isfile(p):
            yield p, name
    for ordner in KONFIG_ORDNER:
        basis = os.path.join(PROFIL, ordner)
        for wurzel, _, dateien in os.walk(basis):
            for d in dateien:
                p = os.path.join(wurzel, d)
                yield p, os.path.relpath(p, PROFIL)


def sichere(stempel=None):
    """Packt die aktuelle Einrichtung in ein ZIP und gibt dessen Pfad zurück."""
    if not os.path.isdir(SICHERUNGEN):
        os.makedirs(SICHERUNGEN)
    stempel = stempel or time.strftime('%Y%m%d-%H%M%S')
    ziel = os.path.join(SICHERUNGEN, 'einrichtung-%s.zip' % stempel)
    with zipfile.ZipFile(ziel, 'w', zipfile.ZIP_DEFLATED) as z:
        for absolut, relativ in _konfig_pfade():
            z.write(absolut, relativ.replace(os.sep, '/'))
        # Den aktiven Skin mitschreiben: er steht in guisettings.xml, die beim
        # Beenden noch verändert wird - der Stand von jetzt ist verlässlicher.
        haut = rpc('Settings.GetSettingValue', setting='lookandfeel.skin')
        if haut:
            z.writestr('jorga-skin.txt', haut.get('value', ''))
    return ziel


def _entpacke_nach_profil(zipdatei, fortschritt=None, von=0, bis=100):
    """Entpackt ein Einrichtungs-ZIP ins Profil. Gibt die Zahl der Dateien zurück."""
    anzahl = 0
    with zipfile.ZipFile(zipdatei) as z:
        namen = [n for n in z.namelist() if not n.endswith('/') and n != 'jorga-skin.txt']
        for i, name in enumerate(namen):
            # Kein Ausbrechen aus dem Profil über .. oder absolute Pfade zulassen
            sauber = os.path.normpath(name).replace('\\', '/').lstrip('/')
            if sauber.startswith('..') or os.path.isabs(name):
                log('übersprungen, Pfad verlässt das Profil: %s' % name, xbmc.LOGWARNING)
                continue
            if fortschritt:
                fortschritt.update(von + int((bis - von) * i / max(len(namen), 1)),
                                   'Dateien: %s' % os.path.basename(sauber))
                if fortschritt.iscanceled():
                    break
            ziel = os.path.join(PROFIL, sauber.replace('/', os.sep))
            if not os.path.isdir(os.path.dirname(ziel)):
                os.makedirs(os.path.dirname(ziel))
            with z.open(name) as quelle, open(ziel, 'wb') as senke:
                shutil.copyfileobj(quelle, senke)
            anzahl += 1
    return anzahl


def _kopiere_vorlage(fortschritt=None, von=0, bis=100):
    """Kopiert die mitgelieferte Vorlage ins Profil. Gibt die Zahl der Dateien zurück."""
    dateien = []
    basis = os.path.join(VORLAGE, 'userdata')
    for wurzel, _, namen in os.walk(basis):
        dateien.extend(os.path.join(wurzel, n) for n in namen)
    for i, quelle in enumerate(dateien):
        relativ = os.path.relpath(quelle, basis)
        if fortschritt:
            fortschritt.update(von + int((bis - von) * i / max(len(dateien), 1)),
                               'Dateien: %s' % os.path.basename(relativ))
            if fortschritt.iscanceled():
                break
        ziel = os.path.join(PROFIL, relativ)
        if not os.path.isdir(os.path.dirname(ziel)):
            os.makedirs(os.path.dirname(ziel))
        shutil.copy2(quelle, ziel)
    return len(dateien)


# ------------------------------------------------------------------ Skinwechsel

def setze_skin(kennung):
    """Schaltet auf einen Skin um. Gibt True zurück, wenn er danach aktiv ist.

    Kodi lässt einen Skinwechsel aus einem laufenden Add-on heraus nicht zu. Das
    ist Absicht und keine Lücke: ein Add-on, das die Oberfläche austauscht, könnte
    den Nutzer aussperren. Am Gerät (Kodi 21.2, Android) wurden alle vier Wege
    gemessen, und keiner trägt:

    1. Settings.SetSettingValue lädt den Zielskin tatsächlich - Kodi fragt 260 ms
       später nach, ob die Änderung bleiben soll, und nimmt sie nach weiteren
       200 ms unbeantwortet zurück.
    2. Diese Rückfrage ist von aussen nicht zu beantworten. Sie meldet sich nicht
       als yesnodialog, und ein Klick aus einem Add-on-Thread trifft sie nicht
       mehr rechtzeitig.
    3. Einen Builtin für den Skinwechsel gibt es nicht. SkinBuiltins.cpp kennt nur
       Skin-eigene Einstellungen und ReloadSkin.
    4. lookandfeel.skin in guisettings.xml zu schreiben hilft nicht: Kodi
       überschreibt die Datei beim Beenden mit dem Stand aus seinem Speicher
       (gemessen: skin.estuary in der Datei, nach dem Beenden wieder
       skin.mimic.lr).

    Der Versuch bleibt trotzdem drin, weil er nichts kostet und auf anderen
    Kodi-Fassungen greifen kann. Schlägt er fehl, nennt der Assistent den Weg
    über die Einstellungen - ein Klick. Beim Einrichten eines frischen Kodi
    stellt sich die Frage ohnehin nicht: dort installiert Kodi den Skin als
    Abhängigkeit dieses Pakets und fragt von selbst, ob gewechselt werden soll.
    """
    ist = rpc('Settings.GetSettingValue', setting='lookandfeel.skin')
    if ist and ist.get('value') == kennung:
        return True
    if not xbmc.getCondVisibility('System.HasAddon(%s)' % kennung):
        log('Skin %s ist nicht installiert' % kennung, xbmc.LOGWARNING)
        return False

    rpc('Settings.SetSettingValue', setting='lookandfeel.skin', value=kennung)
    for _ in range(10):
        xbmc.sleep(500)
        ist = rpc('Settings.GetSettingValue', setting='lookandfeel.skin')
        if ist and ist.get('value') == kennung:
            return True
    log('Skinwechsel auf %s nicht übernommen, aktiv bleibt %s - Kodi lässt das '
        'aus einem Add-on nicht zu' % (kennung, ist.get('value') if ist else '?'),
        xbmc.LOGINFO)
    return False


# -------------------------------------------------------------------- Hauptwege

def _lies_vorlagen_einstellungen():
    pfad = os.path.join(VORLAGE, 'einstellungen.json')
    if not os.path.isfile(pfad):
        return {}
    with open(pfad, 'r', encoding='utf-8') as f:
        return json.load(f)


def spiele_ein(nachfragen=True):
    """Spielt die mitgelieferte Einrichtung ein, nach Sicherung der bestehenden.

    Mit nachfragen=False läuft der Vorgang ohne Dialoge durch und Kodi bleibt
    anschliessend an. Dieser Weg dient dem Einrichten mehrerer Geräte und dem
    Prüfen des Assistenten; er ist über
    RunScript(script.jorga.build,einspielen,ohne-rueckfrage) erreichbar. Die
    Aktionsnamen bleiben bewusst ohne Umlaute: sie werden auf der Fernbedienung
    eingetippt.
    """
    if not os.path.isdir(os.path.join(VORLAGE, 'userdata')):
        if nachfragen:
            xbmcgui.Dialog().ok(NAME, 'Dieses Paket enthält keine Vorlage.')
        log('keine Vorlage im Paket', xbmc.LOGERROR)
        return

    if nachfragen and not xbmcgui.Dialog().yesno(
            NAME,
            'Die fertige Einrichtung wird eingespielt: Skin, Startmenü, '
            'Mediatheken und Einstellungen.[CR][CR]'
            'Deine bestehende Einrichtung wird vorher gesichert und lässt sich '
            'in diesem Assistenten jederzeit zurückholen.[CR][CR]Jetzt einspielen?',
            nolabel='Abbrechen', yeslabel='Einspielen'):
        return

    fortschritt = xbmcgui.DialogProgress() if nachfragen else None
    if fortschritt:
        fortschritt.create(NAME, 'Bestehende Einrichtung sichern ...')
    dateien, gesetzt, offen, skin_ok = 0, 0, [], False
    try:
        sicherung = sichere()
        log('gesichert nach %s' % sicherung)

        if fortschritt:
            fortschritt.update(10, 'Dateien einspielen ...')
        dateien = _kopiere_vorlage(fortschritt, 10, 45)

        if fortschritt:
            fortschritt.update(45, 'Einstellungen setzen ...')
        gesetzt, offen = setze_einstellungen(
            _lies_vorlagen_einstellungen(), fortschritt, 45, 80)

        if fortschritt:
            fortschritt.update(80, 'Skin umschalten ...')
        skin_ok = setze_skin('skin.mimic.lr')

        if fortschritt:
            fortschritt.update(95, 'Add-ons einlesen ...')
        xbmc.executebuiltin('UpdateLocalAddons')
        xbmc.sleep(1500)
    finally:
        if fortschritt:
            fortschritt.close()

    log('eingespielt: %s Dateien, %s Einstellungen, Skin %s' % (
        dateien, gesetzt, 'ok' if skin_ok else 'offen'))
    if offen:
        log('nicht gesetzt (kennt dieses Kodi nicht): %s' % ', '.join(offen))

    if not nachfragen:
        melde('Einrichtung eingespielt: %s Dateien, %s Einstellungen' % (dateien, gesetzt))
        return

    hinweis = ''
    if not skin_ok:
        hinweis = ('[CR][CR]Bleibt noch ein Schritt: Kodi lässt den Skinwechsel '
                   'aus einem Add-on heraus nicht zu. Stelle ihn einmal selbst um '
                   'unter Einstellungen > Benutzeroberfläche > Skin, Eintrag '
                   '"Mimic-LR". Das Startmenü ist dann sofort da.')
    xbmcgui.Dialog().ok(
        NAME,
        'Fertig.[CR][CR]%s Dateien eingespielt, %s Einstellungen gesetzt.%s'
        '[CR][CR]Die Sicherung deiner alten Einrichtung liegt bereit.' % (
            dateien, gesetzt, hinweis))

    if xbmcgui.Dialog().yesno(
            NAME,
            'Kodi sollte jetzt neu starten, damit alles sauber greift.[CR][CR]'
            'Jetzt beenden?', nolabel='Später', yeslabel='Beenden'):
        xbmc.executebuiltin('Quit')


def sichere_auf_wunsch():
    ziel = sichere()
    xbmcgui.Dialog().ok(NAME, 'Einrichtung gesichert:[CR][CR]%s' % ziel)


def hole_zurueck():
    """Spielt eine früher angelegte Sicherung wieder ein."""
    if not os.path.isdir(SICHERUNGEN):
        xbmcgui.Dialog().ok(NAME, 'Es gibt noch keine Sicherung.')
        return
    dateien = sorted((d for d in os.listdir(SICHERUNGEN) if d.endswith('.zip')), reverse=True)
    if not dateien:
        xbmcgui.Dialog().ok(NAME, 'Es gibt noch keine Sicherung.')
        return

    wahl = xbmcgui.Dialog().select('Welche Sicherung zurückholen?', dateien)
    if wahl < 0:
        return
    quelle = os.path.join(SICHERUNGEN, dateien[wahl])

    if not xbmcgui.Dialog().yesno(
            NAME, 'Die Einrichtung von[CR][CR]%s[CR][CR]wird wieder eingespielt. '
                  'Fortfahren?' % dateien[wahl],
            nolabel='Abbrechen', yeslabel='Zurückholen'):
        return

    fortschritt = xbmcgui.DialogProgress()
    fortschritt.create(NAME, 'Sicherung einspielen ...')
    anzahl = 0
    try:
        anzahl = _entpacke_nach_profil(quelle, fortschritt, 0, 70)
        # guisettings.xml aus der Sicherung wirkt erst nach einem Neustart: Kodi
        # hält die Einstellungen im Speicher und schreibt sie beim Beenden
        # zurück. Deshalb hier kein Setzen über JSON-RPC, sondern Neustart.
        fortschritt.update(80, 'Skin zurücksetzen ...')
        with zipfile.ZipFile(quelle) as z:
            if 'jorga-skin.txt' in z.namelist():
                alt = z.read('jorga-skin.txt').decode('utf-8').strip()
                if alt:
                    setze_skin(alt)
    finally:
        fortschritt.close()

    xbmcgui.Dialog().ok(
        NAME, '%s Dateien zurückgeholt.[CR][CR]Kodi muss neu starten, damit die '
              'Einstellungen aus der Sicherung greifen.' % anzahl)
    if xbmcgui.Dialog().yesno(NAME, 'Kodi jetzt beenden?',
                              nolabel='Später', yeslabel='Beenden'):
        xbmc.executebuiltin('Quit')


def zeige_inhalt():
    """Listet auf, was das Paket einspielt - vor dem Einspielen nachlesbar."""
    werte = _lies_vorlagen_einstellungen()
    dateien = []
    basis = os.path.join(VORLAGE, 'userdata')
    for wurzel, _, namen in os.walk(basis):
        dateien.extend(os.path.relpath(os.path.join(wurzel, n), basis) for n in namen)

    zeilen = [
        'Skin: Mimic-LR mit fertigem Startmenü',
        'Mediatheken: ARD, ZDF, SRF Play, ARTE, 3sat',
        'Dazu: YouTube, TMDb-Helper, globale Suche',
        '',
        '%s Konfigurationsdateien:' % len(dateien),
    ]
    zeilen += ['  ' + d.replace(os.sep, '/') for d in sorted(dateien)]
    zeilen += ['', '%s Kodi-Einstellungen, darunter:' % len(werte)]
    zeilen += ['  %s = %s' % (k, v) for k, v in sorted(werte.items())[:12]]
    if len(werte) > 12:
        zeilen.append('  ... und %s weitere' % (len(werte) - 12))
    zeilen += ['', 'Nicht angetastet: deine Videoquellen, die Medienbibliothek',
               'und bereits installierte Add-ons.']
    xbmcgui.Dialog().textviewer('Was dieses Paket einspielt', '\n'.join(zeilen))

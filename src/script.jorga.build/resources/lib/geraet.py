"""Überträgt ein ganzes Kodi-Gerät auf ein anderes: Add-ons und Konfiguration.

Der Unterschied zu einrichtung.py: dort liegt die mitgelieferte, feste Vorlage
dieses Pakets. Hier geht es um ein **beliebiges** Gerät, das sich selbst
beschreibt und auf einem anderen wieder entsteht.

Ein Paket ist eine einzige ZIP-Datei:

    paket.json        Add-on-Kennungen, Bezugsquellen, Einstellungen, Skin
    userdata/...      Startmenü, Favoriten, Quellen, Skin-Einstellungen

Was bewusst **nicht** darin liegt, sind die Add-ons selbst. Ein gewachsenes
Gerät trägt schnell ein halbes Gigabyte davon, und mitgelieferte Fassungen
veralten ab dem Tag des Packens. Stattdessen stehen im Paket die Kataloge, aus
denen die Add-ons stammen; das Zielgerät lädt daraus die jeweils aktuelle
Fassung. Ein Paket bleibt dadurch wenige hundert Kilobyte gross.

Die Kehrseite, offen benannt: Verschwindet eine Fremdquelle, fehlt das
betreffende Add-on. Der Assistent meldet genau diese Fälle, statt sie zu
verschweigen, und spielt alles Übrige trotzdem ein.
"""

import json
import os
import shutil
import time
import zipfile

import xbmc
import xbmcgui

import einrichtung
import paket

from einrichtung import NAME, PROFIL, SICHERUNGEN, log


def _quelle_erfragen():
    """Fragt, woher ein Paket kommt. Gibt Pfad oder Adresse, sonst None."""
    wege = ['Datei suchen (Gerät, USB-Stick oder Netzwerk)',
            'Adresse eingeben (http:// oder smb://)']
    wahl = xbmcgui.Dialog().select('Woher kommt das Paket?', wege)
    if wahl == 0:
        return xbmcgui.Dialog().browseSingle(1, 'Paketdatei wählen', 'files', '.zip') or None
    if wahl == 1:
        return xbmcgui.Dialog().input('Adresse der Paketdatei') or None
    return None


# ------------------------------------------------------- Dieses Gerät erfassen

def erzeuge(ziel=None, name=None, fortschritt=None, mit_luecken=True):
    """Schreibt das laufende Gerät als Paket weg. Gibt (Pfad, Beschreibung).

    Mit mit_luecken=True werden die Kataloge einmal gelesen, um zu sehen, welche
    Add-ons aus keiner Quelle mehr zu beziehen sind - verwaiste Add-ons, deren
    Repository verschwunden ist. Genau die kommen als ZIP mit ins Paket. Alle
    übrigen bleiben draussen und werden auf dem Zielgerät frisch geladen.
    Das kostet beim Erfassen eine Minute und macht das Paket vollständig.
    """
    if not os.path.isdir(SICHERUNGEN):
        os.makedirs(SICHERUNGEN)
    ziel = ziel or os.path.join(
        SICHERUNGEN, 'geraet-%s.zip' % time.strftime('%Y%m%d-%H%M%S'))

    if fortschritt:
        fortschritt.update(5, 'Gerät erfassen ...')
    beschreibung = paket.erfasse_geraet(PROFIL, name)

    luecken = []
    if mit_luecken:
        if fortschritt:
            fortschritt.update(10, 'Bezugsquellen prüfen ...')
        angebot, ausgefallen = paket.sammle_kataloge(
            beschreibung['kataloge'], fortschritt, 10, 55)
        luecken = [a for a in beschreibung['addons']
                   if a not in angebot and os.path.isdir(
                       os.path.join(paket.ADDONS, a))]
        beschreibung['quellen_ausgefallen'] = ausgefallen
        beschreibung['mitgeliefert'] = luecken
        if ausgefallen:
            log('beim Erfassen nicht erreichbar: %s' % ', '.join(ausgefallen),
                xbmc.LOGWARNING)

    with zipfile.ZipFile(ziel, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr(paket.PAKET_DATEI,
                   json.dumps(beschreibung, indent=2, ensure_ascii=False))
        for absolut, relativ in einrichtung._konfig_pfade():
            z.write(absolut, 'userdata/' + relativ.replace(os.sep, '/'))
        for i, kennung in enumerate(luecken):
            if fortschritt:
                fortschritt.update(60 + int(35 * i / max(len(luecken), 1)),
                                   'Mitnehmen: %s' % kennung)
            try:
                z.writestr('addons/%s.zip' % kennung, paket.packe_addon(kennung))
            except Exception as problem:
                log('%s nicht einpackbar: %s' % (kennung, problem), xbmc.LOGWARNING)

    log('Gerät erfasst: %s (%s Add-ons, davon %s mitgeliefert, %s Einstellungen)'
        % (ziel, len(beschreibung['addons']), len(luecken),
           len(beschreibung['einstellungen'])))
    return ziel, beschreibung


def erzeuge_auf_wunsch():
    fortschritt = xbmcgui.DialogProgress()
    fortschritt.create(NAME, 'Gerät erfassen ...')
    try:
        ziel, beschreibung = erzeuge(fortschritt=fortschritt)
    finally:
        fortschritt.close()

    groesse = os.path.getsize(ziel) // 1024
    zeilen = ['%s Add-ons, %s Einstellungen, %s Bezugsquellen.' % (
        len(beschreibung['addons']), len(beschreibung['einstellungen']),
        len(beschreibung['kataloge']))]
    if beschreibung.get('mitgeliefert'):
        zeilen.append('%s Add-ons sind aus keiner Quelle mehr zu bekommen und '
                      'reisen deshalb im Paket mit.' % len(beschreibung['mitgeliefert']))
    if beschreibung.get('quellen_ausgefallen'):
        zeilen.append('Nicht erreichbar beim Prüfen: %s'
                      % ', '.join(beschreibung['quellen_ausgefallen']))
    zeilen += ['', '%s (%s KB)' % (ziel, groesse), '',
               'Diese eine Datei auf das neue Gerät bringen und dort '
               '"Gerät aus Paket einrichten" wählen.']
    xbmcgui.Dialog().ok(NAME, 'Dieses Gerät ist als Paket gesichert.[CR][CR]'
                              + '[CR]'.join(zeilen))


# ----------------------------------------------------------- Paket einspielen

def _konfiguration_einspielen(zipdatei, ordner, fortschritt=None, von=85, bis=92):
    """Spielt den userdata-Teil eines Pakets ins Profil. Gibt die Zahl Dateien."""
    if zipdatei is None:                         # entpackter Ordner statt ZIP
        basis = os.path.join(ordner, 'userdata')
        anzahl = 0
        for wurzel, _, namen in os.walk(basis):
            for n in namen:
                quelle = os.path.join(wurzel, n)
                ziel = os.path.join(PROFIL, os.path.relpath(quelle, basis))
                os.makedirs(os.path.dirname(ziel), exist_ok=True)
                shutil.copy2(quelle, ziel)
                anzahl += 1
        return anzahl

    anzahl = 0
    with zipfile.ZipFile(zipdatei) as z:
        namen = [n for n in z.namelist()
                 if n.startswith('userdata/') and not n.endswith('/')]
        for i, name in enumerate(namen):
            # Kein Ausbrechen aus dem Profil über .. oder absolute Pfade
            rest = name[len('userdata/'):]
            sauber = os.path.normpath(rest).replace('\\', '/').lstrip('/')
            if not sauber or sauber.startswith('..') or os.path.isabs(rest):
                log('übersprungen, Pfad verlässt das Profil: %s' % name, xbmc.LOGWARNING)
                continue
            if fortschritt:
                fortschritt.update(von + int((bis - von) * i / max(len(namen), 1)),
                                   'Konfiguration: %s' % os.path.basename(sauber))
            ziel = os.path.join(PROFIL, sauber.replace('/', os.sep))
            os.makedirs(os.path.dirname(ziel), exist_ok=True)
            with z.open(name) as quelle, open(ziel, 'wb') as senke:
                shutil.copyfileobj(quelle, senke)
            anzahl += 1
    return anzahl


def spiele_ein(quelle=None, nachfragen=True):
    """Richtet dieses Gerät nach einem Paket ein.

    Reihenfolge und ihr Grund:
      1. Bestehendes sichern - der Weg zurück muss offen bleiben.
      2. Kataloge lesen, Abhängigkeiten auflösen, Add-ons laden. Zuerst, weil
         die Konfiguration sich auf Add-ons bezieht, die es dann schon gibt.
      3. Konfigurationsdateien ins Profil.
      4. Einstellungen über JSON-RPC - eine kopierte guisettings.xml würde Kodi
         beim Beenden mit dem Stand aus dem Speicher überschreiben.
      5. Die erzeugte Menüdatei des Skins löschen, damit das Startmenü aus den
         eingespielten Dateien neu entsteht, und zum Neustart raten.
    """
    if quelle is None:
        quelle = _quelle_erfragen()
    if not quelle:
        return None

    fortschritt = xbmcgui.DialogProgress() if nachfragen else None
    if fortschritt:
        fortschritt.create(NAME, 'Paket lesen ...')
    bericht = {}
    try:
        lokal = paket.hole_paket(quelle, os.path.join(SICHERUNGEN, 'geladen'))
        beschreibung, zipdatei = paket.lies_paket(lokal)

        if nachfragen:
            fortschritt.close()
            fortschritt = None
            if not xbmcgui.Dialog().yesno(
                    NAME,
                    '%s[CR]erstellt am %s[CR][CR]%s Add-ons, %s Einstellungen.[CR][CR]'
                    'Vorhandene Add-ons bleiben, fehlende werden nachgeladen. '
                    'Deine jetzige Einrichtung wird vorher gesichert.[CR][CR]'
                    'Jetzt einrichten?' % (
                        beschreibung.get('name', 'Paket'),
                        beschreibung.get('erstellt', '?'),
                        len(beschreibung.get('addons', [])),
                        len(beschreibung.get('einstellungen', {}))),
                    nolabel='Abbrechen', yeslabel='Einrichten'):
                return None
            fortschritt = xbmcgui.DialogProgress()
            fortschritt.create(NAME, 'Bestehende Einrichtung sichern ...')

        bericht['sicherung'] = einrichtung.sichere()

        angebot, ausgefallen = paket.sammle_kataloge(
            beschreibung.get('kataloge', []), fortschritt, 2, 15)

        # Zuerst die mitgereisten Add-ons: sie stehen in keinem Katalog, und
        # andere Add-ons können von ihnen abhängen.
        mitgeliefert = paket.entpacke_mitgelieferte(zipdatei, fortschritt, 16)

        reihenfolge, unauffindbar = paket.loese_auf(
            beschreibung.get('addons', []), angebot, mitgeliefert)
        neu, schon_da, fehler = paket.installiere(
            reihenfolge, angebot, fortschritt, 18, 80)
        bericht.update(ausgefallen=ausgefallen, unauffindbar=unauffindbar,
                       neu=neu, schon_da=schon_da, fehler=fehler,
                       mitgeliefert=mitgeliefert)

        if neu or mitgeliefert:
            paket.einlesen(list(neu) + list(mitgeliefert), fortschritt, 82)

        if fortschritt:
            fortschritt.update(85, 'Konfiguration einspielen ...')
        bericht['dateien'] = _konfiguration_einspielen(
            zipdatei, lokal, fortschritt, 85, 92)

        gesetzt, offen = einrichtung.setze_einstellungen(
            beschreibung.get('einstellungen', {}), fortschritt, 92, 98)
        bericht.update(gesetzt=gesetzt, offen=offen)

        haut = beschreibung.get('skin', '')
        paket.menue_neu_bauen_lassen(haut)
        bericht['skin_ok'] = einrichtung.setze_skin(haut) if haut else False
    except Exception as problem:
        log('Paket nicht eingespielt: %s' % problem, xbmc.LOGERROR)
        bericht['abbruch'] = str(problem)
    finally:
        if fortschritt:
            fortschritt.close()

    _ergebnis_melden(bericht, nachfragen)
    return bericht


def _ergebnis_melden(bericht, nachfragen):
    """Schreibt das Ergebnis ins Log und zeigt es, wenn jemand davorsitzt."""
    if 'abbruch' in bericht:
        if nachfragen:
            xbmcgui.Dialog().ok(NAME, 'Das Paket liess sich nicht einspielen:'
                                      '[CR][CR]%s' % bericht['abbruch'])
        return

    log('Paket eingespielt: %s neu, %s vorhanden, %s Dateien, %s Einstellungen' % (
        len(bericht.get('neu', [])), len(bericht.get('schon_da', [])),
        bericht.get('dateien', 0), bericht.get('gesetzt', 0)))
    for schluessel, text in (('fehler', 'nicht installierbar'),
                             ('unauffindbar', 'in keinem Katalog gefunden'),
                             ('ausgefallen', 'Katalog nicht erreichbar'),
                             ('offen', 'Einstellung unbekannt')):
        if bericht.get(schluessel):
            log('%s: %s' % (text, bericht[schluessel]), xbmc.LOGWARNING)

    if not nachfragen:
        einrichtung.melde('Paket eingespielt: %s Add-ons, %s Dateien' % (
            len(bericht.get('neu', [])), bericht.get('dateien', 0)))
        return

    zeilen = ['%s Add-ons nachgeladen, %s waren schon da.' % (
        len(bericht.get('neu', [])), len(bericht.get('schon_da', []))),
        '%s Konfigurationsdateien, %s Einstellungen gesetzt.' % (
            bericht.get('dateien', 0), bericht.get('gesetzt', 0))]
    if bericht.get('mitgeliefert'):
        zeilen.append('%s davon kamen aus dem Paket selbst - ihre Quelle gibt '
                      'es nicht mehr.' % len(bericht['mitgeliefert']))
    if bericht.get('fehler'):
        zeilen.append('%s Add-ons kamen nicht durch (Einzelheiten im Log).'
                      % len(bericht['fehler']))
    if bericht.get('unauffindbar'):
        zeilen.append('%s stehen in keinem Katalog: %s' % (
            len(bericht['unauffindbar']), ', '.join(bericht['unauffindbar'][:4])))
    if bericht.get('ausgefallen'):
        zeilen.append('Quelle nicht erreichbar: %s' % ', '.join(bericht['ausgefallen']))
    if not bericht.get('skin_ok'):
        zeilen += ['', 'Noch ein Schritt von Hand: Kodi lässt den Skinwechsel aus '
                       'einem Add-on nicht zu. Einstellungen > Benutzeroberfläche '
                       '> Skin umstellen.']
    xbmcgui.Dialog().ok(NAME, 'Fertig.[CR][CR]' + '[CR]'.join(zeilen))

    if xbmcgui.Dialog().yesno(
            NAME, 'Kodi muss neu starten, damit Add-ons und Startmenü greifen.'
                  '[CR][CR]Jetzt beenden?', nolabel='Später', yeslabel='Beenden'):
        xbmc.executebuiltin('Quit')


def zeige_paket(quelle=None):
    """Zeigt, was ein Paket enthält - nachlesbar vor dem Einspielen."""
    if quelle is None:
        quelle = _quelle_erfragen()
    if not quelle:
        return
    try:
        lokal = paket.hole_paket(quelle, os.path.join(SICHERUNGEN, 'geladen'))
        beschreibung, _ = paket.lies_paket(lokal)
    except Exception as problem:
        xbmcgui.Dialog().ok(NAME, 'Paket nicht lesbar:[CR][CR]%s' % problem)
        return

    zeilen = ['%s' % beschreibung.get('name', 'Paket'),
              'erstellt am %s mit Kodi %s' % (beschreibung.get('erstellt', '?'),
                                              beschreibung.get('kodi', '?')),
              'Skin: %s' % (beschreibung.get('skin') or 'keiner'), '',
              'Bezugsquellen (%s):' % len(beschreibung.get('kataloge', []))]
    zeilen += ['  %s' % k.get('id', k.get('addons_xml'))
               for k in beschreibung.get('kataloge', [])]
    zeilen += ['', 'Add-ons (%s):' % len(beschreibung.get('addons', []))]
    zeilen += ['  %s' % a for a in beschreibung.get('addons', [])]
    zeilen += ['', 'Einstellungen (%s):' % len(beschreibung.get('einstellungen', {}))]
    zeilen += ['  %s = %s' % (k, v)
               for k, v in sorted(beschreibung.get('einstellungen', {}).items())]
    if beschreibung.get('nicht_uebernommen'):
        zeilen += ['', 'Bewusst nicht im Paket (hängt am Gerät):']
        zeilen += ['  %s' % n for n in beschreibung['nicht_uebernommen']]
    xbmcgui.Dialog().textviewer('Inhalt des Pakets', '\n'.join(zeilen))

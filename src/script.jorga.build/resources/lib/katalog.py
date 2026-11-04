"""Das Build-Angebot: fertige Einrichtungen, die im Netz liegen.

Bis hierher brauchte der Assistent eine Paketdatei in der Hand - auf einem
USB-Stick, im Netzwerk oder als eingetippte Adresse. Das ist für ein eigenes
Gerät in Ordnung und für ein fremdes unbrauchbar: niemand tippt eine
Repository-Adresse auf einer Fernbedienung ein.

Ein Katalog löst das. Er ist eine einzige JSON-Datei im Netz und nennt die
verfügbaren Builds mit Namen, Stand und Adresse:

    {
      "katalog": "Jorga Builds",
      "builds": [
        {"name": "Jorga Standard",
         "kurz": "Mediatheken, Skin Mimic-LR, fertiges Startmenü",
         "adresse": "https://.../jorga-standard-1.0.0.zip",
         "stand": "2026-11-04",
         "bytes": 24576,
         "kodi_min": 19,
         "kodi_max": 22}
      ]
    }

Der Assistent zeigt daraus eine Liste, lädt das gewählte Paket und spielt es
ein - drei Tastendrücke statt einer Adresse.

**Zwei Kataloge, bewusst getrennt.** Fest eingebaut ist der öffentliche
Katalog dieses Projekts; er führt nur Builds, die ausschliesslich aus legalen
Quellen bestehen. Daneben lässt sich in den Einstellungen des Assistenten ein
**eigener** Katalog eintragen - eine Adresse auf dem eigenen Speicher, dem
NAS oder einem privaten Webserver. Wer sein eigenes Gerät auf mehrere Geräte
bringen will, legt sein Paket dorthin und trägt die Adresse einmal ein. Was
dort steht, bleibt bei ihm; dieses Projekt verbreitet es nicht.

Der Stand des eingespielten Builds wird im Profil vermerkt
(jorga-build.json). Daran erkennt der Dienst später, ob im Katalog eine
neuere Fassung steht, und sagt es - ohne etwas von allein zu verändern.
"""

import json
import os
import time

import xbmc
import xbmcaddon
import xbmcgui

import einrichtung
import paket

from einrichtung import NAME, PROFIL, log


# Der öffentliche Katalog dieses Projekts. Bewusst auf den main-Zweig, damit
# ein neuer Build ohne neue Add-on-Fassung sichtbar wird.
STANDARD_KATALOG = ('https://raw.githubusercontent.com/JorgaWetzel/kodi-addons'
                    '/main/repo/builds.json')

# Vermerk über den eingespielten Build. Liegt im Profil, nicht im Add-on-Ordner:
# eine Neuinstallation des Assistenten soll ihn nicht verlieren.
VERMERK = os.path.join(PROFIL, 'jorga-build.json')

MAX_KATALOG = 1024 * 1024


def _einstellung(name, standard=''):
    try:
        return xbmcaddon.Addon().getSetting(name) or standard
    except Exception:                      # Add-on ohne settings.xml
        return standard


def adressen():
    """Die Kataloge, die gefragt werden: der öffentliche und der eigene."""
    liste = [STANDARD_KATALOG]
    eigener = _einstellung('eigener_katalog').strip()
    if eigener and eigener not in liste:
        liste.append(eigener)
    return liste


def lies(adresse):
    """Liest einen Katalog. Gibt die Liste der Builds zurück."""
    roh = paket._hole(adresse, MAX_KATALOG)
    inhalt = json.loads(roh.decode('utf-8'))
    builds = inhalt.get('builds', [])
    if not isinstance(builds, list):
        raise ValueError('builds ist keine Liste')
    for b in builds:
        b.setdefault('katalog', inhalt.get('katalog', adresse))
        # Eine relative Adresse bezieht sich auf den Ort des Katalogs. Das
        # erlaubt, Katalog und Pakete zusammen zu verschieben.
        if b.get('adresse') and '://' not in b['adresse']:
            b['adresse'] = adresse.rsplit('/', 1)[0] + '/' + b['adresse'].lstrip('/')
    return builds


def sammle():
    """Alle Kataloge lesen. Gibt (Builds, nicht erreichbare Adressen)."""
    builds, ausgefallen = [], []
    for adresse in adressen():
        try:
            builds.extend(lies(adresse))
        except Exception as problem:
            log('Katalog nicht lesbar (%s): %s' % (adresse, problem), xbmc.LOGWARNING)
            ausgefallen.append(adresse)
    return builds, ausgefallen


def _kodi_hauptversion():
    try:
        return int(xbmc.getInfoLabel('System.BuildVersion').split('.')[0])
    except (ValueError, IndexError):
        return 0


def passt(build, hauptversion=None):
    """True, wenn der Build für die laufende Kodi-Fassung gedacht ist.

    Fehlt die Angabe im Katalog, gilt der Build als passend: ein Paket nennt
    nur Kataloge und Kennungen und ist dadurch meist fassungsübergreifend.
    """
    version = hauptversion or _kodi_hauptversion()
    if not version:
        return True
    unten, oben = build.get('kodi_min'), build.get('kodi_max')
    if unten and version < int(unten):
        return False
    if oben and version > int(oben):
        return False
    return True


def _zeile(build):
    teile = [build.get('name', 'Build')]
    if build.get('stand'):
        teile.append(build['stand'])
    if build.get('bytes'):
        teile.append('%d KB' % (int(build['bytes']) // 1024))
    kopf = '   '.join(teile)
    if not passt(build):
        kopf += '   (für Kodi %s-%s)' % (build.get('kodi_min', '?'),
                                         build.get('kodi_max', '?'))
    return kopf


def waehle(nur_passende=True):
    """Zeigt das Angebot und gibt den gewählten Build zurück, sonst None."""
    fortschritt = xbmcgui.DialogProgress()
    fortschritt.create(NAME, 'Angebot abrufen ...')
    try:
        builds, ausgefallen = sammle()
    finally:
        fortschritt.close()

    if nur_passende:
        builds = [b for b in builds if passt(b)]
    if not builds:
        text = 'Im Angebot steht derzeit kein Build für diese Kodi-Fassung.'
        if ausgefallen:
            text += '[CR][CR]Nicht erreichbar:[CR]%s' % '[CR]'.join(ausgefallen)
        text += ('[CR][CR]Ein eigener Katalog lässt sich in den Einstellungen '
                 'dieses Add-ons eintragen.')
        xbmcgui.Dialog().ok(NAME, text)
        return None

    eintraege = [_zeile(b) for b in builds]
    wahl = xbmcgui.Dialog().select('Welche Einrichtung?', eintraege,
                                   useDetails=False)
    return builds[wahl] if wahl >= 0 else None


def einrichten():
    """Build aus dem Angebot wählen und einspielen."""
    import geraet                          # erst hier: geraet nutzt katalog

    build = waehle()
    if not build:
        return None
    if not build.get('adresse'):
        xbmcgui.Dialog().ok(NAME, '%s nennt keine Adresse - der Katalog ist '
                                  'unvollständig.' % build.get('name', 'Der Build'))
        return None

    hinweis = build.get('kurz', '')
    antwort = xbmcgui.Dialog().yesnocustom(
        NAME, '%s%s[CR][CR]Stand %s%s[CR][CR]Das Paket wird geladen und '
              'eingespielt. Deine jetzige Einrichtung wird vorher '
              'gesichert.[CR][CR]"Frisch" entfernt die bisherige Einrichtung '
              'zuerst - richtig für ein Gerät, das jemand anders '
              'eingerichtet hat.' % (
                  build.get('name', 'Build'),
                  '[CR]' + hinweis if hinweis else '',
                  build.get('stand', 'unbekannt'),
                  '[CR]%d KB' % (int(build['bytes']) // 1024)
                  if build.get('bytes') else ''),
        customlabel='Frisch einrichten',
        nolabel='Abbrechen', yeslabel='Einrichten')
    if antwort not in (1, 2):
        return None

    bericht = geraet.spiele_ein(build['adresse'], nachfragen=True,
                                vorab_bestaetigt=True, frisch=(antwort == 2))
    if bericht and 'abbruch' not in bericht:
        vermerke(build)
    return bericht


def zeige():
    """Was steckt in einem Build aus dem Angebot?"""
    import geraet

    build = waehle(nur_passende=False)
    if build and build.get('adresse'):
        geraet.zeige_paket(build['adresse'])


# ------------------------------------------------- Stand des eigenen Geräts

def vermerke(build):
    """Hält fest, welcher Build hier eingespielt wurde."""
    try:
        with open(VERMERK, 'w', encoding='utf-8') as f:
            json.dump({'name': build.get('name', ''),
                       'stand': build.get('stand', ''),
                       'adresse': build.get('adresse', ''),
                       'eingespielt': time.strftime('%Y-%m-%d %H:%M')},
                      f, indent=2, ensure_ascii=False)
    except Exception as problem:
        log('Vermerk nicht geschrieben: %s' % problem, xbmc.LOGWARNING)


def eingespielter_build():
    """Der Vermerk über den eingespielten Build, oder None."""
    try:
        with open(VERMERK, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


def neuerer_stand():
    """Gibt den Build zurück, wenn im Katalog ein neuerer Stand steht.

    Verglichen werden Datumsangaben als Text - "2026-11-04" ist in dieser
    Schreibweise richtig sortierbar. Ohne Stand im Katalog gibt es nichts zu
    melden: eine Meldung ohne Datum wäre bei jedem Start dieselbe.
    """
    vermerk = eingespielter_build()
    if not vermerk or not vermerk.get('stand'):
        return None
    builds, _ = sammle()
    for b in builds:
        if b.get('name') == vermerk['name'] and b.get('stand', '') > vermerk['stand']:
            return b
    return None


def zeige_stand():
    """Was ist hier eingespielt, und gibt es Neueres?"""
    vermerk = eingespielter_build()
    if not vermerk:
        xbmcgui.Dialog().ok(NAME, 'Auf diesem Gerät wurde noch kein Build aus '
                                  'dem Angebot eingespielt.')
        return
    zeilen = ['%s' % vermerk.get('name', '?'),
              'Stand %s' % (vermerk.get('stand') or 'unbekannt'),
              'eingespielt am %s' % (vermerk.get('eingespielt') or '?')]
    neuer = neuerer_stand()
    zeilen += ['', 'Im Angebot steht Stand %s.' % neuer['stand'] if neuer
               else '', 'Das ist der neueste Stand im Angebot.' if not neuer else '']
    xbmcgui.Dialog().ok(NAME, '[CR]'.join(z for z in zeilen if z != ''))
    if neuer and xbmcgui.Dialog().yesno(NAME, 'Den neueren Stand jetzt '
                                              'einspielen?',
                                        nolabel='Später', yeslabel='Einspielen'):
        import geraet
        bericht = geraet.spiele_ein(neuer['adresse'], nachfragen=True,
                                    vorab_bestaetigt=True)
        if bericht and 'abbruch' not in bericht:
            vermerke(neuer)


# ------------------------------------------------------- Eigenen Katalog setzen

def eigenen_katalog_eintragen():
    """Fragt die Adresse eines eigenen Katalogs ab und speichert sie."""
    vorher = _einstellung('eigener_katalog')
    neu = xbmcgui.Dialog().input(
        'Adresse der eigenen builds.json', defaultt=vorher)
    if neu is None:
        return
    neu = neu.strip()
    try:
        xbmcaddon.Addon().setSetting('eigener_katalog', neu)
    except Exception as problem:
        xbmcgui.Dialog().ok(NAME, 'Einstellung nicht gespeichert:[CR][CR]%s' % problem)
        return
    if not neu:
        einrichtung.melde('Eigener Katalog entfernt')
        return
    try:
        anzahl = len(lies(neu))
        xbmcgui.Dialog().ok(NAME, 'Katalog erreichbar: %s Build(s).' % anzahl)
    except Exception as problem:
        xbmcgui.Dialog().ok(NAME, 'Gespeichert, aber derzeit nicht lesbar:'
                                  '[CR][CR]%s' % problem)

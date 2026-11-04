"""Der Dienst: lädt auf einem noch nicht eingerichteten Gerät zum Einrichten ein.

Ein Assistent, den man erst unter Add-ons suchen muss, hilft genau dort nicht,
wo er gebraucht wird: auf einem frischen Gerät, das jemand einrichten soll, der
sich mit Kodi nicht auskennt. Deshalb meldet sich der Assistent nach der
Installation von selbst - einmal.

Drei Bedingungen müssen dafür zusammenkommen, und jede hat ihren Grund:

* **Noch nichts eingerichtet.** Gibt es eine eigene Sicherung oder den Vermerk
  über einen eingespielten Build, kennt der Nutzer den Assistenten - dann hat
  ein Dialog beim Start nichts zu suchen.
* **Heute noch nicht gefragt.** Wer "Später" wählt, soll nicht bei jedem Start
  erneut gefragt werden.
* **In den Einstellungen nicht abgeschaltet.** "Nicht mehr fragen" schaltet die
  Einladung dauerhaft aus.

Dazu weist der Dienst darauf hin, wenn im Katalog ein neuerer Stand des
eingespielten Builds steht. Nur als Benachrichtigung, und nur einmal am Tag:
Eingespielt wird nichts von allein - ein Gerät, das sich hinter dem Rücken
seines Besitzers umbaut, ist kaputt, nicht gepflegt.
"""

import json
import os
import sys
import time

import xbmc
import xbmcaddon
import xbmcgui

ADDON = xbmcaddon.Addon()
sys.path.insert(0, os.path.join(ADDON.getAddonInfo('path'), 'resources', 'lib'))

import einrichtung  # noqa: E402  - erst nach dem Pfad möglich
import katalog      # noqa: E402

# Wartezeit, bevor sich der Dienst meldet. Kodi lädt beim Start Skin, Add-ons
# und Datenbanken; ein Dialog mitten hinein wird vom Skin überdeckt oder
# verschluckt. 30 Sekunden reichen auch auf einem Android-Fernsehgerät.
ANLAUF = 30

VERMERK = os.path.join(einrichtung.PROFIL, 'jorga-dienst.json')


def _vermerk():
    try:
        with open(VERMERK, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def _vermerke(**werte):
    inhalt = _vermerk()
    inhalt.update(werte)
    try:
        with open(VERMERK, 'w', encoding='utf-8') as f:
            json.dump(inhalt, f, indent=2, ensure_ascii=False)
    except Exception as problem:
        einrichtung.log('Dienstvermerk nicht geschrieben: %s' % problem,
                        xbmc.LOGWARNING)


def _ja(name, standard=True):
    wert = ADDON.getSetting(name)
    return standard if wert == '' else wert == 'true'


def _schon_eingerichtet():
    """True, wenn auf diesem Gerät schon mit dem Assistenten gearbeitet wurde."""
    return (os.path.isdir(einrichtung.SICHERUNGEN)
            or os.path.isfile(katalog.VERMERK))


def _einladen():
    """Fragt einmal, ob das Gerät jetzt eingerichtet werden soll."""
    heute = time.strftime('%Y-%m-%d')
    if _vermerk().get('gefragt') == heute:
        return
    _vermerke(gefragt=heute)

    antwort = xbmcgui.Dialog().yesnocustom(
        einrichtung.NAME,
        'Dieses Gerät ist noch nicht eingerichtet.[CR][CR]Der Assistent kann '
        'eine fertige Einrichtung einspielen: Add-ons, Startmenü und '
        'Einstellungen in einem Zug.[CR][CR]Jetzt einrichten?',
        customlabel='Nicht mehr fragen', nolabel='Später', yeslabel='Einrichten')

    if antwort == 2:
        ADDON.setSetting('beim_start_fragen', 'false')
        einrichtung.melde('Verstanden - der Assistent bleibt still.')
    elif antwort == 1:
        katalog.einrichten()


def _auf_neuen_stand_hinweisen():
    """Meldet, wenn im Katalog ein neuerer Stand des Builds steht."""
    heute = time.strftime('%Y-%m-%d')
    if _vermerk().get('stand_geprueft') == heute:
        return
    _vermerke(stand_geprueft=heute)
    try:
        neuer = katalog.neuerer_stand()
    except Exception as problem:           # kein Netz, kaputter Katalog
        einrichtung.log('Standprüfung nicht möglich: %s' % problem, xbmc.LOGDEBUG)
        return
    if neuer:
        einrichtung.melde('Neuer Stand verfügbar: %s (%s)'
                          % (neuer.get('name', '?'), neuer.get('stand', '?')),
                          zeit=8000)
        einrichtung.log('neuer Build-Stand im Katalog: %s %s'
                        % (neuer.get('name'), neuer.get('stand')))


def main():
    monitor = xbmc.Monitor()
    if monitor.waitForAbort(ANLAUF):       # Kodi beendet sich schon wieder
        return

    if not _schon_eingerichtet():
        if _ja('beim_start_fragen'):
            _einladen()
        return

    if _ja('auf_stand_hinweisen') and os.path.isfile(katalog.VERMERK):
        _auf_neuen_stand_hinweisen()


if __name__ == '__main__':
    main()

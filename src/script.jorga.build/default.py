"""Einstiegspunkt des Einrichtungsassistenten.

Liegt in Kodi unter Add-ons > Programm-Add-ons > "Jorga Build".
Die Arbeit selbst steckt in resources/lib/einrichtung.py.

Ohne Parameter erscheint das Auswahlmenü. Mit Parameter laufen die Schritte
direkt, was das Einrichten mehrerer Geräte erlaubt:

    RunScript(script.jorga.build,einspielen)
    RunScript(script.jorga.build,einspielen,ohne-rueckfrage)
    RunScript(script.jorga.build,sichern)
    RunScript(script.jorga.build,skin,skin.mimic.lr)
"""

import os
import sys

import xbmcaddon
import xbmcgui

sys.path.insert(0, os.path.join(
    xbmcaddon.Addon().getAddonInfo('path'), 'resources', 'lib'))

import einrichtung  # noqa: E402  - erst nach dem Pfad möglich

MENUE = [
    ('Einrichtung einspielen', einrichtung.spiele_ein),
    ('Was wird eingespielt?', einrichtung.zeige_inhalt),
    ('Eigene Einrichtung sichern', einrichtung.sichere_auf_wunsch),
    ('Sicherung zurückholen', einrichtung.hole_zurueck),
]


def main():
    args = sys.argv[1:]
    if args:
        aktion = args[0]
        ohne_rueckfrage = 'ohne-rueckfrage' in args
        if aktion == 'einspielen':
            einrichtung.spiele_ein(nachfragen=not ohne_rueckfrage)
        elif aktion == 'sichern':
            einrichtung.sichere_auf_wunsch()
        elif aktion == 'zurueckholen':
            einrichtung.hole_zurueck()
        elif aktion == 'skin':
            kennung = args[1] if len(args) > 1 else 'skin.mimic.lr'
            einrichtung.log('Skinwechsel auf %s: %s' % (
                kennung, 'erreicht' if einrichtung.setze_skin(kennung) else 'nicht erreicht'))
        else:
            einrichtung.log('unbekannte Aktion: %s' % aktion)
        return

    wahl = xbmcgui.Dialog().select(einrichtung.NAME, [e[0] for e in MENUE])
    if wahl >= 0:
        MENUE[wahl][1]()


if __name__ == '__main__':
    main()

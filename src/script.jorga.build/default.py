"""Einstiegspunkt des Einrichtungsassistenten.

Liegt in Kodi unter Add-ons > Programm-Add-ons > "Jorga Build".

Der Assistent kann zweierlei, und das sind verschiedene Dinge:

* **Die mitgelieferte Einrichtung** einspielen (resources/lib/einrichtung.py).
  Sie steckt fest in diesem Paket: Skin, Startmenü, Mediatheken, Einstellungen.
* **Ein ganzes Gerät übertragen** (resources/lib/geraet.py). Dabei beschreibt
  ein bestehendes Gerät sich selbst in einer Paketdatei, und ein anderes baut
  sich danach auf - mit seinen Add-ons, seinem Menü, seinen Einstellungen.

Ohne Parameter erscheint das Auswahlmenü. Mit Parameter laufen die Schritte
direkt durch, was das Einrichten mehrerer Geräte erlaubt:

    RunScript(script.jorga.build,einspielen)
    RunScript(script.jorga.build,einspielen,ohne-rueckfrage)
    RunScript(script.jorga.build,sichern)
    RunScript(script.jorga.build,zurueckholen)
    RunScript(script.jorga.build,skin,skin.mimic.lr)

    RunScript(script.jorga.build,geraet-erfassen)
    RunScript(script.jorga.build,geraet-einspielen,<Pfad oder Adresse>)
    RunScript(script.jorga.build,geraet-einspielen,<Adresse>,ohne-rueckfrage)

Die Aktionsnamen bleiben bewusst ohne Umlaute: sie werden auf der Fernbedienung
eingetippt.
"""

import os
import sys

import xbmcaddon
import xbmcgui

sys.path.insert(0, os.path.join(
    xbmcaddon.Addon().getAddonInfo('path'), 'resources', 'lib'))

import einrichtung  # noqa: E402  - erst nach dem Pfad möglich
import geraet       # noqa: E402

MENUE = [
    ('Dieses Gerät als Paket sichern', geraet.erzeuge_auf_wunsch),
    ('Gerät aus Paket einrichten', geraet.spiele_ein),
    ('Was steckt in einem Paket?', geraet.zeige_paket),
    ('—', None),
    ('Mitgelieferte Einrichtung einspielen', einrichtung.spiele_ein),
    ('Was wird dabei eingespielt?', einrichtung.zeige_inhalt),
    ('Nur die Konfiguration sichern', einrichtung.sichere_auf_wunsch),
    ('Sicherung zurückholen', einrichtung.hole_zurueck),
]


def main():
    args = sys.argv[1:]
    if args:
        aktion = args[0]
        ohne_rueckfrage = 'ohne-rueckfrage' in args
        weitere = [a for a in args[1:] if a != 'ohne-rueckfrage']

        if aktion == 'einspielen':
            einrichtung.spiele_ein(nachfragen=not ohne_rueckfrage)
        elif aktion == 'sichern':
            einrichtung.sichere_auf_wunsch()
        elif aktion == 'zurueckholen':
            einrichtung.hole_zurueck()
        elif aktion == 'geraet-erfassen':
            ziel, beschreibung = geraet.erzeuge(weitere[0] if weitere else None)
            einrichtung.melde('Gerät erfasst: %s Add-ons' % len(beschreibung['addons']))
        elif aktion == 'geraet-einspielen':
            geraet.spiele_ein(weitere[0] if weitere else None,
                              nachfragen=not ohne_rueckfrage)
        elif aktion == 'skin':
            kennung = weitere[0] if weitere else 'skin.mimic.lr'
            einrichtung.log('Skinwechsel auf %s: %s' % (
                kennung, 'erreicht' if einrichtung.setze_skin(kennung) else 'nicht erreicht'))
        else:
            einrichtung.log('unbekannte Aktion: %s' % aktion)
        return

    wahl = xbmcgui.Dialog().select(einrichtung.NAME, [e[0] for e in MENUE])
    if wahl >= 0 and MENUE[wahl][1]:
        MENUE[wahl][1]()


if __name__ == '__main__':
    main()

"""Einstiegspunkt des Einrichtungsassistenten.

Liegt in Kodi unter Add-ons > Programm-Add-ons > "Jorga Build".

Der Assistent kann drei Dinge, und das sind verschiedene:

* **Einen Build aus dem Angebot** einspielen (resources/lib/katalog.py). Eine
  JSON-Datei im Netz nennt die verfügbaren Einrichtungen; der Assistent zeigt
  sie als Liste, lädt die gewählte und spielt sie ein. Das ist der Weg für ein
  fremdes Gerät: niemand tippt eine Adresse auf einer Fernbedienung ein.
* **Ein ganzes Gerät übertragen** (resources/lib/geraet.py). Ein bestehendes
  Gerät beschreibt sich selbst in einer Paketdatei, ein anderes baut sich
  danach auf - mit seinen Add-ons, seinem Menü, seinen Einstellungen.
* **Die mitgelieferte Einrichtung** einspielen (resources/lib/einrichtung.py).
  Sie steckt fest in diesem Paket: Skin, Startmenü, Mediatheken, Einstellungen.

Dazu die Pflege (resources/lib/pflege.py): Platz freigeben und frisch anfangen.

Ohne Parameter erscheint das Auswahlmenü. Mit Parameter laufen die Schritte
direkt durch, was das Einrichten mehrerer Geräte erlaubt:

    RunScript(script.jorga.build,angebot)
    RunScript(script.jorga.build,stand)

    RunScript(script.jorga.build,geraet-erfassen)
    RunScript(script.jorga.build,geraet-einspielen,<Pfad oder Adresse>)
    RunScript(script.jorga.build,geraet-einspielen,<Adresse>,ohne-rueckfrage)
    RunScript(script.jorga.build,geraet-einspielen,<Adresse>,frisch)

    RunScript(script.jorga.build,einspielen)
    RunScript(script.jorga.build,einspielen,ohne-rueckfrage)
    RunScript(script.jorga.build,sichern)
    RunScript(script.jorga.build,zurueckholen)
    RunScript(script.jorga.build,skin,skin.mimic.lr)

    RunScript(script.jorga.build,aufraeumen)
    RunScript(script.jorga.build,aufraeumen,ohne-rueckfrage)
    RunScript(script.jorga.build,frisch)

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
import katalog      # noqa: E402
import pflege       # noqa: E402

# Was seltener gebraucht wird, liegt eine Ebene tiefer: ein Menü, das auf einem
# Fernseher nicht mehr auf einen Blick passt, kostet mehr, als es spart.
WEITERES = [
    ('Aufräumen - Platz freigeben', pflege.aufraeumen),
    ('Belegten Platz ansehen', pflege.zeige_platz),
    ('Frisch anfangen - Einrichtung entfernen', pflege.frisch_machen),
    ('—', None),
    ('Sicherung zurückholen', einrichtung.hole_zurueck),
    ('Nur die Konfiguration sichern', einrichtung.sichere_auf_wunsch),
    ('—', None),
    ('Mitgelieferte Einrichtung einspielen', einrichtung.spiele_ein),
    ('Was wird dabei eingespielt?', einrichtung.zeige_inhalt),
    ('—', None),
    ('Eigenen Build-Katalog eintragen', katalog.eigenen_katalog_eintragen),
]


def _zeige(menue, titel=None):
    wahl = xbmcgui.Dialog().select(titel or einrichtung.NAME,
                                   [e[0] for e in menue])
    if wahl >= 0 and menue[wahl][1]:
        menue[wahl][1]()


def weiteres():
    _zeige(WEITERES, 'Pflege und Sicherung')


MENUE = [
    ('Einrichtung aus dem Angebot installieren', katalog.einrichten),
    ('Was steckt in einem Build?', katalog.zeige),
    ('Eingespielter Stand und Aktualisierung', katalog.zeige_stand),
    ('—', None),
    ('Dieses Gerät als Paket sichern', geraet.erzeuge_auf_wunsch),
    ('Gerät aus Paket einrichten (Datei oder Adresse)', geraet.spiele_ein),
    ('Was steckt in einem Paket?', geraet.zeige_paket),
    ('—', None),
    ('Pflege und Sicherung ...', weiteres),
]


def main():
    args = sys.argv[1:]
    if args:
        aktion = args[0]
        ohne_rueckfrage = 'ohne-rueckfrage' in args
        frisch = 'frisch' in args[1:]
        weitere = [a for a in args[1:] if a not in ('ohne-rueckfrage', 'frisch')]

        if aktion == 'einspielen':
            einrichtung.spiele_ein(nachfragen=not ohne_rueckfrage)
        elif aktion == 'sichern':
            einrichtung.sichere_auf_wunsch()
        elif aktion == 'zurueckholen':
            einrichtung.hole_zurueck()
        elif aktion == 'angebot':
            katalog.einrichten()
        elif aktion == 'stand':
            katalog.zeige_stand()
        elif aktion == 'geraet-erfassen':
            ziel, beschreibung = geraet.erzeuge(weitere[0] if weitere else None)
            einrichtung.melde('Gerät erfasst: %s Add-ons' % len(beschreibung['addons']))
        elif aktion == 'geraet-einspielen':
            geraet.spiele_ein(weitere[0] if weitere else None,
                              nachfragen=not ohne_rueckfrage, frisch=frisch)
        elif aktion == 'aufraeumen':
            pflege.aufraeumen(nachfragen=not ohne_rueckfrage)
        elif aktion == 'frisch':
            pflege.frisch_machen(nachfragen=not ohne_rueckfrage)
        elif aktion == 'skin':
            kennung = weitere[0] if weitere else 'skin.mimic.lr'
            einrichtung.log('Skinwechsel auf %s: %s' % (
                kennung, 'erreicht' if einrichtung.setze_skin(kennung) else 'nicht erreicht'))
        else:
            einrichtung.log('unbekannte Aktion: %s' % aktion)
        return

    _zeige(MENUE)


if __name__ == '__main__':
    main()

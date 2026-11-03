"""Erzeugt aus einem gezogenen Kodi-Stand die Vorlage für den Einrichtungsassistenten.

    python vorlage.py <ordner-mit-gezogenem-userdata>

Der Ordner muss enthalten, was `sichere-shield.ps1` von einem Gerät holt:

    guisettings.xml
    addon_data/skin.mimic.lr/settings.xml

Was dabei entsteht, landet unter src/script.jorga.build/resources/build/ und geht
mit dem Add-on an jeden, der es installiert. Deshalb filtert dieses Skript zwei
Klassen von Werten heraus:

**Gerätegebundenes.** Die Bildschirmauflösung und die Audio-Ausgabe hängen an der
Hardware. Eine fremde Auflösung aus einer Vorlage kann auf anderer Hardware ein
schwarzes Bild erzeugen - der Nutzer sieht dann nichts mehr, mit dem er es
zurückstellen könnte.

**Vertrauliches und Diagnose-Reste.** Passwörter, die Geräte-UUID, eingeschaltete
Protokollierung.

Das Startmenü wird nicht übernommen, sondern hier geschrieben: ein weitergegebenes
Menü darf nur auf Add-ons zeigen, die das Paket auch mitbringt.
"""

import json
import pathlib
import shutil
import sys
import xml.etree.ElementTree as ET

WURZEL = pathlib.Path(__file__).parent
ZIEL = WURZEL / "src" / "script.jorga.build" / "resources" / "build"

# Gehört in keine weitergegebene Vorlage, je mit Begründung
TABU = {
    "services.deviceuuid": "je Gerät eigen, Kodi erzeugt sie selbst",
    "services.webserverpassword": "Passwort",
    "services.webserverusername": "Zugangsname",
    "services.airplaypassword": "Passwort",
    "network.httpproxypassword": "Passwort",
    "network.httpproxyusername": "Zugangsname",
    "audiooutput.passthroughdevice": "hängt an der Audio-Hardware",
    "audiooutput.audiodevice": "hängt an der Audio-Hardware",
    "videoscreen.resolution": "hängt am Bildschirm, falscher Wert = schwarzes Bild",
    "videoscreen.whitelist": "hängt am Bildschirm, falscher Wert = schwarzes Bild",
    "videoscreen.monitor": "hängt am Bildschirm",
    "debug.showloginfo": "Diagnose-Rest",
    "debug.extralogging": "Diagnose-Rest",
    "lookandfeel.skin": "setzt der Assistent gezielt zuletzt",
    "general.addonupdates": "eine Vorlage darf Add-on-Updates nie abschalten",
    "general.addonnotifications": "siehe general.addonupdates",
    "system.playlistspath": "verweist auf das Profil des Ursprungsgeräts",
    "subtitles.movie": "verweist auf ein Add-on, das die Vorlage nicht mitbringt",
    "subtitles.tv": "verweist auf ein Add-on, das die Vorlage nicht mitbringt",
}
TABU_PRAEFIX = ("gamesachievements.", "services.esa", "services.zeroconf", "pvrmanager.", "epg.")

# Skin-Schalter, die nur zur Fehlersuche an waren
SKIN_TABU = {"skin.toggledebug"}

MENUE = [
    # (Beschriftung, Untertitel, Symbol im Skin, Aktion)
    ("Mediatheken", "Alle Sender auf einen Blick", "video.png",
     'ActivateWindow(Videos,"plugin://plugin.video.mediatheken/",return)'),
    ("ARD", "ARD Mediathek", "tv.png",
     'ActivateWindow(Videos,"plugin://plugin.video.ardmediathek_de/",return)'),
    ("ZDF", "ZDF Mediathek", "tv.png",
     'ActivateWindow(Videos,"plugin://plugin.video.zdf_de_lite/",return)'),
    ("SRF", "SRF Play", "tv.png",
     'ActivateWindow(Videos,"plugin://plugin.video.srfplaytv/",return)'),
    ("ARTE", "ARTE", "tv.png",
     'ActivateWindow(Videos,"plugin://plugin.video.arteplussept/",return)'),
    ("3sat", "3sat Mediathek", "tv.png",
     'ActivateWindow(Videos,"plugin://plugin.video.3satmediathek/",return)'),
    ("YouTube", "YouTube", "video.png",
     'ActivateWindow(Videos,"plugin://plugin.video.youtube/",return)'),
    ("Suche", "Alles durchsuchen", "search.png",
     'RunScript(script.globalsearch)'),
]
# Kodis eigene Menüpunkte: defaultID sorgt dafür, dass der Skin sie als solche erkennt
MENUE_STANDARD = [
    ("Favoriten", "favorites", "favourite.png", "ActivateWindow(favourites)"),
    ("Addons", "add-ons", "addon.png", "ActivateWindow(10040)"),
    ("Einstellungen", "settings", None, "ActivateWindow(Settings)"),
]

FAVORITEN = [
    ("ARD - Sendung verpasst", "plugin://plugin.video.ardmediathek_de/"),
    ("ZDF Mediathek", "plugin://plugin.video.zdf_de_lite/"),
    ("SRF Play", "plugin://plugin.video.srfplaytv/"),
    ("ARTE", "plugin://plugin.video.arteplussept/"),
    ("3sat", "plugin://plugin.video.3satmediathek/"),
]


def einstellungen(quelle: pathlib.Path) -> dict:
    """Liest guisettings.xml und gibt die weitergebbaren Abweichungen zurück."""
    wurzel = ET.parse(quelle).getroot()
    werte, standard, raus = {}, 0, []
    for s in wurzel.iter("setting"):
        kennung = s.get("id")
        if not kennung:
            continue
        if s.get("default") == "true":        # Kodi markiert Unveränderte selbst
            standard += 1
            continue
        if kennung in TABU:
            raus.append((kennung, TABU[kennung]))
            continue
        if kennung.startswith(TABU_PRAEFIX):
            raus.append((kennung, "gerätenahe Gruppe"))
            continue
        if len(s) > 0:                        # Listen kann JSON-RPC nicht setzen
            raus.append((kennung, "verschachtelt"))
            continue
        werte[kennung] = s.text or ""
    print(f"  guisettings: {len(werte)} übernommen, {standard} auf Standard, {len(raus)} gefiltert")
    for kennung, grund in sorted(raus):
        print(f"    - {kennung:<40} {grund}")
    return werte


def skin_einstellungen(quelle: pathlib.Path, ziel: pathlib.Path):
    """Übernimmt die Skin-Einstellungen ohne die Diagnose-Schalter."""
    baum = ET.parse(quelle)
    wurzel = baum.getroot()
    entfernt = [s for s in list(wurzel) if s.get("id") in SKIN_TABU]
    for s in entfernt:
        wurzel.remove(s)
    ziel.parent.mkdir(parents=True, exist_ok=True)
    baum.write(ziel, encoding="utf-8", xml_declaration=True)
    print(f"  skin.mimic.lr: {len(list(wurzel))} Schalter, {len(entfernt)} gefiltert")


def startmenue(ziel: pathlib.Path):
    """Schreibt das Startmenü - nur Einträge, die das Paket auch bedienen kann."""
    zeilen = ["<?xml version='1.0' encoding='utf-8'?>", "<shortcuts>"]
    for label, label2, symbol, aktion in MENUE:
        zeilen += [
            "\t<shortcut>",
            "\t\t<defaultID />",
            f"\t\t<label>{label}</label>",
            f"\t\t<label2>{label2}</label2>",
            "\t\t<icon>DefaultShortcut.png</icon>",
            f"\t\t<thumb>special://skin/extras/icons/{symbol}</thumb>",
            f"\t\t<action>{aktion.replace('&', '&amp;').replace('<', '&lt;')}</action>",
            "\t</shortcut>",
        ]
    for label, kennung, symbol, aktion in MENUE_STANDARD:
        thumb = f"special://skin/extras/icons/{symbol}" if symbol else "DefaultIconSettings.png"
        zeilen += [
            "\t<shortcut>",
            f"\t\t<defaultID>{kennung}</defaultID>",
            f"\t\t<label>{label}</label>",
            "\t\t<label2>Common menu item</label2>",
            "\t\t<icon>DefaultShortcut.png</icon>",
            f"\t\t<thumb>{thumb}</thumb>",
            f"\t\t<action>{aktion}</action>",
            "\t</shortcut>",
        ]
    zeilen += [
        "\t<shortcut>",
        "\t\t<defaultID />",
        "\t\t<label>Beenden</label>",
        "\t\t<label2>Kodi beenden</label2>",
        "\t\t<icon>DefaultShortcut.png</icon>",
        "\t\t<thumb>special://skin/extras/icons/power.png</thumb>",
        "\t\t<action>Quit</action>",
        "\t</shortcut>",
        "</shortcuts>",
    ]
    ziel.parent.mkdir(parents=True, exist_ok=True)
    ziel.write_text("\n".join(zeilen) + "\n", encoding="utf-8")
    print(f"  Startmenü: {len(MENUE) + len(MENUE_STANDARD) + 1} Einträge")


def favoriten(ziel: pathlib.Path):
    zeilen = ["<favourites>"]
    for name, pfad in FAVORITEN:
        zeilen.append(
            f'    <favourite name="{name}">ActivateWindow(Videos,&quot;{pfad}&quot;,return)</favourite>')
    zeilen.append("</favourites>")
    ziel.write_text("\n".join(zeilen) + "\n", encoding="utf-8")
    print(f"  Favoriten: {len(FAVORITEN)} Einträge")


def quellen(ziel: pathlib.Path):
    """Nur allgemein sinnvolle Quellen - keine aus dem Ursprungsgerät."""
    ziel.write_text("""<sources>
    <programs>
        <default pathversion="1"></default>
    </programs>
    <video>
        <default pathversion="1"></default>
    </video>
    <music>
        <default pathversion="1"></default>
    </music>
    <pictures>
        <default pathversion="1"></default>
    </pictures>
    <files>
        <default pathversion="1"></default>
        <source>
            <name>Home</name>
            <path pathversion="1">special://home</path>
            <allowsharing>true</allowsharing>
        </source>
    </files>
    <games>
        <default pathversion="1"></default>
    </games>
</sources>
""", encoding="utf-8")
    print("  Quellen: 1 Eintrag (special://home)")


def erweiterte_einstellungen(ziel: pathlib.Path):
    """Cache-Werte, die auf Geräten mit knappem Arbeitsspeicher nicht umkippen."""
    ziel.write_text("""<advancedsettings>
  <!-- Kodi reserviert bis zum Dreifachen von memorysize. Der Standard von 20 MB
       ist für Streams zu knapp, der früher verbreitete Rat von 292 MB sprengt
       Geräte wie die Shield (dort nur rund 1 GB frei): 3 x 292 MB = 876 MB führen
       zum Absturz. 100 MB bedeuten höchstens 300 MB und laufen stabil. -->
  <cache>
    <memorysize>104857600</memorysize>
    <buffermode>1</buffermode>
    <readfactor>4.0</readfactor>
  </cache>
  <epg>
    <!-- Die Meldung beim EPG-Aufbau verdeckt sonst bei jedem Start das Menü -->
    <displayupdatepopup>false</displayupdatepopup>
  </epg>
</advancedsettings>
""", encoding="utf-8")
    print("  advancedsettings: Cache 100 MB")


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    quelle = pathlib.Path(sys.argv[1])
    gui = quelle / "guisettings.xml"
    skin = quelle / "addon_data" / "skin.mimic.lr" / "settings.xml"
    for p in (gui, skin):
        if not p.is_file():
            raise SystemExit(f"fehlt: {p}")

    if ZIEL.exists():
        shutil.rmtree(ZIEL)
    ud = ZIEL / "userdata"
    ud.mkdir(parents=True)

    print(f"Vorlage aus {quelle}:")
    werte = einstellungen(gui)
    (ZIEL / "einstellungen.json").write_text(
        json.dumps(werte, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")

    skin_einstellungen(skin, ud / "addon_data" / "skin.mimic.lr" / "settings.xml")
    startmenue(ud / "addon_data" / "script.skinshortcuts" / "mainmenu.DATA.xml")
    favoriten(ud / "favourites.xml")
    quellen(ud / "sources.xml")
    erweiterte_einstellungen(ud / "advancedsettings.xml")

    dateien = sorted(p for p in ZIEL.rglob("*") if p.is_file())
    gesamt = sum(p.stat().st_size for p in dateien)
    print(f"\n{len(dateien)} Dateien, {gesamt / 1024:.1f} KB unter {ZIEL}")
    for p in dateien:
        print(f"  {p.relative_to(ZIEL).as_posix():<52} {p.stat().st_size / 1024:>7.1f} KB")


if __name__ == "__main__":
    main()

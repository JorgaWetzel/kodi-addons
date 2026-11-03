# -*- coding: utf-8 -*-
"""Sammelmenü der fünf öffentlich-rechtlichen Mediatheken.

Das Add-on bringt keine eigenen Inhalte mit. Sein Zweck ist, die fünf Mediatheken
über die Abhängigkeiten in addon.xml in einem Schritt zu installieren und sie danach
unter einem Menüpunkt zusammenzufassen, statt sie einzeln im Add-on-Browser zu suchen.

Ein Eintrag wird nur angezeigt, wenn das zugehörige Add-on wirklich vorhanden und
aktiviert ist - sonst landet man auf einem Menüpunkt, der ins Leere führt.
"""

import sys

import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmcvfs

HANDLE = int(sys.argv[1])

# Anzeigename, Add-on-ID, Einstiegspfad
MEDIATHEKEN = [
    ("ARD Mediathek", "plugin.video.ardmediathek_de", "plugin://plugin.video.ardmediathek_de/"),
    ("ZDF Mediathek", "plugin.video.zdf_de_lite", "plugin://plugin.video.zdf_de_lite/"),
    ("SRF Play", "plugin.video.srfplaytv", "plugin://plugin.video.srfplaytv/"),
    ("ARTE", "plugin.video.arteplussept", "plugin://plugin.video.arteplussept/"),
    ("3sat Mediathek", "plugin.video.3satmediathek", "plugin://plugin.video.3satmediathek/"),
]


def ist_verfuegbar(addon_id):
    try:
        xbmcaddon.Addon(addon_id)
        return True
    except Exception:
        # Kodi wirft, wenn das Add-on fehlt oder deaktiviert ist
        return False


def symbol(addon_id):
    for pfad in (
        f"special://home/addons/{addon_id}/icon.png",
        f"special://home/addons/{addon_id}/resources/icon.png",
    ):
        if xbmcvfs.exists(pfad):
            return pfad
    return "DefaultAddonVideo.png"


def zeige_menue():
    vorhanden = 0
    for name, addon_id, pfad in MEDIATHEKEN:
        if not ist_verfuegbar(addon_id):
            continue
        vorhanden += 1
        eintrag = xbmcgui.ListItem(label=name)
        eintrag.setArt({"icon": symbol(addon_id), "thumb": symbol(addon_id)})
        eintrag.setInfo("video", {"title": name, "plot": f"Inhalte von {name}"})
        xbmcplugin.addDirectoryItem(HANDLE, pfad, eintrag, isFolder=True)

    if vorhanden == 0:
        xbmcgui.Dialog().notification(
            "Mediatheken DACH",
            "Keine Mediathek installiert oder alle deaktiviert",
            xbmcgui.NOTIFICATION_WARNING,
            6000,
        )

    xbmcplugin.setContent(HANDLE, "videos")
    xbmcplugin.endOfDirectory(HANDLE)


if __name__ == "__main__":
    zeige_menue()

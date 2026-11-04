"""Aufräumen und frisch anfangen - die beiden Pflegeschritte eines Assistenten.

**Aufräumen** gibt Platz frei, ohne die Einrichtung anzutasten. Auf einem
Android-Fernsehgerät ist das kein Luxus: Kodi legt jedes heruntergeladene
Add-on-ZIP dauerhaft ab, und der Bildspeicher für Cover wächst unbegrenzt.

**Frisch anfangen** setzt die Einrichtung auf den Stand nach der Installation
zurück, damit ein Build auf einem sauberen Gerät landet statt über einem
fremden.

Zwei Dinge dabei sind nicht offensichtlich und begründen den Aufbau:

* **Eine gelöschte guisettings.xml kommt zurück.** Kodi hält die Einstellungen
  im Speicher und schreibt sie beim Beenden vollständig neu. Zurückgesetzt wird
  deshalb über JSON-RPC (`Settings.ResetSettingValue`), Wert für Wert.
* **Die Add-ons bleiben stehen.** Den laufenden Skin oder ein geladenes
  Python-Modul im Betrieb zu löschen, bringt Kodi zum Absturz. Gebraucht wird
  es auch nicht: die Einrichtung überschreibt, was die Oberfläche bestimmt -
  Menü, Skin, Einstellungen. Ein übriggebliebenes Add-on taucht nur noch unter
  "Add-ons" auf und stört nichts.
"""

import os
import shutil

import xbmc
import xbmcgui
import xbmcvfs

import einrichtung
import paket

from einrichtung import NAME, PROFIL, SICHERUNGEN, log, rpc


# Was beim Aufräumen weggeräumt wird, und was es ist.
AUFRAEUMEN = [
    ('addons/packages', 'special://home/addons/packages',
     'Heruntergeladene Add-on-Pakete - Kodi behält jedes ZIP, braucht es aber '
     'nach der Installation nicht mehr.'),
    ('temp', 'special://temp',
     'Zwischendateien von Add-ons und Abspielvorgängen.'),
]

# Der Bildspeicher. Eigener Schritt, weil Kodi danach neu starten muss: Ordner
# und Datenbank gehören zusammen, und die Datenbank hat Kodi im Betrieb offen.
BILDSPEICHER = ['special://profile/Thumbnails',
                'special://profile/Database/Textures13.db']

# Dateien, die beim Frischanfang verschwinden. guisettings.xml steht bewusst
# nicht dabei - siehe Modulkopf.
FRISCH_DATEIEN = ['favourites.xml', 'sources.xml', 'RssFeeds.xml',
                  'mediasources.xml', 'passwords.xml']
FRISCH_ORDNER = ['addon_data', 'playlists', 'keymaps', 'library']

# Diese Add-on-Daten bleiben beim Frischanfang: der Assistent selbst (sonst
# verliert er die Adresse des eigenen Katalogs) und seine Sicherungen.
FRISCH_BEHALTEN = {'script.jorga.build'}


def _groesse(pfad):
    """Belegte Bytes unter einem Pfad, rekursiv. 0, wenn es nichts gibt."""
    if os.path.isfile(pfad):
        return os.path.getsize(pfad)
    summe = 0
    for wurzel, _, namen in os.walk(pfad):
        for n in namen:
            try:
                summe += os.path.getsize(os.path.join(wurzel, n))
            except OSError:
                pass
    return summe


def _lies_mb(bytes_):
    return '%.1f MB' % (bytes_ / (1024.0 * 1024.0))


def _leere(pfad, nur_inhalt=True):
    """Löscht einen Pfad. Gibt die freigegebenen Bytes zurück.

    Mit nur_inhalt bleibt der Ordner selbst stehen: Kodi erwartet manche
    Ordner (addons/packages, temp) und legt sie nicht immer neu an.
    """
    echt = xbmcvfs.translatePath(pfad)
    frei = _groesse(echt)
    try:
        if os.path.isfile(echt):
            os.remove(echt)
        elif os.path.isdir(echt):
            if nur_inhalt:
                for name in os.listdir(echt):
                    ziel = os.path.join(echt, name)
                    if os.path.isdir(ziel):
                        shutil.rmtree(ziel, ignore_errors=True)
                    else:
                        try:
                            os.remove(ziel)
                        except OSError as problem:
                            log('%s nicht löschbar: %s' % (ziel, problem),
                                xbmc.LOGWARNING)
            else:
                shutil.rmtree(echt, ignore_errors=True)
        else:
            return 0
    except OSError as problem:
        log('%s nicht löschbar: %s' % (echt, problem), xbmc.LOGWARNING)
        return 0
    return frei


# ------------------------------------------------------------------ Aufräumen

def aufraeumen(nachfragen=True):
    """Gibt Platz frei, ohne die Einrichtung anzutasten."""
    posten = [(name, pfad, _groesse(xbmcvfs.translatePath(pfad)), beschreibung)
              for name, pfad, beschreibung in AUFRAEUMEN]
    bilder = sum(_groesse(xbmcvfs.translatePath(p)) for p in BILDSPEICHER)
    gesamt = sum(p[2] for p in posten)

    if nachfragen:
        zeilen = ['%s  %s' % (_lies_mb(g), name) for name, _, g, _ in posten]
        zeilen += ['', 'Der Bildspeicher (Cover und Vorschaubilder) belegt '
                       '%s. Er wird einzeln abgefragt, weil Kodi danach neu '
                       'starten muss.' % _lies_mb(bilder)]
        if not xbmcgui.Dialog().yesno(
                NAME, 'Freigeben:[CR][CR]%s[CR][CR]Zusammen %s. Die Einrichtung '
                      'bleibt unberührt.[CR][CR]Jetzt aufräumen?'
                      % ('[CR]'.join(zeilen), _lies_mb(gesamt)),
                nolabel='Abbrechen', yeslabel='Aufräumen'):
            return None

    frei = 0
    for name, pfad, _, _ in posten:
        frei += _leere(pfad)
        log('aufgeräumt: %s' % name)

    bilder_frei = 0
    if nachfragen and bilder > 1024 * 1024 and xbmcgui.Dialog().yesno(
            NAME, 'Auch den Bildspeicher leeren (%s)?[CR][CR]Cover und '
                  'Vorschaubilder werden danach neu geladen, und Kodi muss '
                  'dafür neu starten.' % _lies_mb(bilder),
            nolabel='Behalten', yeslabel='Leeren'):
        for pfad in BILDSPEICHER:
            bilder_frei += _leere(pfad, nur_inhalt=not pfad.endswith('.db'))
        frei += bilder_frei

    if nachfragen:
        text = '%s freigegeben.' % _lies_mb(frei)
        if bilder_frei:
            xbmcgui.Dialog().ok(NAME, text + '[CR][CR]Der Bildspeicher wurde '
                                             'geleert - Kodi jetzt neu starten.')
            _neustart_anbieten()
        else:
            einrichtung.melde(text)
    log('Aufräumen: %s freigegeben' % _lies_mb(frei))
    return frei


# ------------------------------------------------------------- Frisch anfangen

def _setze_einstellungen_zurueck():
    """Setzt alle abweichenden Kodi-Einstellungen auf den Standard zurück.

    Ausgenommen bleibt, was am Gerät hängt: Auflösung, Bildmodus und
    Audiogerät. Dieselbe Liste, die auch beim Erfassen nicht mitwandert -
    ein zurückgesetzter Bildmodus kann ein schwarzes Bild bedeuten, und wer
    das auf einem Fernseher auslöst, kommt ohne fremde Hilfe nicht zurück.
    """
    werte = paket.abweichende_einstellungen(PROFIL)
    zurueck, offen = 0, []
    for kennung in sorted(werte):
        if kennung in paket.NICHT_UEBERNEHMEN:
            continue
        if rpc('Settings.ResetSettingValue', setting=kennung) is None:
            offen.append(kennung)
        else:
            zurueck += 1
    if offen:
        log('nicht zurücksetzbar: %s' % ', '.join(offen), xbmc.LOGWARNING)
    return zurueck, offen


def frisch_machen(nachfragen=True, sichern=True):
    """Setzt die Einrichtung auf den Stand nach der Kodi-Installation zurück.

    Mit sichern=False entfällt die Sicherung, weil der Aufrufer schon eine
    angelegt hat - so entsteht beim "frisch einrichten" nicht zweimal
    dasselbe ZIP.
    """
    if nachfragen and not xbmcgui.Dialog().yesno(
            NAME, 'Frisch anfangen entfernt:[CR][CR]'
                  'Startmenü, Favoriten, Quellen und Tastenbelegung[CR]'
                  'alle Add-on-Einstellungen[CR]'
                  'die geänderten Kodi-Einstellungen[CR][CR]'
                  'Die Add-ons selbst bleiben installiert, und alles wird '
                  'vorher gesichert.[CR][CR]Fortfahren?',
            nolabel='Abbrechen', yeslabel='Frisch anfangen'):
        return None

    bericht = {'sicherung': einrichtung.sichere() if sichern else None}
    fortschritt = xbmcgui.DialogProgress() if nachfragen else None
    if fortschritt:
        fortschritt.create(NAME, 'Einstellungen zurücksetzen ...')
    try:
        bericht['zurueckgesetzt'], bericht['offen'] = _setze_einstellungen_zurueck()

        if fortschritt:
            fortschritt.update(50, 'Konfiguration entfernen ...')
        geloescht = 0
        for name in FRISCH_DATEIEN:
            pfad = os.path.join(PROFIL, name)
            if os.path.isfile(pfad):
                os.remove(pfad)
                geloescht += 1
        for ordner in FRISCH_ORDNER:
            basis = os.path.join(PROFIL, ordner)
            if not os.path.isdir(basis):
                continue
            for name in os.listdir(basis):
                if ordner == 'addon_data' and name in FRISCH_BEHALTEN:
                    continue
                ziel = os.path.join(basis, name)
                if os.path.isdir(ziel):
                    shutil.rmtree(ziel, ignore_errors=True)
                else:
                    os.remove(ziel)
                geloescht += 1
        bericht['geloescht'] = geloescht

        # Die erzeugte Menüdatei des aktiven Skins mit entfernen, sonst zeigt
        # das Gerät weiter das alte Startmenü (an drei Stellen, siehe
        # paket.menue_neu_bauen_lassen).
        if fortschritt:
            fortschritt.update(80, 'Startmenü zurücksetzen ...')
        haut = rpc('Settings.GetSettingValue', setting='lookandfeel.skin')
        if haut:
            paket.menue_neu_bauen_lassen(haut.get('value', ''))
    except Exception as problem:
        log('Frischanfang abgebrochen: %s' % problem, xbmc.LOGERROR)
        bericht['abbruch'] = str(problem)
    finally:
        if fortschritt:
            fortschritt.close()

    log('Frischanfang: %s Einstellungen zurück, %s Dateien entfernt, '
        'Sicherung %s' % (bericht.get('zurueckgesetzt', 0),
                          bericht.get('geloescht', 0), bericht.get('sicherung')))
    if nachfragen:
        if 'abbruch' in bericht:
            xbmcgui.Dialog().ok(NAME, 'Abgebrochen:[CR][CR]%s' % bericht['abbruch'])
            return bericht
        xbmcgui.Dialog().ok(
            NAME, 'Frisch.[CR][CR]%s Einstellungen auf Standard, %s '
                  'Konfigurationsposten entfernt.[CR][CR]Sicherung:[CR]%s'
                  % (bericht.get('zurueckgesetzt', 0), bericht.get('geloescht', 0),
                     os.path.basename(bericht.get('sicherung', '-'))))
        _neustart_anbieten()
    return bericht


def _neustart_anbieten():
    if xbmcgui.Dialog().yesno(NAME, 'Kodi jetzt beenden? Beim nächsten Start '
                                    'greift alles.',
                              nolabel='Später', yeslabel='Beenden'):
        xbmc.executebuiltin('Quit')


def zeige_platz():
    """Was belegt wie viel - ohne etwas zu verändern."""
    zeilen = []
    for name, pfad, beschreibung in AUFRAEUMEN:
        zeilen += ['%-24s %10s' % (name, _lies_mb(_groesse(xbmcvfs.translatePath(pfad)))),
                   '   %s' % beschreibung, '']
    bilder = sum(_groesse(xbmcvfs.translatePath(p)) for p in BILDSPEICHER)
    zeilen += ['%-24s %10s' % ('Bildspeicher', _lies_mb(bilder)),
               '   Cover und Vorschaubilder. Kodi lädt sie nach dem Leeren neu.',
               '']
    sicherungen = _groesse(SICHERUNGEN)
    zeilen += ['%-24s %10s' % ('eigene Sicherungen', _lies_mb(sicherungen)),
               '   %s' % SICHERUNGEN,
               '   Wird beim Aufräumen nicht angetastet - hier liegt der Weg '
               'zurück.']
    xbmcgui.Dialog().textviewer('Belegter Platz', '\n'.join(zeilen))

# Kodi Add-ons

Privates Arbeitsrepository für unsere überarbeiteten Kodi-Add-ons.
Erster Prüfgegenstand: `plugin.video.vavooto` und dessen Streaming-Störung.

## Ablauf

1. Kodi-Installation, Version, Plattform und Add-on-Bestand erfassen.
2. Einstellungen und Add-ons sichern; Fehlerprotokoll auswerten.
3. Updatequellen und Abhängigkeiten prüfen; Updates und Reparaturen einspielen.
4. Wiedergabe, Navigation, Favoriten und Verhalten bei Netzfehlern testen.
5. Geprüfte eigene Version veröffentlichen.
6. **Erst nach vollständiger Überarbeitung und Prüfung:** einen schön gestalteten Installer erstellen. Michaz dient als gestalterische Referenz.

## Stand

Noch kein repariertes Add-on oder installierbares Release. Das betroffene Gerät und die Kodi-Version sind noch zuzuordnen.

Öffentliche Vergleichsquelle: [eyMarv/plugin.video.vavooto](https://github.com/eyMarv/plugin.video.vavooto), Version 6.5.1, Autorenangabe kasi/michaz. Noch nicht als installierter oder aktueller Stand bestätigt.

Erste statische Prüfpunkte: ungeschützte JSON-/Cache-Auswertung, Netzwerkaufrufe ohne explizite Zeitgrenze, automatische Abhängigkeitsinstallation beim Start und deaktivierte Zertifikatsprüfung an einzelnen API-Aufrufen. Die konkrete Ursache der Streaming-Störung ist damit noch nicht nachgewiesen.

Private Releases benötigen GitHub-Anmeldung. Eine direkt von Kodi erreichbare Updatequelle wird beim Release festgelegt.

Keine Zugangsdaten, persönlichen Kodi-Profile oder unbereinigten Protokolle ins Repository übernehmen.

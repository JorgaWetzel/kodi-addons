# Jorga Repository — reparierte Mediathek-Add-ons für Kodi

Ein Kodi-Repository mit Fassungen der Mediathek-Add-ons von
[sarbes](https://github.com/sarbes), die gegen den aktuellen Stand der Sender-APIs
repariert wurden. Die Versionsnummern liegen über denen des offiziellen
Kodi-Repositoriums, damit die Reparaturen beim nächsten Update nicht wieder
überschrieben werden.

Geprüft auf Kodi 21.2 (Omega), NVIDIA Shield, Android 11 — am 03.11.2026 jede Quelle
bis zur laufenden Wiedergabe.

## Installieren

1. [`repository.jorga-1.0.0.zip`](repo/repository.jorga/repository.jorga-1.0.0.zip)
   herunterladen.
2. In Kodi: **Einstellungen → Add-ons → Aus ZIP-Datei installieren** → die Datei wählen.
   Ist der Punkt gesperrt, vorher unter **Einstellungen → System → Add-ons**
   *Unbekannte Quellen* einschalten.
3. **Aus Repository installieren → Jorga Repository → Video-Add-ons →
   Mediatheken DACH**.

Das Paket *Mediatheken DACH* zieht ARD, ZDF, SRF Play, ARTE und 3sat als
Abhängigkeiten mit — ein Schritt statt fünf — und fasst sie in einem Menü zusammen.
ARD, SRF und ARTE kommen dabei unverändert aus dem offiziellen Kodi-Repository.

## Was repariert wurde

### ZDF — funktionierte überhaupt nicht mehr

`plugin.video.zdf_de_lite` 5.0.2 holte sein API-Token von
`zdf-cdn.live.cellular.de`. Dieser Hostname **löst nicht mehr auf**, ohne Token
scheiterte jede einzelne Abfrage. Das Token steht jetzt dort, wo es auch der
ZDF-Web-Client liest: in der Konfiguration der Senderwebseite. Es ist im
RSC-Payload als JavaScript-String eingebettet, die Anführungszeichen sind escaped —
ein Suchausdruck für reines JSON findet dort nichts.

Dazu: Ein abgelaufenes Token wurde vorher nur scheinbar erneuert — der Code las
dieselbe Datei erneut und wiederholte den Aufruf mit demselben ungültigen Token.
Und der Menüpunkt "Meistgesehen" zeigte auf ein Dokument, das das ZDF abgeschaltet
hat (`profile: http://zdf.de/rels/gone`); dafür jetzt "Sendung verpasst".

### 3sat — Sendungsliste blieb leer

Ein einzelner Eintrag, dem ein früher geliefertes Feld fehlte, brach die Liste mit
`KeyError: 'self'` ab — und riss damit **alle** 324 Sendungen mit. Solche Einträge
werden jetzt übersprungen und protokolliert. Der Fix sitzt am gemeinsamen Eingang
und deckt A-Z, Suche, Rubriken und EPG gleichzeitig ab.

### ARD — Absturz statt Meldung

Zwei Fälle endeten mit einem nackten Skriptfehler auf dem Bildschirm:

- Bei Altersfreigabe liefert die API Metadaten ohne `mediaCollection`
  (`blockedByFsk`) → `TypeError: 'NoneType' object is not subscriptable`. Betrifft
  jeden Film mit Altersfreigabe ausserhalb der Sendezeit.
- Die A-Z-Liste gibt bei manchen Sendungen eine Sendungs- statt einer Videokennung
  als Wiedergabelink aus; die API antwortet mit 404/400.

Beide melden jetzt den Grund und lassen die Liste bedienbar.

## Inhalt

| Add-on | Version | Herkunft |
|---|---|---|
| `repository.jorga` | 1.0.0 | dieses Repository |
| `plugin.video.mediatheken` | 1.0.0 | dieses Repository — Sammelpaket und Menü |
| `plugin.video.zdf_de_lite` | 5.0.3 | sarbes 5.0.2, repariert |
| `script.module.libzdf` | 5.0.3 | sarbes 5.0.2, repariert (ZDF **und** 3sat) |
| `script.module.libard` | 6.0.4 | sarbes 6.0.3, repariert |

Die Änderungen stehen je Add-on im `<news>`-Abschnitt der `addon.xml` und sind damit
in Kodi unter *Add-on-Informationen → Änderungsprotokoll* lesbar.

## Was dieses Repository nicht leistet

- **Geosperren bleiben Geosperren.** Streams mit `/dach/` im CDN-Pfad antworten
  ausserhalb von Deutschland, Österreich und der Schweiz mit HTTP 403. Betroffen ist
  Lizenzware; Eigenproduktionen der Sender laufen, und das ist der grösste Teil des
  Katalogs. Kein Add-on-Fehler und mit einem Add-on auch nicht zu beheben.
- **Jugendschutzsperren bleiben.** Filme mit Altersfreigabe sind erst zur Sendezeit
  abrufbar. Repariert ist nur, dass das eine verständliche Meldung gibt.

## Selbst bauen

```
python build.py
```

liest `src/`, legt je Add-on ein ZIP unter `repo/<id>/` ab und erzeugt `addons.xml`
samt `addons.xml.md5`. Stimmt die MD5-Summe nicht zur `addons.xml`, ignoriert Kodi
das Repository stillschweigend — deshalb immer über das Skript bauen, nie die Dateien
von Hand ändern.

Nach dem Bauen `repo/` committen und pushen; die URLs in
`src/repository.jorga/addon.xml` zeigen auf `raw.githubusercontent.com`, das
Repository muss dafür öffentlich sein.

## Lizenz und Urheberschaft

Die drei reparierten Add-ons stammen von **sarbes** und stehen unter **GPL-2.0-only**;
sie behalten Lizenz, Urheberangabe und Quellenverweis. Die Änderungen sind in der
jeweiligen `addon.xml` als solche gekennzeichnet. `repository.jorga` und
`plugin.video.mediatheken` stehen ebenfalls unter GPL-2.0-only.

Keines dieser Add-ons wird von einer Sendeanstalt unterstützt. Sie greifen auf die
frei zugänglichen Mediatheken der öffentlich-rechtlichen Sender zu.

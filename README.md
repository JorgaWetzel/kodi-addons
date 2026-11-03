# Jorga Repository — fertige Kodi-Einrichtung für die Mediatheken im DACH-Raum

Ein Kodi-Repository mit zwei Teilen:

- **Ein Einrichtungsassistent**, der ein frisches Kodi in einem Zug einsatzfertig
  macht: Skin mit fertigem Startmenü, die Mediatheken von ARD, ZDF, SRF, ARTE und
  3sat, die passenden Kodi-Einstellungen. Die bestehende Einrichtung wird vorher
  gesichert und lässt sich jederzeit zurückholen.
- **Reparierte Mediathek-Add-ons** von [sarbes](https://github.com/sarbes), gegen
  den aktuellen Stand der Sender-APIs instandgesetzt. Die Versionsnummern liegen
  über denen des offiziellen Kodi-Repositoriums, damit die Reparaturen beim
  nächsten Update nicht wieder überschrieben werden.

Geprüft auf Kodi 21.2 (Omega), NVIDIA Shield, Android 11 — am 03.11.2026 jede
Quelle bis zur laufenden Wiedergabe.

## Installieren

1. [`repository.jorga-2.0.0.zip`](repo/repository.jorga/repository.jorga-2.0.0.zip)
   herunterladen.
2. In Kodi: **Einstellungen → Add-ons → Aus ZIP-Datei installieren** → die Datei
   wählen. Ist der Punkt gesperrt, vorher unter **Einstellungen → System →
   Add-ons** *Unbekannte Quellen* einschalten.
3. **Aus Repository installieren → Jorga Repository → Programm-Add-ons →
   Jorga Build**.

Kodi zieht dabei alles mit, was die Einrichtung braucht — Skin, Mediatheken,
YouTube, TMDb-Helper, globale Suche — und fragt beim Skin, ob es gleich auf
*Mimic-LR* umschalten soll. Dann **Add-ons → Programm-Add-ons → Jorga Build →
Einrichtung einspielen**.

Wer nur die reparierten Mediatheken will, nimmt statt *Jorga Build* das Paket
**Video-Add-ons → Mediatheken DACH**: es zieht die fünf Sender als Abhängigkeiten
mit und fasst sie in einem Menü zusammen, ohne Einstellungen anzutasten.

## Der Einrichtungsassistent

Vier Punkte unter **Add-ons → Programm-Add-ons → Jorga Build**:

| Punkt | Was er tut |
|---|---|
| Einrichtung einspielen | Sichert die bestehende Einrichtung, spielt dann Startmenü, Favoriten, Skin-Einstellungen und 44 Kodi-Einstellungen ein |
| Was wird eingespielt? | Zeigt vorher jede Datei und jede Einstellung an |
| Eigene Einrichtung sichern | Legt eine Sicherung an, ohne etwas zu ändern |
| Sicherung zurückholen | Spielt eine frühere Sicherung wieder ein |

Für das Einrichten mehrerer Geräte geht es auch ohne Menü:

```
RunScript(script.jorga.build,einspielen,ohne-rueckfrage)
RunScript(script.jorga.build,sichern)
RunScript(script.jorga.build,zurueckholen)
```

Sicherungen landen unter `userdata/jorga-sicherungen/` und umfassen Einstellungen,
Startmenü, Favoriten, Quellen, Tastenbelegungen und Skin-Einstellungen. Nicht
dabei sind `Database/` und `Thumbnails/` — die baut Kodi selbst neu auf und sie
machen den Löwenanteil der Datenmenge aus.

### Zwei Dinge, die der Assistent bewusst anders macht

**Einstellungen werden nicht als Datei kopiert, sondern gesetzt.** Kodi hält seine
Einstellungen im Speicher und schreibt sie beim Beenden zurück. Eine kopierte
`guisettings.xml` ist deshalb beim nächsten Beenden wieder weg. Der Assistent
setzt diese Werte über JSON-RPC; dann stehen sie im Speicher und Kodi schreibt sie
selbst korrekt weg. Nur Dateien, die Kodi erst bei Bedarf liest — Startmenü,
Favoriten, Quellen, Skin-Einstellungen — werden direkt ersetzt.

**Der Skin bleibt ein manueller Klick.** Kodi lässt einen Skinwechsel aus einem
laufenden Add-on nicht zu, und das ist Absicht: ein Add-on, das die Oberfläche
austauscht, könnte den Nutzer aussperren. Auf dem Gerät wurden alle vier Wege
gemessen, keiner trägt — `Settings.SetSettingValue` lädt den Zielskin, fragt
260 ms später nach und nimmt die Änderung nach weiteren 200 ms unbeantwortet
zurück; die Rückfrage ist aus einem Add-on-Thread nicht zu beantworten; einen
Builtin für den Skinwechsel gibt es nicht; und `lookandfeel.skin` in
`guisettings.xml` zu schreiben hilft nicht, weil Kodi die Datei beim Beenden
überschreibt. Bei einer frischen Installation stellt sich die Frage nicht: dort
installiert Kodi den Skin als Abhängigkeit und fragt von selbst.

## Was repariert wurde

### ZDF — funktionierte überhaupt nicht mehr

`plugin.video.zdf_de_lite` 5.0.2 holte sein API-Token von
`zdf-cdn.live.cellular.de`. Dieser Hostname **löst nicht mehr auf**, ohne Token
scheiterte jede einzelne Abfrage. Das Token steht jetzt dort, wo es auch der
ZDF-Web-Client liest: in der Konfiguration der Senderwebseite. Es ist im
RSC-Payload als JavaScript-String eingebettet, die Anführungszeichen sind
escaped — ein Suchausdruck für reines JSON findet dort nichts.

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
| `repository.jorga` | 2.0.0 | dieses Repository |
| `script.jorga.build` | 1.0.0 | dieses Repository — Einrichtungsassistent |
| `plugin.video.mediatheken` | 1.0.0 | dieses Repository — Sammelpaket und Menü |
| `plugin.video.zdf_de_lite` | 5.0.3 | sarbes 5.0.2, repariert |
| `script.module.libzdf` | 5.0.3 | sarbes 5.0.2, repariert (ZDF **und** 3sat) |
| `script.module.libard` | 6.0.4 | sarbes 6.0.3, repariert |

Die Änderungen stehen je Add-on im `<news>`-Abschnitt der `addon.xml` und sind
damit in Kodi unter *Add-on-Informationen → Änderungsprotokoll* lesbar.

Alles Übrige — Skin, ARD, SRF, ARTE, 3sat, YouTube, TMDb-Helper — kommt aus dem
**offiziellen Kodi-Repository**, das bei jedem Kodi ab Werk eingerichtet ist. Das
ist bewusst so: nichts wird hier doppelt verteilt, nichts veraltet, und die Lizenz
fremder Add-ons bleibt unberührt. Einzige zusätzlich eingebundene Quelle ist das
Repository von **jurialmunkey** für eine aktuelle Fassung des TMDb-Helpers.

## Was dieses Repository nicht leistet

- **Geosperren bleiben Geosperren.** Streams mit `/dach/` im CDN-Pfad antworten
  ausserhalb von Deutschland, Österreich und der Schweiz mit HTTP 403. Betroffen
  ist Lizenzware; Eigenproduktionen der Sender laufen, und das ist der grösste
  Teil des Katalogs. Kein Add-on-Fehler und mit einem Add-on auch nicht zu
  beheben.
- **Jugendschutzsperren bleiben.** Filme mit Altersfreigabe sind erst zur
  Sendezeit abrufbar. Repariert ist nur, dass das eine verständliche Meldung gibt.
- **Keine Bildschirm- und Ton-Einstellungen.** Auflösung und Audio-Ausgabe hängen
  an der Hardware; eine fremde Auflösung aus einer Vorlage kann auf anderer
  Hardware ein schwarzes Bild erzeugen, aus dem der Nutzer nicht mehr
  herausfindet. Diese Werte bleiben deshalb unangetastet.

## Selbst bauen

```
python build.py
```

liest `src/`, legt je Add-on ein ZIP unter `repo/<id>/` ab und erzeugt
`addons.xml` samt `addons.xml.md5`. Stimmt die MD5-Summe nicht zur `addons.xml`,
ignoriert Kodi das Repository stillschweigend — deshalb immer über das Skript
bauen, nie die Dateien von Hand ändern.

Die Vorlage des Assistenten entsteht aus einem gezogenen Gerätestand:

```
python vorlage.py <ordner-mit-userdata>
```

Das Skript filtert dabei heraus, was gerätegebunden ist (Auflösung, Audio-Gerät)
oder vertraulich (Passwörter, Geräte-UUID), und schreibt das Startmenü neu — ein
weitergegebenes Menü darf nur auf Add-ons zeigen, die das Paket auch mitbringt.

Nach dem Bauen `repo/` committen und pushen; die URLs in
`src/repository.jorga/addon.xml` zeigen auf `raw.githubusercontent.com`, das
Repository muss dafür öffentlich sein.

## Lizenz und Urheberschaft

Die drei reparierten Add-ons stammen von **sarbes** und stehen unter
**GPL-2.0-only**; sie behalten Lizenz, Urheberangabe und Quellenverweis. Die
Änderungen sind in der jeweiligen `addon.xml` als solche gekennzeichnet.
`repository.jorga`, `plugin.video.mediatheken` und `script.jorga.build` stehen
ebenfalls unter GPL-2.0-only.

Keines dieser Add-ons wird von einer Sendeanstalt unterstützt. Sie greifen auf die
frei zugänglichen Mediatheken der öffentlich-rechtlichen Sender zu.

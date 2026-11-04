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

Unter **Add-ons → Programm-Add-ons → Jorga Build**. Der Assistent kann dreierlei,
und das sind verschiedene Dinge.

### Eine Einrichtung aus dem Angebot installieren

Der kürzeste Weg auf einem fremden Gerät: **Einrichtung aus dem Angebot
installieren**. Der Assistent liest eine Liste fertiger Einrichtungen aus dem
Netz, zeigt sie mit Namen, Stand und Grösse, lädt die gewählte und spielt sie
ein. Drei Tastendrücke — niemand tippt eine Repository-Adresse auf einer
Fernbedienung ein.

Der Katalog ist eine einzige JSON-Datei; fest eingebaut ist
[`repo/builds.json`](repo/builds.json) aus diesem Repository.

```json
{
  "katalog": "Jorga Builds",
  "builds": [
    {
      "name": "Jorga Standard",
      "kurz": "Mediatheken von ARD, ZDF, SRF, ARTE und 3sat, Skin Mimic-LR",
      "adresse": "builds/jorga-standard-2026-11-04.zip",
      "stand": "2026-11-04",
      "bytes": 6298,
      "kodi_min": 21,
      "kodi_max": 22
    }
  ]
}
```

Eine Adresse ohne `https://` wird relativ zum Katalog gelesen — Katalog und
Pakete lassen sich dadurch zusammen verschieben. `kodi_min`/`kodi_max` blenden
aus, was auf dem Gerät nicht läuft.

**Ein eigener Katalog gehört dir allein.** Unter *Einstellungen → Build-Angebot*
lässt sich eine zweite Adresse eintragen — und zwar nicht nur `http://`:
Kataloge und Pakete werden über Kodis eigene Dateischicht gelesen, also auch
von `smb://` oder `nfs://`. Ein **Ordner auf dem NAS genügt**, ein Webserver
ist nicht nötig. Wer sein eigenes Gerät auf weitere Geräte
bringen will, legt sein Paket samt einer `builds.json` dorthin und hat dieselbe
Auswahlliste — ohne dass das Paket irgendwo veröffentlicht wird. Der eingebaute
Katalog dieses Repositories führt ausschliesslich Einrichtungen, die aus legalen
Quellen bestehen; was sonst auf einem Gerät steht, gehört auf den eigenen
Speicher, nicht hierher.

Dazu zwei Punkte, die das Angebot erst brauchbar machen:

* **Frisch einrichten.** Jede Einrichtung lässt sich auch mit der Schaltfläche
  *Frisch* starten: Startmenü, Favoriten, Quellen, Tastenbelegung, alle
  Add-on-Einstellungen und die geänderten Kodi-Einstellungen gehen vorher weg —
  richtig für ein Gerät, das jemand anders eingerichtet hat. Gesichert wird
  trotzdem zuerst. Die Add-ons selbst bleiben stehen: den laufenden Skin oder
  ein geladenes Python-Modul im Betrieb zu löschen, bringt Kodi zum Absturz,
  und die Einrichtung überschreibt ohnehin alles, was die Oberfläche bestimmt.
* **Aufräumen.** Kodi behält jedes heruntergeladene Add-on-ZIP dauerhaft, und
  der Bildspeicher für Cover wächst unbegrenzt. Unter *Pflege und Sicherung*
  steht beides mit Grössenangabe; der Bildspeicher wird einzeln abgefragt, weil
  Kodi danach neu starten muss.

### Ein ganzes Gerät übertragen

Ein bestehendes Kodi beschreibt sich selbst in einer Paketdatei, ein anderes baut
sich danach auf — mit seinen Add-ons, seinem Startmenü, seinen Einstellungen.

| Punkt | Was er tut |
|---|---|
| Dieses Gerät als Paket sichern | Schreibt Add-on-Liste, Bezugsquellen, Startmenü, Favoriten und Einstellungen in **eine** Datei |
| Gerät aus Paket einrichten | Baut dieses Gerät nach einem Paket auf — aus einer Datei, von einem USB-Stick oder über eine Adresse |
| Was steckt in einem Paket? | Listet Inhalt und Herkunft auf, bevor etwas passiert |

**Die Add-ons selbst stecken nicht im Paket.** Ein gewachsenes Gerät trägt schnell
ein halbes Gigabyte davon, und mitgelieferte Fassungen veralten ab dem Tag des
Packens. Stattdessen stehen im Paket die Kataloge, aus denen die Add-ons stammen;
das Zielgerät lädt daraus die jeweils aktuelle Fassung samt allem, was sie
ihrerseits braucht. Gemessen an einem Gerät mit 120 Add-ons: **330 KB statt
500 MB**.

Zwei Dinge, die dabei leicht übersehen werden und hier gelöst sind:

* **Das offizielle Kodi-Repository fehlt in jeder Erfassung**, weil es in Kodi
  eingebaut ist und nicht im Add-on-Ordner liegt. Ohne es sind drei Dutzend
  Add-ons unauffindbar — `inputstream.adaptive`, die Metadaten-Scraper,
  `pvr.iptvsimple`. Der Assistent ergänzt es anhand der Kodi-Generation.
* **Add-ons, deren Quelle verschwunden ist**, wären sonst für immer weg. Beim
  Erfassen prüft der Assistent jede Kennung gegen die Kataloge und packt genau
  die verwaisten mit ins Paket — und nur die.

Was am Zielgerät nicht gefunden wird, meldet der Assistent namentlich, statt es
zu verschweigen, und spielt alles Übrige trotzdem ein.

**Die Einstellungen der einzelnen Add-ons reisen mit, ihre Zugangsdaten nicht.**
Ohne die Add-on-Einstellungen steht auf dem neuen Gerät zwar jedes Add-on, aber
keines so eingestellt wie zuvor. Mitgenommen wird deshalb je Add-on die
`settings.xml` — und nur die; Caches, Datenbanken und Verläufe bleiben draussen.
Werte unter Schlüsseln wie `password`, `token`, `api.key` oder `uuid` werden
dabei geleert, der Schlüssel selbst bleibt stehen. Das Muster ist an den 2007
belegten Einstellungen eines echten Geräts geprüft: 260 geleert, kein Fehlalarm
— `audiooutput.passthrough` und `debug.showloginfo` bleiben unangetastet,
obwohl „pass" und „login" darin vorkommen.

Aus demselben Grund enthält ein Paket **keine** `guisettings.xml` und keine
`profiles.xml`: die tragen Webserver-Zugang, Geräte-UUID und die am Bildschirm
hängenden Werte mit sich. Gebraucht werden sie ohnehin nicht — die
Kodi-Einstellungen stehen gefiltert in `paket.json` und werden über JSON-RPC
gesetzt.

### Die mitgelieferte Einrichtung einspielen

Die steckt fest in diesem Paket und braucht keine Vorarbeit:

| Punkt | Was er tut |
|---|---|
| Mitgelieferte Einrichtung einspielen | Sichert die bestehende, spielt dann Startmenü, Favoriten, Skin-Einstellungen und 44 Kodi-Einstellungen ein |
| Was wird dabei eingespielt? | Zeigt vorher jede Datei und jede Einstellung an |
| Nur die Konfiguration sichern | Legt eine Sicherung an, ohne etwas zu ändern |
| Sicherung zurückholen | Spielt eine frühere Sicherung wieder ein |

Für das Einrichten mehrerer Geräte geht beides auch ohne Menü:

```
RunScript(script.jorga.build,angebot)
RunScript(script.jorga.build,stand)
RunScript(script.jorga.build,geraet-erfassen)
RunScript(script.jorga.build,geraet-einspielen,<Pfad oder Adresse>,ohne-rueckfrage)
RunScript(script.jorga.build,geraet-einspielen,<Adresse>,frisch)
RunScript(script.jorga.build,einspielen,ohne-rueckfrage)
RunScript(script.jorga.build,sichern)
RunScript(script.jorga.build,zurueckholen)
RunScript(script.jorga.build,aufraeumen,ohne-rueckfrage)
RunScript(script.jorga.build,frisch)
```

Auf einem Gerät, auf dem noch nichts eingerichtet ist, meldet sich der Assistent
beim Start **einmal** von selbst und fragt, ob er einrichten soll — ein
Assistent, den man erst unter Add-ons suchen muss, hilft genau dort nicht, wo er
gebraucht wird. Wer „Nicht mehr fragen" wählt, hat Ruhe; auf einem eingerichteten
Gerät sagt er von sich aus nichts. Steht im Katalog später ein neuerer Stand des
eingespielten Builds, erscheint eine Benachrichtigung — eingespielt wird nichts
von allein.

Sicherungen landen unter `userdata/jorga-sicherungen/` und umfassen Einstellungen,
Startmenü, Favoriten, Quellen, Tastenbelegungen und Skin-Einstellungen. Nicht
dabei sind `Database/` und `Thumbnails/` — die baut Kodi selbst neu auf und sie
machen den Löwenanteil der Datenmenge aus.

### Fünf Dinge, die der Assistent bewusst anders macht

**Binäre Add-ons liegen je Plattform an einer anderen Adresse.** Streaming-Module,
PVR-Schnittstellen, Eingabegeräte und Bildschirmschoner gibt es für jedes
Betriebssystem und jeden Prozessor einmal. Das offizielle Repository führt sie
deshalb sechsfach im Katalog und legt ihre ZIPs in einem Verzeichnis ab, dessen
Name die Plattform trägt — der Dateiname dagegen nicht:

```
.../omega/inputstream.adaptive+android-aarch64/inputstream.adaptive-21.5.25.zip
```

Wer die Adresse ohne diese Unterscheidung zusammensetzt, bekommt 404. Am
04.11.2026 gemessen: betroffen waren `inputstream.adaptive`,
`inputstream.ffmpegdirect`, `inputstream.rtmp`, `pvr.iptvsimple`,
`peripheral.joystick` und jeder Bildschirmschoner — bei einem Gerät mit
Streaming und IPTV also genau das, worauf es ankommt. Der Assistent bestimmt die
Plattform des laufenden Geräts und nimmt nur den passenden Eintrag. Für Linux
nennt das offizielle Repository keine Binär-Add-ons; dort kommen sie aus der
Paketverwaltung der Distribution, und der Assistent lässt sie weg, statt eine
Adresse zu erfinden.

**Ein Paket ist nicht an die Kodi-Fassung seines Ursprungsgeräts gebunden.** Viele
Repositories führen je Kodi-Generation einen eigenen Zweig und benennen ihn im
Pfad (`repo.kodinerds.net/addons/omega/addons.xml`). Ein auf Kodi 21 erfasstes
Paket würde auf Kodi 22 weiter *omega* holen und Add-ons einspielen, die dort
nicht laufen. Der Assistent stellt den Generationsnamen in Katalog und Ablage auf
die Generation des Zielgeräts um und behält die ursprüngliche Adresse als
Rückfall: führt ein Repository den neuen Zweig noch nicht, wird wieder der alte
genommen — ein älteres Add-on ist besser als keines.

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

**Das Startmenü wird an drei Stellen gepflegt, nicht an einer.** Wer bei
`script.skinshortcuts` nur `mainmenu.DATA.xml` ersetzt, sieht keine Wirkung: Die
Widget-Pfade stehen getrennt in `<skin>.properties`, und gerendert wird aus einer
daraus erzeugten Include-Datei im Skin-Ordner. Bleibt die stehen, zeigt das Gerät
trotz eingespielter Dateien weiter das alte Menü — am 03.11.2026 so gemessen. Der
Assistent entfernt sie deshalb, damit Kodi sie neu aufbaut.

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
| `script.jorga.build` | 1.2.1 | dieses Repository — Einrichtungsassistent |
| `plugin.video.mediatheken` | 1.0.0 | dieses Repository — Sammelpaket und Menü |
| `plugin.video.zdf_de_lite` | 5.0.3 | sarbes 5.0.2, repariert |
| `script.module.libzdf` | 5.0.3 | sarbes 5.0.2, repariert (ZDF **und** 3sat) |
| `script.module.libard` | 6.0.4 | sarbes 6.0.3, repariert |

Dazu das Build-Angebot: [`repo/builds.json`](repo/builds.json) als Katalog und
die Pakete darunter in [`repo/builds/`](repo/builds/). Die Einrichtungen dort
bestehen ausschliesslich aus Add-ons der offiziellen Quellen; erzeugt werden sie
mit `python baue-angebot.py`.

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
- **Keine fremden Add-ons im Paket.** Wer ein Gerät überträgt, bekommt eine
  Paketdatei mit Kennungen und Bezugsquellen — die Add-ons selbst lädt das
  Zielgerät bei deren Anbietern. Dieses Repository verteilt also nur, was in der
  Tabelle oben steht. Verschwindet eine fremde Quelle, fehlt ihr Add-on; der
  Assistent sagt dann, welches.
- **Ein erfasstes Gerätepaket gehört dem, der es erzeugt.** Es beschreibt ein
  konkretes Gerät samt dessen vollständiger Add-on-Liste und bleibt deshalb dort,
  wo sein Besitzer es ablegt. Im Angebot dieses Repositories stehen nur
  Einrichtungen aus der Tabelle oben und den offiziellen Quellen —
  `baue-angebot.py` lässt alles weg, was `.gitignore` ignoriert, und
  `geraet-*.zip` steht dort. Für eigene Pakete ist der eigene Katalog da: Paket
  und `builds.json` auf den eigenen Speicher legen, die Adresse unter
  *Einstellungen → Build-Angebot* eintragen. Dieselbe Auswahlliste, nur dass
  nichts davon veröffentlicht wird.

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

Das Build-Angebot entsteht getrennt davon:

```
python baue-angebot.py
```

Es packt die mitgelieferte Vorlage als Paket nach `repo/builds/` und schreibt
`repo/builds.json`. Der Dateiname trägt den Stand, damit ein weitergegebener Link
niemals anderen Inhalt bekommt — dieselbe Regel, die `build.py` für Add-on-ZIPs
über `git cat-file` durchsetzt: was im letzten Commit steht, wird nicht neu
gepackt. Für eine Änderung geht die Versionsnummer hoch.

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

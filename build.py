"""Baut aus src/ ein installierbares Kodi-Repository unter repo/.

Ein Kodi-Repository ist nichts weiter als ein Verzeichnisbaum mit drei Bestandteilen:

    repo/addons.xml           alle addon.xml der enthaltenen Add-ons hintereinander
    repo/addons.xml.md5       die MD5-Summe genau dieser Datei
    repo/<id>/<id>-<ver>.zip  je Add-on ein ZIP, dessen oberster Ordner die ID ist

Kodi liest addons.xml, vergleicht die Versionen mit dem Installierten und laedt bei
Bedarf das passende ZIP. Die MD5-Datei entscheidet, ob Kodi ueberhaupt neu liest -
stimmt sie nicht zur addons.xml, ignoriert Kodi das Repository stillschweigend.

    python build.py

Danach repo/ committen und pushen. Die URLs in repository.jorga/addon.xml zeigen auf
raw.githubusercontent.com, das Repository muss dafuer oeffentlich sein.
"""

import hashlib
import pathlib
import re
import shutil
import xml.etree.ElementTree as ET
import zipfile

WURZEL = pathlib.Path(__file__).parent
SRC = WURZEL / "src"
REPO = WURZEL / "repo"

# Dateien, die nie in ein Add-on-ZIP gehoeren
AUSSCHLUSS_ORDNER = {"__pycache__", ".git", ".idea"}
AUSSCHLUSS_ENDUNG = {".pyc", ".pyo", ".orig", ".rej"}


def addon_ids():
    for p in sorted(SRC.iterdir()):
        if p.is_dir() and (p / "addon.xml").exists():
            yield p


def version_von(addon_xml: pathlib.Path) -> tuple[str, str]:
    wurzel = ET.parse(addon_xml).getroot()
    return wurzel.get("id"), wurzel.get("version")


def packe(ordner: pathlib.Path, ziel: pathlib.Path):
    ziel.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(ziel, "w", zipfile.ZIP_DEFLATED) as z:
        for datei in sorted(ordner.rglob("*")):
            if any(teil in AUSSCHLUSS_ORDNER for teil in datei.parts):
                continue
            if datei.suffix in AUSSCHLUSS_ENDUNG or not datei.is_file():
                continue
            # Oberster Ordner im ZIP muss die Add-on-ID sein, sonst lehnt Kodi ab
            z.write(datei, pathlib.Path(ordner.name) / datei.relative_to(ordner))


def main():
    # Das Verzeichnis wird nicht geleert: aeltere ZIP-Fassungen bleiben liegen.
    # Ein einmal weitergegebener Download-Link soll nicht brechen, nur weil eine
    # neue Fassung gebaut wurde. Kodi nimmt ohnehin die hoechste Version aus
    # addons.xml; wer noch das alte ZIP installiert, wird von dort aktualisiert.
    REPO.mkdir(exist_ok=True)

    teile = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>', "<addons>"]
    gebaut = []

    for ordner in addon_ids():
        kennung, version = version_von(ordner / "addon.xml")
        if kennung != ordner.name:
            raise SystemExit(f"Ordner {ordner.name} traegt die ID {kennung} - muss gleich sein")

        packe(ordner, REPO / kennung / f"{kennung}-{version}.zip")

        # addon.xml ohne eigene XML-Deklaration in die Sammeldatei uebernehmen
        text = (ordner / "addon.xml").read_text(encoding="utf-8")
        text = re.sub(r"^\s*<\?xml[^>]*\?>\s*", "", text)
        teile.append(text.rstrip())

        # Symbole neben das ZIP legen, damit Kodi sie im Browser zeigen kann
        for name, quelle in (("icon.png", "icon.png"), ("fanart.jpg", "fanart.jpg")):
            for kandidat in (ordner / quelle, ordner / "resources" / quelle):
                if kandidat.exists():
                    shutil.copy2(kandidat, REPO / kennung / name)
                    break

        gebaut.append((kennung, version))

    teile.append("</addons>")
    addons_xml = "\n".join(teile) + "\n"

    # newline="" unterbindet die Umwandlung von \n in \r\n unter Windows. Ohne das
    # stimmt die Datei auf der Platte nicht zu der MD5-Summe, die hier aus dem
    # String berechnet wird - und Kodi ignoriert ein Repository mit falscher Summe
    # stillschweigend, ohne jede Fehlermeldung. Dass es ueber GitHub trotzdem lief,
    # lag allein an .gitattributes (eol=lf) und waere bei einem lokalen Test oder
    # einem Klon ohne diese Datei stillschweigend kaputt gewesen.
    with open(REPO / "addons.xml", "w", encoding="utf-8", newline="") as f:
        f.write(addons_xml)

    # Kodi vergleicht die Summe der Bytes, die es laedt - also ueber die kodierte Datei
    summe = hashlib.md5(addons_xml.encode("utf-8")).hexdigest()
    with open(REPO / "addons.xml.md5", "w", encoding="utf-8", newline="") as f:
        f.write(summe)

    print(f"{len(gebaut)} Add-ons gebaut:")
    for kennung, version in gebaut:
        print(f"  {kennung:<34} {version}")

    # Gegenprobe ueber die Datei, nicht ueber den String: nur so faellt auf, wenn
    # das Schreiben die Bytes noch veraendert hat. Eine falsche Summe laesst Kodi
    # das Repository ohne Fehlermeldung ignorieren - das darf nicht durchrutschen.
    roh = (REPO / "addons.xml").read_bytes()
    gelesen = hashlib.md5(roh).hexdigest()
    if gelesen != summe:
        raise SystemExit(
            f"MD5 passt nicht zur geschriebenen Datei: {gelesen} statt {summe}.\n"
            "Kodi wuerde dieses Repository stillschweigend ignorieren."
        )
    print(f"\naddons.xml  {len(roh)} Bytes")
    print(f"MD5         {summe}  (gegen die Datei geprueft)")


if __name__ == "__main__":
    main()

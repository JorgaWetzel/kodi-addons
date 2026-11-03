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
    if REPO.exists():
        shutil.rmtree(REPO)
    REPO.mkdir()

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
    (REPO / "addons.xml").write_text(addons_xml, encoding="utf-8")

    # Kodi vergleicht die Summe der Bytes, die es laedt - also ueber die kodierte Datei
    summe = hashlib.md5(addons_xml.encode("utf-8")).hexdigest()
    (REPO / "addons.xml.md5").write_text(summe, encoding="utf-8")

    print(f"{len(gebaut)} Add-ons gebaut:")
    for kennung, version in gebaut:
        print(f"  {kennung:<34} {version}")
    print(f"\naddons.xml  {len(addons_xml)} Zeichen")
    print(f"MD5         {summe}")


if __name__ == "__main__":
    main()

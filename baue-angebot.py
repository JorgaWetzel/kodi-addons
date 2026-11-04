"""Baut das Build-Angebot: repo/builds/ und repo/builds.json.

Das Angebot ist die Liste fertiger Einrichtungen, die der Assistent beim
Einrichten eines Geräts zur Auswahl zeigt. Es ist etwas anderes als das
Kodi-Repository aus build.py: dort liegen Add-ons, hier liegen Einrichtungen.

    python baue-angebot.py

Daraus entsteht:

    repo/builds/jorga-standard-<stand>.zip   die Einrichtung als Paket
    repo/builds.json                         der Katalog, den der Assistent liest

Der Standard-Build wird aus der Vorlage im Assistenten erzeugt
(src/script.jorga.build/resources/build/) - eine Quelle, zwei Wege: wer den
Assistenten installiert hat, kann sie offline einspielen; wer ein fremdes
Gerät einrichtet, holt dieselbe Einrichtung aus dem Angebot.

Der Dateiname trägt den Stand. Ein schon veröffentlichtes Build-ZIP wird
dadurch nie mit anderem Inhalt überschrieben - dieselbe Regel wie in
build.py, nur hier über den Namen gelöst, weil ein Build im Gegensatz zu
einem Add-on keine Versionsnummer hat.

**Was nicht ins Angebot kommt:** alles, was Git ignoriert. Gerätepakete
heissen geraet-*.zip oder shield-*.zip und stehen in .gitignore; sie
beschreiben ein konkretes Gerät samt dessen Add-on-Liste und gehören dem,
der sie erzeugt hat - nicht in ein öffentliches Angebot. Die Prüfung läuft
über git selbst, damit die Regel an einer Stelle steht.
"""

import json
import os
import pathlib
import re
import subprocess
import time
import xml.etree.ElementTree as ET
import zipfile

WURZEL = pathlib.Path(__file__).parent
SRC = WURZEL / "src"
REPO = WURZEL / "repo"
BUILDS = REPO / "builds"

ASSISTENT = SRC / "script.jorga.build"
VORLAGE = ASSISTENT / "resources" / "build"

# Kodi-Generationen, deren Namen in Katalogpfaden auftauchen. Der Build nennt
# omega; der Assistent stellt die Adressen beim Einspielen auf die Generation
# des Zielgeräts um (paket.fuer_diese_kodi).
OFFIZIELL = "https://mirrors.kodi.tv/addons/omega"

STANDARD = {
    "dateiname": "jorga-standard",
    "name": "Jorga Standard",
    "kurz": "Mediatheken von ARD, ZDF, SRF, ARTE und 3sat, Skin Mimic-LR mit "
            "fertigem Startmenü",
    "kodi_min": 21,
    "kodi_max": 22,
}


def ignoriert(pfad: pathlib.Path) -> bool:
    """True, wenn Git diese Datei ignoriert - dann gehört sie nicht ins Angebot."""
    ergebnis = subprocess.run(
        ["git", "check-ignore", "-q", str(pfad)], cwd=str(WURZEL),
        capture_output=True)
    return ergebnis.returncode == 0


def kataloge() -> list:
    """Die Bezugsquellen des Standard-Builds.

    Gelesen aus der addon.xml des eigenen Repositories, damit Angebot und
    Repository nicht auseinanderlaufen, plus das offizielle Kodi-Repository:
    das ist in Kodi eingebaut, steht in keiner addon.xml und fehlt sonst.
    """
    liste = [{"id": "repository.xbmc.org",
              "addons_xml": OFFIZIELL + "/addons.xml.gz",
              "datadir": OFFIZIELL}]
    wurzel = ET.parse(SRC / "repository.jorga" / "addon.xml").getroot()
    for verzeichnis in wurzel.iter("dir"):
        info = verzeichnis.findtext("info")
        datadir = verzeichnis.find("datadir")
        if not info or datadir is None or not datadir.text:
            continue
        liste.append({"id": _kennung(info.strip(), "repository.jorga"),
                      "addons_xml": info.strip(),
                      "datadir": datadir.text.strip().rstrip("/")})
    return liste


def _kennung(adresse: str, standard: str) -> str:
    """Die Kennung einer Fremdquelle aus ihrer Adresse.

    Das eigene Repository bindet neben der eigenen Quelle die Originalquelle
    des TMDb-Helpers ein. Beide unter derselben Kennung zu führen, wäre für
    jeden irreführend, der sich ein Paket ansieht - im Pfad steht der richtige
    Name schon drin.
    """
    treffer = re.search(r"repository\.[A-Za-z0-9_.-]+", adresse)
    return treffer.group(0).rstrip("/.") if treffer else standard


def addon_liste() -> list:
    """Die Add-ons des Standard-Builds: die Abhängigkeiten des Assistenten.

    Der Assistent selbst und das Repository kommen dazu. Sie sind auf dem
    Zielgerät schon installiert - sonst könnte dort niemand einspielen -,
    gehören aber in die Liste, damit ein "frisch" eingerichtetes Gerät
    seine Aktualisierungen weiter bekommt.
    """
    wurzel = ET.parse(ASSISTENT / "addon.xml").getroot()
    kennungen = {i.get("addon") for i in wurzel.iter("import")
                 if i.get("addon") and not i.get("addon").startswith(("xbmc.", "kodi."))}
    kennungen |= {"script.jorga.build", "repository.jorga"}
    return sorted(kennungen)


def einstellungen() -> dict:
    with open(VORLAGE / "einstellungen.json", encoding="utf-8") as f:
        return json.load(f)


def baue_standard(stand: str) -> pathlib.Path:
    """Packt die mitgelieferte Vorlage als Build-Paket. Gibt den Pfad."""
    ziel = BUILDS / f"{STANDARD['dateiname']}-{stand}.zip"
    if ziel.exists():
        print(f"{ziel.name} liegt schon vor, unverändert gelassen")
        return ziel

    beschreibung = {
        "name": STANDARD["name"],
        "kurz": STANDARD["kurz"],
        "erstellt": time.strftime("%Y-%m-%d %H:%M"),
        "stand": stand,
        "kodi": "",                      # fassungsübergreifend, siehe Modulkopf
        "kodi_min": STANDARD["kodi_min"],
        "kodi_max": STANDARD["kodi_max"],
        "skin": "skin.mimic.lr",
        "kataloge": kataloge(),
        "addons": addon_liste(),
        "einstellungen": einstellungen(),
        "nicht_übernommen": [],
        "quellen_ausgefallen": [],
        "mitgeliefert": [],
    }

    ziel.parent.mkdir(parents=True, exist_ok=True)
    basis = VORLAGE / "userdata"
    with zipfile.ZipFile(ziel, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("paket.json",
                   json.dumps(beschreibung, indent=2, ensure_ascii=False))
        for datei in sorted(basis.rglob("*")):
            if datei.is_file():
                z.write(datei, "userdata/" + datei.relative_to(basis).as_posix())
    print(f"{ziel.name} gebaut: {len(beschreibung['addons'])} Add-ons, "
          f"{len(beschreibung['einstellungen'])} Einstellungen, "
          f"{ziel.stat().st_size // 1024} KB")
    return ziel


def eintrag(zipdatei: pathlib.Path) -> dict:
    """Baut den Katalogeintrag aus der paket.json im ZIP."""
    with zipfile.ZipFile(zipdatei) as z:
        p = json.loads(z.read("paket.json").decode("utf-8"))
    return {
        "name": p.get("name") or zipdatei.stem,
        "kurz": p.get("kurz", ""),
        "adresse": "builds/" + zipdatei.name,
        "stand": p.get("stand") or (p.get("erstellt", "")[:10]),
        "bytes": zipdatei.stat().st_size,
        "kodi_min": p.get("kodi_min"),
        "kodi_max": p.get("kodi_max"),
        "addons": len(p.get("addons", [])),
    }


def main():
    stand = time.strftime("%Y-%m-%d")
    baue_standard(stand)

    # Je Build nur der neueste Stand im Katalog. Ältere ZIPs bleiben liegen,
    # damit ein weitergegebener Link nicht bricht.
    neueste = {}
    übersprungen = []
    for zipdatei in sorted(BUILDS.glob("*.zip")):
        if ignoriert(zipdatei):
            übersprungen.append(zipdatei.name)
            continue
        try:
            e = eintrag(zipdatei)
        except (KeyError, ValueError, zipfile.BadZipFile) as problem:
            print(f"  {zipdatei.name}: keine lesbare paket.json ({problem})")
            continue
        vorher = neueste.get(e["name"])
        if not vorher or (e["stand"] or "") > (vorher["stand"] or ""):
            neueste[e["name"]] = e

    katalog = {
        "katalog": "Jorga Builds",
        "stand": stand,
        "hinweis": "Fertige Kodi-Einrichtungen. Eine Adresse ohne Schema ist "
                   "relativ zu diesem Katalog zu lesen.",
        "builds": [neueste[n] for n in sorted(neueste)],
    }
    with open(REPO / "builds.json", "w", encoding="utf-8", newline="\n") as f:
        json.dump(katalog, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"\nbuilds.json: {len(katalog['builds'])} Build(s)")
    for b in katalog["builds"]:
        print(f"  {b['name']:<20} {b['stand']}  {b['bytes'] // 1024} KB  "
              f"{b['addons']} Add-ons  Kodi {b['kodi_min']}-{b['kodi_max']}")
    if übersprungen:
        print(f"\nnicht ins Angebot (von Git ignoriert): "
              f"{', '.join(übersprungen)}")


if __name__ == "__main__":
    main()

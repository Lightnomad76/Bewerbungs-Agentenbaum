# -*- coding: utf-8 -*-
"""Offline-Selbsttest fuer cvtailoring.py — deterministisch, keine API, kein Netz.

Aufruf:  .\.venv\Scripts\python.exe verify_cvtailoring.py   (exit 0 = alle gruen)
         (kein jobspy noetig -> laeuft auch global: py -3.11 verify_cvtailoring.py)

Prueft: Read-only-Invariante (nichts erfunden/geloescht), Scoring-Ordnung
(Muss>Kann>neutral>0), Stations-/Bullet-Sortierung + Tie-Break, weggelassen =
Score-0-Bullets, muss_fehlt-Durchreichung, Determinismus, Edge-Cases.
"""
from __future__ import annotations

import json
import sys

from jdparser import parse
from tailoring import abgleich
from coverletter import _bewerber_als_text
from cvtailoring import priorisiere, priorisiere_fuer_anzeige


_fails = []
_n = 0


def check(bedingung, name):
    global _n
    _n += 1
    if bedingung:
        print("  OK  " + name)
    else:
        print("  FAIL " + name)
        _fails.append(name)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

ANZEIGE = """Industriemechaniker (m/w/d)

Ihre Aufgaben:
- Wartung und Instandhaltung von Produktionsanlagen
- Montage von Baugruppen
- Fräsen und Drehen von Bauteilen

Ihr Profil:
- Abgeschlossene Ausbildung als Industriemechaniker
- Erfahrung in der CNC-Zerspanung zwingend erforderlich
- Kenntnisse in Hydraulik sind von Vorteil
- SPS-Kenntnisse wünschenswert
"""

BEWERBER = {
    "name": "Max Muster",
    "beruf": "Industriemechaniker",
    "erfahrung": "10 Jahren Berufserfahrung",
    "stationen": [
        {
            "firma": "SAMSON AG",
            "zeitraum": "2018–2024",
            "taetigkeiten": [
                "Wartung und Instandhaltung von Maschinen",
                "CNC-Fräsen und Drehen von Bauteilen",
                "Schweißen nach WIG",
            ],
            "skills": ["Hydraulik", "Pneumatik"],
        },
        {
            "firma": "Müller GmbH",
            "zeitraum": "2014–2018",
            "taetigkeiten": [
                "Montage von Baugruppen",
                "Allgemeine Büroarbeiten",
            ],
            "skills": [],
        },
    ],
}


def _baue():
    jd = parse(ANZEIGE)
    abg = abgleich(jd, parse(_bewerber_als_text(BEWERBER)))
    return jd, abg, priorisiere(BEWERBER, jd, abg)


def main():
    jd, abg, res = _baue()

    print("--- Schema / Grundstruktur ---")
    for k in ("stationen", "weggelassen", "relevant_keywords", "muss_fehlt", "stats"):
        check(k in res, "Top-Level-Key vorhanden: " + k)
    check(len(res["stationen"]) == 2, "2 Stationen im Output")

    print("--- abgleich-Durchreichung ---")
    check(res["relevant_keywords"] == sorted(set(abg["vorhanden"])),
          "relevant_keywords == abgleich.vorhanden")
    check(res["muss_fehlt"] == sorted(abg["muss_fehlt"]),
          "muss_fehlt unveraendert durchgereicht")
    check("Zerspanung" in res["muss_fehlt"],
          "echte MUSS-Luecke (Zerspanung) bleibt sichtbar")
    check("Zerspanung" not in res["relevant_keywords"],
          "fehlendes MUSS NICHT als gedeckt behauptet")

    # Stationen nach Sortierung benannt referenzieren
    st_by_firma = {s["firma"]: s for s in res["stationen"]}
    samson = st_by_firma["SAMSON AG"]
    mueller = st_by_firma["Müller GmbH"]

    print("--- Read-only: nichts erfunden / nichts geloescht ---")
    in_texte = {st["firma"]: set(t.strip() for t in st["taetigkeiten"])
                for st in BEWERBER["stationen"]}
    for st in res["stationen"]:
        out_texte = set(b["text"] for b in st["bullets"]) | \
                    set(b["text"] for b in st["weggelassen"])
        check(out_texte == in_texte[st["firma"]],
              "Station " + st["firma"] + ": Bullets vollstaendig erhalten (keine erfunden/verloren)")
        for b in st["bullets"]:
            check(b["text"] in in_texte[st["firma"]],
                  "kein erfundener Bullet-Text: " + b["text"][:30])

    print("--- Scoring: Muss > Kann > neutral > 0 ---")
    b_cnc = next(b for b in samson["bullets"] if "CNC" in b["text"])
    b_wartung = next(b for b in samson["bullets"] if b["text"].startswith("Wartung"))
    check(b_cnc["score"] == 5, "CNC-Bullet Score 5 (CNC=Muss 3 + Fräsen 1 + Drehen 1)")
    check(b_wartung["score"] == 2, "Wartung-Bullet Score 2 (2x neutral)")
    check(b_cnc["score"] > b_wartung["score"], "Muss-Bullet > neutral-Bullet")
    check("CNC" in b_cnc["treffer"] and "Zerspanung" not in b_cnc["treffer"],
          "treffer nur gedeckte Keywords")

    print("--- Bullet-Sortierung innerhalb Station (Score desc) ---")
    scores = [b["score"] for b in samson["bullets"]]
    check(scores == sorted(scores, reverse=True), "SAMSON-Bullets Score nicht-steigend")
    check(samson["bullets"][0]["text"].startswith("CNC"),
          "hoechstbewerteter Bullet (CNC) steht oben")

    print("--- weggelassen = exakt Score-0-Bullets ---")
    for st in res["stationen"]:
        check(all(b["score"] == 0 for b in st["weggelassen"]),
              "Station " + st["firma"] + ": weggelassen sind alle Score 0")
        check(all(b["score"] > 0 for b in st["bullets"]),
              "Station " + st["firma"] + ": gezeigte Bullets alle Score > 0")
    weg_texte = set(b["text"] for b in res["weggelassen"])
    check("Schweißen nach WIG" in weg_texte, "irrelevanter Bullet (Schweißen/WIG) weggelassen")
    check("Allgemeine Büroarbeiten" in weg_texte, "irrelevanter Bullet (Büroarbeiten) weggelassen")
    check(res["stats"]["weggelassen"] == 2, "stats.weggelassen == 2")

    print("--- Stations-Sortierung (Score desc, Tie-Break Original) ---")
    check(res["stationen"][0]["firma"] == "SAMSON AG",
          "relevantere Station (SAMSON) steht oben")
    check(samson["score"] > mueller["score"], "SAMSON-Score > Müller-Score")
    st_scores = [s["score"] for s in res["stationen"]]
    check(st_scores == sorted(st_scores, reverse=True), "Stationen-Score nicht-steigend")

    print("--- Skills relevant ---")
    check(samson["skills_relevant"] == ["Hydraulik"],
          "SAMSON skills_relevant == [Hydraulik] (Pneumatik nicht in Anzeige)")
    check(all(k in res["relevant_keywords"] for k in samson["skills_relevant"]),
          "skills_relevant ⊆ relevant_keywords")

    print("--- Stats-Konsistenz ---")
    check(res["stats"]["bullets_gesamt"] == 5, "bullets_gesamt == 5")
    check(res["stats"]["bullets_relevant"]
          == sum(len(s["bullets"]) for s in res["stationen"]),
          "bullets_relevant == Summe gezeigter Bullets")
    check(res["stats"]["stationen"] == 2, "stats.stationen == 2")

    print("--- Determinismus ---")
    res2 = priorisiere(BEWERBER, jd, abg)
    check(json.dumps(res, ensure_ascii=False, sort_keys=True)
          == json.dumps(res2, ensure_ascii=False, sort_keys=True),
          "gleiche Inputs -> identischer Output")
    res3 = priorisiere_fuer_anzeige(BEWERBER, ANZEIGE)
    check(json.dumps(res, ensure_ascii=False, sort_keys=True)
          == json.dumps(res3, ensure_ascii=False, sort_keys=True),
          "priorisiere == priorisiere_fuer_anzeige (Bequemlichkeits-Pfad)")

    print("--- Edge-Cases ---")
    leer = priorisiere({"stationen": []}, jd, abg)
    check(leer["stationen"] == [] and leer["stats"]["bullets_gesamt"] == 0,
          "keine Stationen -> leeres, stabiles Ergebnis")
    keine_st = priorisiere({}, jd, abg)
    check(keine_st["stationen"] == [], "Bewerber ohne 'stationen'-Key -> kein Crash")
    leere_anz = priorisiere(BEWERBER, parse(""),
                            abgleich(parse(""), parse(_bewerber_als_text(BEWERBER))))
    check(leere_anz["relevant_keywords"] == [],
          "leere Anzeige -> keine relevanten Keywords")
    check(all(len(s["bullets"]) == 0 for s in leere_anz["stationen"]),
          "leere Anzeige -> alle Bullets Score 0 (nichts faelschlich relevant)")
    nur_leere_bullets = priorisiere(
        {"stationen": [{"firma": "X", "taetigkeiten": ["", "  "], "skills": []}]}, jd, abg)
    check(nur_leere_bullets["stats"]["bullets_gesamt"] == 0,
          "leere/Whitespace-Bullets werden uebersprungen, kein Crash")

    print()
    if _fails:
        print("ERGEBNIS: " + str(_n - len(_fails)) + "/" + str(_n) + " gruen — FEHLER:")
        for f in _fails:
            print("  - " + f)
        return 1
    print("ERGEBNIS: " + str(_n) + "/" + str(_n) + " gruen.")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    sys.exit(main())

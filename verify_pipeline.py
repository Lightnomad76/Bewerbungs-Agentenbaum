# -*- coding: utf-8 -*-
"""End-to-End-Verify der E-C-Pipeline — testet die KOMPOSITION der Module, nicht
jedes Modul isoliert (das tun verify_jdparser/tailoring/cvtailoring/coverletter).

Kette:  jdparser.parse → tailoring.abgleich → cvtailoring.priorisiere
                                            → coverletter.schreibe → critic + factground

Prüft den Vertrag, auf den sich die Generator-Integration (gen_bewerbung_guetepruefer.py)
verlässt: gleiche (Anzeige, Bewerber)-Quelle, **konsistente** Keywords über alle Module,
**durchgängige Ehrlichkeit** (kein muss_fehlt-Keyword wird im Brief behauptet), Writer-Output
besteht critic + factground 0 FEHLER, und die Bequemlichkeits-Pfade sind äquivalent.

Aufruf:  .\.venv\Scripts\python.exe verify_pipeline.py   (exit 0 = alle grün)
         (kein jobspy nötig → auch global py -3.11)
"""
from __future__ import annotations

import sys

from jdparser import parse
from tailoring import abgleich
from cvtailoring import priorisiere, priorisiere_fuer_anzeige
from coverletter import schreibe, schreibe_fuer_anzeige, _bewerber_als_text
from critic import pruefe as critic_pruefe, hat_fehler as critic_hat_fehler
from factground import sammle_fakten, pruefe as fg_pruefe, hat_fehler as fg_hat_fehler


_fails = []
_n = 0


def check(bedingung, name):
    global _n
    _n += 1
    print(("  OK  " if bedingung else "  FAIL ") + name)
    if not bedingung:
        _fails.append(name)


# --- Synthetische Fixtures (muss_fehlt bewusst NICHT leer: testet Ehrlichkeit) ---

ANZEIGE = """Industriemechaniker (m/w/d)

Ihre Aufgaben:
- Wartung und Instandhaltung von Anlagen
- Montage von Baugruppen

Ihr Profil:
- CNC-Erfahrung zwingend erforderlich
- Fräsen zwingend erforderlich
- Englisch von Vorteil
"""

BEWERBER = {
    "name": "Max Muster",
    "email": "max@example.de",
    "telefon": "0123-456",
    "ort": "Musterstadt",
    "beruf": "Industriemechaniker",
    "erfahrung": "10 Jahren Berufserfahrung",
    "stationen": [
        {
            "firma": "Beispiel GmbH",
            "zeitraum": "2015–2024",
            "taetigkeiten": [
                "Wartung und Instandhaltung von Maschinen",
                "Montage von Baugruppen",
                "CNC-Bearbeitung von Bauteilen",
            ],
            "skills": ["Hydraulik"],
        },
    ],
}

DATUM = "01.01.2026"  # fix → Determinismus-Vergleich unabhängig vom Tagesdatum


def main():
    # --- Kette einmal komponieren (wie der Generator es tut) ------------------
    jd = parse(ANZEIGE)
    cv_text = _bewerber_als_text(BEWERBER)
    abg = abgleich(jd, parse(cv_text))
    cvt = priorisiere(BEWERBER, jd, abg)
    brief = schreibe(BEWERBER, jd, abg, datum=DATUM)
    fakten = sammle_fakten(BEWERBER)

    print("--- Kette läuft + Grundannahmen ---")
    check(isinstance(brief, str) and len(brief) > 100, "Brief erzeugt (Kette wirft nicht)")
    check("Fräsen" in abg["muss_fehlt"], "Fixture: MUSS 'Fräsen' fehlt im CV (Ehrlichkeit prüfbar)")
    check("CNC" in abg["vorhanden"], "Fixture: 'CNC' im CV gedeckt")

    print("--- Single-Source-Konsistenz über Module ---")
    check(cvt["relevant_keywords"] == sorted(set(abg["vorhanden"])),
          "cvtailoring.relevant_keywords == tailoring.vorhanden")
    check(cvt["muss_fehlt"] == sorted(abg["muss_fehlt"]),
          "cvtailoring.muss_fehlt == tailoring.muss_fehlt (Durchreichung)")

    print("--- Durchgängige Ehrlichkeit (kein muss_fehlt im Brief) ---")
    for kw in abg["muss_fehlt"]:
        check(kw.lower() not in brief.lower(),
              "Brief behauptet fehlendes MUSS NICHT: " + kw)
    for kw in abg["vorhanden"][:3]:
        pass  # (vorhandene dürfen genannt werden — kein Zwang, nicht asserten)
    check("Fräsen".lower() not in brief.lower(),
          "konkret: 'Fräsen' (nicht im CV) taucht im Brief nicht auf")

    print("--- cvtailoring read-only über die Kette ---")
    in_bullets = set(t.strip() for t in BEWERBER["stationen"][0]["taetigkeiten"])
    st = cvt["stationen"][0]
    out_bullets = set(b["text"] for b in st["bullets"]) | set(b["text"] for b in st["weggelassen"])
    check(out_bullets == in_bullets, "Bullets vollständig erhalten (nichts erfunden/verloren)")

    print("--- Writer-Output besteht beide Gates (end-to-end) ---")
    c_res = critic_pruefe(brief)
    check(not critic_hat_fehler(c_res), "critic.pruefe(brief) = 0 FEHLER")
    fg_res = fg_pruefe(brief, fakten)
    check(not fg_hat_fehler(fg_res),
          "factground.pruefe(brief, fakten) = 0 FEHLER (nichts außerhalb der CV-Fakten behauptet)")

    print("--- Bequemlichkeits-Pfade äquivalent ---")
    check(priorisiere_fuer_anzeige(BEWERBER, ANZEIGE) == cvt,
          "cvtailoring.priorisiere_fuer_anzeige == manuelle Kette")
    check(schreibe_fuer_anzeige(BEWERBER, ANZEIGE, datum=DATUM) == brief,
          "coverletter.schreibe_fuer_anzeige == manuelle Kette")

    print("--- Determinismus der ganzen Kette ---")
    jd2 = parse(ANZEIGE)
    abg2 = abgleich(jd2, parse(_bewerber_als_text(BEWERBER)))
    check(priorisiere(BEWERBER, jd2, abg2) == cvt, "cvtailoring identisch bei Wiederholung")
    check(schreibe(BEWERBER, jd2, abg2, datum=DATUM) == brief, "Brief identisch bei Wiederholung")

    print()
    if _fails:
        print("ERGEBNIS: " + str(_n - len(_fails)) + "/" + str(_n) + " grün — FEHLER:")
        for f in _fails:
            print("  - " + f)
        return 1
    print("ERGEBNIS: " + str(_n) + "/" + str(_n) + " grün.")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    sys.exit(main())

# -*- coding: utf-8 -*-
"""verify_tailoring.py — offline Mechanik-Selbsttest fuer den TailoringAgent.

Prueft gegen synthetische Anzeige/CV-Fixtures (keine PII, kein Netz, kein jobspy),
dass abgleich() vorhandene/fehlende Keywords korrekt trennt, Muss/Kann-Prioritaet
richtig setzt, die Abdeckung rechnet und das Gate hat_luecke greift. exit 0 = gruen.

Lauf: .\\.venv\\Scripts\\python.exe verify_tailoring.py
      (kein jobspy noetig -> auch: py -3.11 verify_tailoring.py)
"""
from __future__ import annotations

import sys

from tailoring import abgleich_texte, abgleich, hat_luecke
from jdparser import parse

_fehler = 0


def ok(bedingung, text, ist=None):
    global _fehler
    marke = "[OK  ]" if bedingung else "[FAIL]"
    extra = "" if bedingung else ("  (ist: " + repr(ist) + ")")
    print("  " + marke + "   " + text + extra)
    if not bedingung:
        _fehler += 1


# Anzeige: Drehen+Fraesen MUSS, SPS KANN, CNC/Wartung neutral.
ANZEIGE = """Industriemechaniker (m/w/d)

Ihr Profil:
- Erfahrung im Drehen und Fraesen zwingend erforderlich
- Kenntnisse in CNC
- Wartung von Anlagen
- SPS-Kenntnisse von Vorteil
"""

# CV: deckt Drehen, CNC, Wartung — aber NICHT Fraesen, NICHT SPS.
CV = """Lebenslauf

Berufserfahrung:
- Drehen von Bauteilen an konventionellen Maschinen
- CNC-Programmierung
- Wartung und Instandhaltung
"""


def main():
    res = abgleich_texte(ANZEIGE, CV)

    print("[1] Vorhanden / fehlend korrekt getrennt")
    ok("Drehen" in res["vorhanden"], "Drehen vorhanden (in beiden)", res["vorhanden"])
    ok("CNC" in res["vorhanden"], "CNC vorhanden")
    ok("Wartung" in res["vorhanden"], "Wartung vorhanden")
    ok("Fräsen" in res["fehlend"], "Fraesen fehlt (nur in Anzeige)", res["fehlend"])
    ok("SPS" in res["fehlend"], "SPS fehlt")
    ok("Drehen" not in res["fehlend"], "Drehen nicht doppelt in fehlend")
    ok(set(res["vorhanden"]) & set(res["fehlend"]) == set(),
       "vorhanden und fehlend disjunkt")

    print("[2] Muss/Kann-Prioritaet")
    ok("Fräsen" in res["muss_fehlt"], "fehlendes MUSS = Fraesen", res["muss_fehlt"])
    ok("Drehen" not in res["muss_fehlt"], "gedecktes MUSS (Drehen) nicht in muss_fehlt")
    ok("SPS" in res["kann_fehlt"], "fehlendes KANN = SPS", res["kann_fehlt"])
    ok(set(res["muss_fehlt"]) & set(res["kann_fehlt"]) == set(),
       "muss_fehlt und kann_fehlt disjunkt")
    ok(set(res["muss_fehlt"]) <= set(res["fehlend"]), "muss_fehlt Teilmenge von fehlend")

    print("[3] Abdeckung + Gate")
    s = res["stats"]
    ok(s["jd_keywords"] > 0, "Anzeige hat Keywords", s)
    ok(s["vorhanden"] + s["fehlend"] == s["jd_keywords"], "vorhanden+fehlend == jd_keywords")
    ok(0 <= s["abdeckung_prozent"] <= 100, "Abdeckung im Bereich 0..100", s["abdeckung_prozent"])
    erwartet = round(100 * s["vorhanden"] / s["jd_keywords"])
    ok(s["abdeckung_prozent"] == erwartet, "Abdeckung korrekt gerechnet", s["abdeckung_prozent"])
    ok(hat_luecke(res) is True, "hat_luecke True (Fraesen-MUSS fehlt)")

    print("[4] Kategorien-Gruppierung der Luecken")
    ok("fertigung" in res["kategorien"], "fehlende fertigung-Kategorie vorhanden", list(res["kategorien"]))
    ok("Fräsen" in res["kategorien"].get("fertigung", []), "Fraesen unter fertigung gelistet")
    alle_kat = [k for liste in res["kategorien"].values() for k in liste]
    ok(sorted(alle_kat) == sorted(res["fehlend"]), "Kategorien decken genau fehlend ab")

    print("[5] Voll-Deckung -> keine Luecke")
    voll = abgleich_texte(ANZEIGE, CV + "\n- Fraesen an CNC-Fraesmaschinen\n- SPS Siemens S7\n")
    ok(voll["muss_fehlt"] == [], "alle MUSS gedeckt -> muss_fehlt leer", voll["muss_fehlt"])
    ok(hat_luecke(voll) is False, "hat_luecke False bei Voll-Deckung")
    ok(voll["stats"]["abdeckung_prozent"] >= res["stats"]["abdeckung_prozent"],
       "Abdeckung steigt bei mehr CV-Deckung")

    print("[6] Negativ / Robustheit")
    leer = abgleich_texte("", "")
    ok(leer["stats"]["jd_keywords"] == 0, "leere Anzeige -> 0 jd_keywords")
    ok(leer["stats"]["abdeckung_prozent"] == 0, "Abdeckung 0 ohne Division-by-zero")
    ok(hat_luecke(leer) is False, "leer -> keine Luecke")
    nur_cv = abgleich_texte("", CV)
    ok(nur_cv["fehlend"] == [] and nur_cv["vorhanden"] == [],
       "leere Anzeige -> nichts vorhanden/fehlend")

    print("[7] abgleich() nimmt parse()-Ergebnisse direkt")
    direkt = abgleich(parse(ANZEIGE), parse(CV))
    ok(direkt["stats"] == res["stats"], "abgleich(parse,parse) == abgleich_texte")

    print("[8] Schema-Stabilitaet")
    ok(set(res.keys()) == {"vorhanden", "fehlend", "muss_fehlt", "kann_fehlt",
                           "kategorien", "stats"},
       "Top-Level-Keys stabil", set(res.keys()))
    ok(set(res["stats"].keys()) == {"jd_keywords", "cv_keywords", "vorhanden", "fehlend",
                                    "muss_fehlt", "kann_fehlt", "abdeckung_prozent"},
       "stats-Keys stabil", set(res["stats"].keys()))

    print("")
    if _fehler == 0:
        print("GRUEN: alle Tailoring-Checks bestanden")
        return 0
    print("ROT: " + str(_fehler) + " Check(s) fehlgeschlagen")
    return 1


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    sys.exit(main())

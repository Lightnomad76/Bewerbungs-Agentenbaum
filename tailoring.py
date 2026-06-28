# -*- coding: utf-8 -*-
"""TailoringAgent / GapAnalysis — deterministischer, offline Abgleich einer
Stellenanzeige gegen den eigenen Lebenslauf.

Pipeline-Rolle (Agenten-Roadmap E-C, vorgezogener Kern von A.4 CVTailoring): bildet
die Bruecke JDParser <-> CV. Beide Seiten werden mit demselben jdparser.parse()
und damit demselben KEYWORD_KATALOG analysiert -> die Kanon-Begriffe sind
vergleichbar (kein Schreibweisen-Drift). Ergebnis: welche Anzeigen-Keywords im CV
**vorhanden** sind und welche **fehlen** — getrennt nach Muss/Kann-Prioritaet.

Das ist der ENTSCHEIDUNGS-Teil des Tailorings (was betonen / was fehlt), NICHT die
Text-Generierung (CoverLetterWriter/CVTailoring-Text = eigene Folge-Etappe).

Grundsatz wie critic/factground/jdparser: der Agent FLAGGT, aendert nichts
(read-only Scope). Er behauptet keine Eignung — er vergleicht nur Vokabular.

EHRLICHE GRENZE (deterministisch, keine LLM): verglichen wird nur Katalog-Vokabular
(jdparser.KEYWORD_KATALOG). Eine im CV anders benannte, sinngleiche Qualifikation
zaehlt nur, wenn beide Seiten denselben Kanon-Begriff treffen. Synonyme ausserhalb
des Katalogs faengt der Abgleich bewusst NICHT — Katalog erweitern statt Schein-Match.

CLI:   python tailoring.py <anzeige-datei> <cv-datei> [--json]
       exit 1 bei fehlenden MUSS-Keywords (Luecke) / 0 sonst.
       (kein jobspy noetig -> auch global: py -3.11 tailoring.py ...)
API:   from tailoring import abgleich, abgleich_texte, hat_luecke, report
       res = abgleich_texte(anzeige_text, cv_text); hat_luecke(res) -> bool
"""
from __future__ import annotations

import sys
import json

from jdparser import parse, keywords_flach


# ---------------------------------------------------------------------------
# Kern-API
# ---------------------------------------------------------------------------


def _kategorie_map(jd_result: dict) -> dict:
    """Kanon-Begriff -> Kategorie (aus dem JDParser-Ergebnis der Anzeige)."""
    kat_von = {}
    for kat, liste in jd_result["keywords"].items():
        for kanon in liste:
            kat_von[kanon] = kat
    return kat_von


def abgleich(jd_result: dict, cv_result: dict) -> dict:
    """Zwei jdparser.parse()-Ergebnisse vergleichen (Anzeige vs. CV).

    Gibt {vorhanden, fehlend, muss_fehlt, kann_fehlt, kategorien, stats} zurueck.
    Bezug ist immer die ANZEIGE: 'vorhanden' = vom CV gedeckte Anzeigen-Keywords."""
    jd_kw = set(keywords_flach(jd_result))
    cv_kw = set(keywords_flach(cv_result))

    vorhanden = jd_kw & cv_kw
    fehlend = jd_kw - cv_kw

    muss = set(jd_result["anforderungen"]["muss"])
    kann = set(jd_result["anforderungen"]["kann"])
    muss_fehlt = muss - cv_kw
    kann_fehlt = (kann - cv_kw) - muss_fehlt  # muss hat Vorrang

    kat_von = _kategorie_map(jd_result)
    # fehlende Keywords nach Kategorie gruppiert (fuer den Report)
    kategorien = {}
    for kanon in sorted(fehlend):
        kategorien.setdefault(kat_von.get(kanon, "sonstige"), []).append(kanon)

    n_jd = len(jd_kw)
    abdeckung = round(100 * len(vorhanden) / n_jd) if n_jd else 0
    return {
        "vorhanden": sorted(vorhanden),
        "fehlend": sorted(fehlend),
        "muss_fehlt": sorted(muss_fehlt),
        "kann_fehlt": sorted(kann_fehlt),
        "kategorien": kategorien,
        "stats": {
            "jd_keywords": n_jd,
            "cv_keywords": len(cv_kw),
            "vorhanden": len(vorhanden),
            "fehlend": len(fehlend),
            "muss_fehlt": len(muss_fehlt),
            "kann_fehlt": len(kann_fehlt),
            "abdeckung_prozent": abdeckung,
        },
    }


def abgleich_texte(anzeige_text: str, cv_text: str) -> dict:
    """Bequemlichkeit: Roh-Texte -> parse() -> abgleich()."""
    return abgleich(parse(anzeige_text), parse(cv_text))


def hat_luecke(result: dict) -> bool:
    """True, wenn mind. ein MUSS-Keyword der Anzeige im CV fehlt (Pipeline-Gate)."""
    return result["stats"]["muss_fehlt"] > 0


# ---------------------------------------------------------------------------
# CLI / Report
# ---------------------------------------------------------------------------

_KAT_LABEL = {
    "fertigung": "Fertigung/Verfahren",
    "mess_qs": "Messtechnik/QS",
    "steuerung_it": "Steuerung/IT",
    "normen": "Normen",
    "soft": "Soft Skills",
    "sprachen": "Sprachen",
    "sonstige": "Sonstige",
}


def report(jd_quelle: str, cv_quelle: str, result: dict) -> str:
    s = result["stats"]
    out = []
    out.append("=== TailoringAgent — Anzeige <-> CV Keyword-Abgleich ===")
    out.append("Anzeige: " + jd_quelle)
    out.append("CV:      " + cv_quelle)
    out.append("Abdeckung: " + str(s["abdeckung_prozent"]) + "%  ("
               + str(s["vorhanden"]) + " von " + str(s["jd_keywords"])
               + " Anzeigen-Keywords im CV)")
    out.append("")
    if result["muss_fehlt"]:
        out.append("MUSS fehlt im CV (" + str(s["muss_fehlt"]) + ") — vorrangig pruefen:")
        out.append("  " + ", ".join(result["muss_fehlt"]))
        out.append("")
    if result["kann_fehlt"]:
        out.append("KANN fehlt im CV (" + str(s["kann_fehlt"]) + ") — optional ergaenzen:")
        out.append("  " + ", ".join(result["kann_fehlt"]))
        out.append("")
    if result["fehlend"]:
        out.append("Alle fehlenden Anzeigen-Keywords nach Kategorie ("
                   + str(s["fehlend"]) + "):")
        for kat, liste in result["kategorien"].items():
            out.append("  " + _KAT_LABEL.get(kat, kat) + ": " + ", ".join(liste))
        out.append("")
    if result["vorhanden"]:
        out.append("Im CV gedeckt (" + str(s["vorhanden"]) + ") — im Brief betonen:")
        out.append("  " + ", ".join(result["vorhanden"]))
        out.append("")
    if s["muss_fehlt"] == 0:
        out.append("GRUEN: alle MUSS-Keywords der Anzeige im CV gedeckt ("
                   + str(s["kann_fehlt"]) + " KANN offen).")
    else:
        out.append("LUECKE: " + str(s["muss_fehlt"]) + " MUSS-Keyword(s) fehlen im CV — "
                   + "vor Bewerbung pruefen (nachweisbar? anders benannt? echte Luecke?).")
    return "\n".join(out)


def _read(pfad: str) -> str:
    with open(pfad, "r", encoding="utf-8") as fh:
        return fh.read()


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("--")]
    flags = {a for a in argv[1:] if a.startswith("--")}
    if len(args) < 2:
        print("Aufruf: python tailoring.py <anzeige-datei> <cv-datei> [--json]",
              file=sys.stderr)
        return 2
    jd_pfad, cv_pfad = args[0], args[1]
    try:
        anzeige = _read(jd_pfad)
        cv = _read(cv_pfad)
    except OSError as e:
        print("FEHLER: Datei nicht lesbar: " + str(e), file=sys.stderr)
        return 2

    result = abgleich_texte(anzeige, cv)
    if "--json" in flags:
        print(json.dumps({"anzeige": jd_pfad, "cv": cv_pfad, **result},
                         ensure_ascii=False, indent=2))
    else:
        print(report(jd_pfad, cv_pfad, result))
    return 1 if hat_luecke(result) else 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    sys.exit(main(sys.argv))

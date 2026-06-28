# -*- coding: utf-8 -*-
"""CVTailoringAgent — deterministisches, offline Umsortieren/Gewichten der
CV-Stationen + -Bullets nach einer konkreten Stellenanzeige.

Pipeline-Rolle (Agenten-Roadmap E-C / A.4, Text-Writer Sub-2): Gegenstueck zum
CoverLetterWriter. Waehrend der Brief frei formuliert, ordnet dieser Agent die
**bestehenden** CV-Inhalte so, dass die fuer die Anzeige relevanten Stationen und
Taetigkeiten oben/prominent stehen.

GATING-ENTSCHEIDUNG (User 2026-06-28): **deterministischer Default** — KEINE LLM-API
(wie Sub-1). Score je Bullet = gewichtete Anzahl Treffer der Anzeigen-Keywords, die
**im CV gedeckt** sind (`abgleich.vorhanden`); Muss > Kann > neutral.

WICHTIG (read-only Geist, §3.3): der Agent **erfindet nichts und loescht nichts**. Er
veraendert keinen Bullet-Text — er sortiert nur (Stationen + Bullets) und schlaegt vor,
nicht-anzeigenrelevante Bullets (Score 0) **wegzulassen** (`weggelassen`); sie bleiben
im Output dokumentiert, werden nicht aus den Stammdaten entfernt. Fehlende MUSS-Keywords
(`muss_fehlt`) werden **durchgereicht, nicht aufgefuellt** — eine echte Luecke bleibt sichtbar.

EHRLICHE GRENZE (deterministisch, keine LLM): bewertet wird nur Katalog-Vokabular
(jdparser.KEYWORD_KATALOG, via tailoring.abgleich). Eine sinngleiche, anders benannte
Taetigkeit zaehlt nur, wenn beide Seiten denselben Kanon-Begriff treffen — Katalog
erweitern statt Schein-Match.

Bewerber-Schema = identisch zu coverletter.py (Single-Source):
  {name, beruf, erfahrung, stationen: [{firma, zeitraum, taetigkeiten:[str], skills:[str]}]}

CLI:   python cvtailoring.py <anzeige-datei> <bewerber.json> [--json]
API:   from cvtailoring import priorisiere, priorisiere_fuer_anzeige
       res = priorisiere_fuer_anzeige(bewerber, anzeige_text)
"""
from __future__ import annotations

import sys
import json

from jdparser import parse, keywords_flach
from tailoring import abgleich
from coverletter import _bewerber_als_text


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


def _gewicht(kanon: str, muss: set, kann: set) -> int:
    """Gewicht eines Kanon-Begriffs: Muss=3, Kann=2, neutral=1."""
    if kanon in muss:
        return 3
    if kanon in kann:
        return 2
    return 1


def _keywords_von(text: str) -> set:
    """Kanon-Begriffe in einem freien Text (Bullet/Skill-Zeile)."""
    return set(keywords_flach(parse(text)))


def _bewerten(text: str, relevant: set, muss: set, kann: set) -> dict:
    """Einen Bullet bewerten: nur Anzeigen-Keywords zaehlen, die im CV gedeckt sind
    (relevant = abgleich.vorhanden). Gibt {text, score, treffer}."""
    treffer = sorted(_keywords_von(text) & relevant)
    score = sum(_gewicht(k, muss, kann) for k in treffer)
    return {"text": text, "score": score, "treffer": treffer}


# ---------------------------------------------------------------------------
# Kern-API
# ---------------------------------------------------------------------------


def priorisiere(bewerber: dict, jd_result: dict, abgleich_result: dict) -> dict:
    """CV-Stationen + Bullets nach Anzeigen-Relevanz umsortieren/gewichten.

    Veraendert KEINE Inhalte: sortiert nur und partitioniert je Station in
    `bullets` (Score>0, relevant) und `weggelassen` (Score 0, Vorschlag wegzulassen).
    Stationen werden nach Relevanz-Score absteigend sortiert; Tie-Break =
    Original-Reihenfolge (= antichronologisch, wenn die Stammdaten neu->alt erfasst sind).
    """
    relevant = set(abgleich_result.get("vorhanden", []) or [])
    muss = set(jd_result.get("anforderungen", {}).get("muss", []) or [])
    kann = set(jd_result.get("anforderungen", {}).get("kann", []) or [])

    stationen_out = []
    weggelassen_gesamt = []
    n_bullets = 0

    for idx, st in enumerate(bewerber.get("stationen", []) or []):
        firma = (st.get("firma") or "").strip()
        zeitraum = (st.get("zeitraum") or "").strip()
        taetigkeiten = st.get("taetigkeiten", []) or []
        skills = st.get("skills", []) or []

        # jeden Bullet bewerten, Original-Index als stabilen Tie-Break behalten
        bewertet = []
        for b_idx, text in enumerate(taetigkeiten):
            text = (text or "").strip()
            if not text:
                continue
            n_bullets += 1
            b = _bewerten(text, relevant, muss, kann)
            b["_idx"] = b_idx
            bewertet.append(b)

        # Score>0 = zeigen (nach Score desc, dann Original-Reihenfolge);
        # Score==0 = nachrangig / Vorschlag wegzulassen (Original-Reihenfolge)
        zeigen = sorted([b for b in bewertet if b["score"] > 0],
                        key=lambda b: (-b["score"], b["_idx"]))
        weg = sorted([b for b in bewertet if b["score"] == 0],
                     key=lambda b: b["_idx"])
        for b in zeigen + weg:
            b.pop("_idx", None)

        # Skills, die anzeigenrelevant + im CV gedeckt sind
        skills_kw = _keywords_von(", ".join(skills)) if skills else set()
        skills_relevant = sorted(skills_kw & relevant)

        bullet_score = sum(b["score"] for b in zeigen)
        skill_score = sum(_gewicht(k, muss, kann) for k in skills_relevant)
        st_score = bullet_score + skill_score

        for b in weg:
            weggelassen_gesamt.append({"firma": firma, "text": b["text"]})

        stationen_out.append({
            "firma": firma,
            "zeitraum": zeitraum,
            "original_index": idx,
            "score": st_score,
            "bullets": zeigen,
            "weggelassen": weg,
            "skills_relevant": skills_relevant,
        })

    # Stationen: Relevanz-Score desc, Tie-Break = Original-Reihenfolge
    stationen_out.sort(key=lambda s: (-s["score"], s["original_index"]))

    return {
        "stationen": stationen_out,
        "weggelassen": weggelassen_gesamt,
        "relevant_keywords": sorted(relevant),
        "muss_fehlt": sorted(abgleich_result.get("muss_fehlt", []) or []),
        "stats": {
            "stationen": len(stationen_out),
            "bullets_gesamt": n_bullets,
            "bullets_relevant": sum(len(s["bullets"]) for s in stationen_out),
            "weggelassen": len(weggelassen_gesamt),
            "muss_fehlt": len(abgleich_result.get("muss_fehlt", []) or []),
        },
    }


def priorisiere_fuer_anzeige(bewerber: dict, anzeige_text: str) -> dict:
    """Bequemlichkeit: parse(anzeige) + abgleich(gegen Bewerber-CV) + priorisiere()."""
    jd = parse(anzeige_text)
    abg = abgleich(jd, parse(_bewerber_als_text(bewerber)))
    return priorisiere(bewerber, jd, abg)


# ---------------------------------------------------------------------------
# CLI / Report
# ---------------------------------------------------------------------------


def report(quelle: str, result: dict) -> str:
    s = result["stats"]
    out = []
    out.append("=== CVTailoringAgent — Stationen/Bullets nach Anzeigen-Relevanz ===")
    out.append("Anzeige: " + quelle)
    out.append("Relevante (im CV gedeckte) Anzeigen-Keywords ("
               + str(len(result["relevant_keywords"])) + "): "
               + (", ".join(result["relevant_keywords"]) or "—"))
    out.append("")
    for n, st in enumerate(result["stationen"], 1):
        kopf = st["firma"] or "(Station " + str(st["original_index"] + 1) + ")"
        if st["zeitraum"]:
            kopf += " (" + st["zeitraum"] + ")"
        out.append(str(n) + ". " + kopf + "  [Score " + str(st["score"]) + "]")
        for b in st["bullets"]:
            tr = ("  <- " + ", ".join(b["treffer"])) if b["treffer"] else ""
            out.append("   + (" + str(b["score"]) + ") " + b["text"] + tr)
        for b in st["weggelassen"]:
            out.append("   - (0) " + b["text"] + "  [nicht anzeigenrelevant]")
        if st["skills_relevant"]:
            out.append("   Skills relevant: " + ", ".join(st["skills_relevant"]))
        out.append("")
    if result["muss_fehlt"]:
        out.append("MUSS fehlt im CV (" + str(s["muss_fehlt"])
                   + ") — NICHT erfindbar, vor Bewerbung pruefen:")
        out.append("  " + ", ".join(result["muss_fehlt"]))
    else:
        out.append("Alle MUSS-Keywords der Anzeige im CV gedeckt.")
    out.append("Wegzulassen vorgeschlagen (Score 0): " + str(s["weggelassen"])
               + " Bullet(s) — nicht geloescht, nur nachrangig.")
    return "\n".join(out)


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("--")]
    flags = {a for a in argv[1:] if a.startswith("--")}
    if len(args) < 2:
        print("Aufruf: python cvtailoring.py <anzeige-datei> <bewerber.json> [--json]",
              file=sys.stderr)
        return 2
    try:
        with open(args[0], "r", encoding="utf-8") as fh:
            anzeige = fh.read()
        with open(args[1], "r", encoding="utf-8") as fh:
            bewerber = json.load(fh)
    except OSError as e:
        print("FEHLER: Datei nicht lesbar: " + str(e), file=sys.stderr)
        return 2
    except json.JSONDecodeError as e:
        print("FEHLER: bewerber.json ungültig: " + str(e), file=sys.stderr)
        return 2

    result = priorisiere_fuer_anzeige(bewerber, anzeige)
    if "--json" in flags:
        print(json.dumps({"anzeige": args[0], **result}, ensure_ascii=False, indent=2))
    else:
        print(report(args[0], result))
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    sys.exit(main(sys.argv))

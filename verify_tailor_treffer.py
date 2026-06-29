"""verify_tailor_treffer.py — Mechanik-Selbsttest des per-Treffer-Tailoring (OHNE Netz).

Prüft deterministisch gegen synthetische Treffer + CV-Text (kein PII, kein Netz):
JSON-Lade-Robustheit, Anzeige-Text-Bau, Abdeckung%/muss_fehlt-Logik, read-only
(Eingabe unverändert), Reihenfolge-Erhalt, top-Begrenzung.

Lauf:  .\.venv\Scripts\python.exe verify_tailor_treffer.py     (exit 0 = grün)
"""
from __future__ import annotations

import copy
import json
import sys
import tempfile
from pathlib import Path

import tailor_treffer as tt

FEHLER: list[str] = []


def check(bedingung: bool, msg: str) -> None:
    if bedingung:
        print(f"  [OK]   {msg}")
    else:
        print(f"  [FAIL] {msg}")
        FEHLER.append(msg)


# CV-Text deckt Fräsen/Drehen, NICHT Schweißen.
CV_TEXT = "Industriemechaniker. Erfahrung in Fräsen und Drehen an CNC-Maschinen. Qualitätsprüfung mit Messschieber."

# Treffer 1: passt gut (Fräsen/Drehen im CV). Treffer 2: verlangt Schweißen (Lücke).
TREFFER = [
    {"title": "Industriemechaniker Fräsen (m/w/d)", "company": "A GmbH", "location": "Obertshausen",
     "site": "indeed", "description": "Sie übernehmen Fräsen und Drehen an CNC-Maschinen, dazu Qualitätsprüfung.",
     "such_titel": ["Industriemechaniker"], "job_url": "u1",
     "match": {"score": 40, "distanz_km": 0}},
    {"title": "Schweißer (m/w/d)", "company": "B AG", "location": "Hanau",
     "site": "servicebund",
     "description": "Wir suchen einen Schweißer. Voraussetzung: Schweißen nach Norm ist zwingend erforderlich. WIG-Kenntnisse erforderlich.",
     "such_titel": "service.bund", "job_url": "u2",
     "match": {"score": 10, "distanz_km": 12}},
]


def test_lade_robustheit() -> None:
    print("[1] lade_treffer: beide Formate")
    with tempfile.TemporaryDirectory() as d:
        p1 = Path(d) / "wrapped.json"
        p1.write_text(json.dumps({"meta": {}, "treffer": TREFFER}), encoding="utf-8")
        check(len(tt.lade_treffer(p1)) == 2, "{meta,treffer}-Format gelesen")
        p2 = Path(d) / "bare.json"
        p2.write_text(json.dumps(TREFFER), encoding="utf-8")
        check(len(tt.lade_treffer(p2)) == 2, "nackte Liste gelesen")
        p3 = Path(d) / "empty.json"
        p3.write_text(json.dumps({"meta": {}}), encoding="utf-8")
        check(tt.lade_treffer(p3) == [], "fehlendes treffer-Feld -> []")


def test_anzeige_text() -> None:
    print("[2] anzeige_text: Felder + such_titel (Liste/Skalar)")
    txt = tt.anzeige_text(TREFFER[0])
    check("Fräsen" in txt and "A GmbH" in txt, "title/company/description drin")
    check("Industriemechaniker" in txt, "such_titel (Liste) drin")
    txt2 = tt.anzeige_text(TREFFER[1])
    check("service.bund" in txt2, "such_titel (Skalar) drin")


def test_abdeckung() -> None:
    print("[3] Abdeckung + muss_fehlt-Logik")
    rows = tt.tailor_treffer(TREFFER, CV_TEXT)
    r1, r2 = rows[0], rows[1]
    check(r1["abdeckung_prozent"] >= r2["abdeckung_prozent"],
          "passender Treffer (Fräsen) hat >= Abdeckung als Schweißer-Lücke")
    check("schweißen" in [m.lower() for m in r2["muss_fehlt"]]
          or any("schwei" in m.lower() for m in r2["muss_fehlt"] + r2["kann_fehlt"]),
          "Schweißen als Lücke erkannt (nicht im CV)")
    check(r1["score"] == 40 and r1["distanz_km"] == 0, "match-Score/Distanz durchgereicht")
    check(r1["site"] == "indeed" and r2["site"] == "servicebund", "site durchgereicht")


def test_readonly_und_reihenfolge() -> None:
    print("[4] read-only + Reihenfolge-Erhalt + top")
    snapshot = copy.deepcopy(TREFFER)
    rows = tt.tailor_treffer(TREFFER, CV_TEXT)
    check(TREFFER == snapshot, "Eingabe-Treffer unverändert (read-only)")
    check([r["title"] for r in rows] == [t["title"] for t in TREFFER],
          "Reihenfolge = Eingabe (match-priorisiert)")
    check(len(tt.tailor_treffer(TREFFER, CV_TEXT, top=1)) == 1, "top=1 begrenzt")


def test_report() -> None:
    print("[5] report: lesbar, kein Crash bei leer")
    rep = tt.report(tt.tailor_treffer(TREFFER, CV_TEXT))
    check("Abdeckung" in rep and "MUSS" in rep, "Report enthält Abdeckung + MUSS")
    check(tt.report([]).strip().endswith("(keine Treffer)"), "leere Liste -> Hinweis statt Crash")


def main() -> int:
    print("=== verify_tailor_treffer (offline) ===")
    test_lade_robustheit()
    test_anzeige_text()
    test_abdeckung()
    test_readonly_und_reihenfolge()
    test_report()
    print()
    if FEHLER:
        print(f"ERGEBNIS: {len(FEHLER)} FAIL — {FEHLER}")
        return 1
    print("ERGEBNIS: alle Checks grün.")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    raise SystemExit(main())

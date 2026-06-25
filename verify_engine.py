"""verify_engine.py — Mechanik-Selbsttest der Daten-Engine (OHNE Netz).

Prüft deterministisch: Profil-Parsing, Dedup, JSON/CSV-Schema, NaN/Datums-Sicherheit.
Der echte Netz-Lauf (scrape_jobs) ist separat: `py -3.11 main.py`.

Lauf:  py -3.11 verify_engine.py     (exit 0 = grün)
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import pandas as pd

import main as engine

FEHLER: list[str] = []


def check(bedingung: bool, msg: str) -> None:
    if bedingung:
        print(f"  [OK]   {msg}")
    else:
        print(f"  [FAIL] {msg}")
        FEHLER.append(msg)


def test_profil_parsing() -> None:
    print("[1] ProfileAgent: jobprofil.yaml parsen")
    p = engine.lade_profil()
    check(bool(p.jobtitel), f"jobtitel nicht leer ({len(p.jobtitel)} Titel)")
    check(bool(p.sites), f"mind. eine Quelle aktiv ({p.sites})")
    check(all(s in engine.GUELTIGE_QUELLEN for s in p.sites), "alle Quellen gültige JobSpy-site_names")
    check(isinstance(p.remote, bool), f"remote ist bool (null->False): {p.remote}")
    check(p.job_type is None or isinstance(p.job_type, str), "job_type None oder str")
    check(isinstance(p.results_wanted, int), "results_wanted ist int")


def _synth_df() -> pd.DataFrame:
    """Synthetischer scrape_jobs-artiger DataFrame mit Dublette, NaN, Datum."""
    return pd.DataFrame([
        {"job_url": "https://x/1", "title": "Industriemechaniker", "company": "ACME",
         "location": "Musterstadt", "date_posted": pd.Timestamp("2026-06-20"),
         "min_amount": 42000, "max_amount": float("nan"), "such_titel": "Industriemechaniker"},
        {"job_url": "https://x/1", "title": "Industriemechaniker", "company": "ACME",  # exakte URL-Dublette
         "location": "Musterstadt", "date_posted": pd.Timestamp("2026-06-20"),
         "min_amount": 42000, "max_amount": float("nan"), "such_titel": "Qualitätssicherung"},
        {"job_url": "https://x/2", "title": "Qualitätsprüfer", "company": "Beta GmbH",
         "location": "Offenbach", "date_posted": pd.NaT,
         "min_amount": float("nan"), "max_amount": 55000, "such_titel": "Qualitätsprüfer"},
    ])


def test_dedup() -> None:
    print("[2] ReportAgent: Dedup")
    out = engine.dedupliziere(_synth_df())
    check(len(out) == 2, f"3 Roh -> 2 dedupliziert (ist {len(out)})")
    # K2: such_titel der URL-Dublette (x/1) muss beide Such-Titel als Liste tragen
    zeile = out[out["job_url"] == "https://x/1"].iloc[0]
    st = zeile["such_titel"]
    check(isinstance(st, list) and set(st) == {"Industriemechaniker", "Qualitätssicherung"},
          f"K2: such_titel je Schlüssel aggregiert (ist {st})")


def test_dedup_k1() -> None:
    print("[2b] ReportAgent: K1 — gleiche(r) Titel/Firma/Ort, andere job_url bleibt erhalten")
    df = pd.DataFrame([
        {"job_url": "https://x/1", "title": "Industriemechaniker", "company": "ACME",
         "location": "Stadt", "such_titel": "Industriemechaniker"},
        {"job_url": "https://x/2", "title": "Industriemechaniker", "company": "ACME",
         "location": "Stadt", "such_titel": "Industriemechaniker"},
    ])
    out = engine.dedupliziere(df)
    check(len(out) == 2, f"K1: 2 verschiedene job_url bleiben 2 (ist {len(out)})")


def test_report_schema() -> None:
    print("[3] ReportAgent: JSON/CSV-Schema + NaN/Datum-Sicherheit")
    p = engine.lade_profil()
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        orig_json, orig_csv = engine.OUT_JSON, engine.OUT_CSV
        engine.OUT_JSON, engine.OUT_CSV = tdp / "t.json", tdp / "t.csv"
        try:
            n = engine.schreibe_report(_synth_df(), p)
            check(n == 2, f"schreibe_report meldet 2 Treffer (ist {n})")
            check(engine.OUT_JSON.exists(), "JSON-Datei geschrieben")
            check(engine.OUT_CSV.exists(), "CSV-Datei geschrieben")
            payload = json.loads(engine.OUT_JSON.read_text(encoding="utf-8"))  # invalid JSON -> Exception
            check("meta" in payload and "treffer" in payload, "Schema hat meta + treffer")
            check(payload["meta"]["anzahl"] == 2, "meta.anzahl == 2")
            check(len(payload["treffer"]) == 2, "treffer-Liste hat 2 Einträge")
            # NaN muss als JSON null (Python None) landen, nicht als float('nan')
            nan_ok = any(t.get("max_amount") is None for t in payload["treffer"])
            check(nan_ok, "NaN korrekt als null serialisiert")
            # NaT-Datum -> null
            nat_ok = any(t.get("date_posted") is None for t in payload["treffer"])
            check(nat_ok, "NaT-Datum korrekt als null serialisiert")
        finally:
            engine.OUT_JSON, engine.OUT_CSV = orig_json, orig_csv


def test_schema_stabil() -> None:
    print("[3b] ReportAgent: S1 — Kernschema stabil trotz fehlender/zusätzlicher Spalten")
    p = engine.lade_profil()
    df = pd.DataFrame([{"title": "X", "company": "Y", "job_url": "u1",
                        "such_titel": "X", "extra_spalte": "soll_weg"}])
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        orig_json, orig_csv = engine.OUT_JSON, engine.OUT_CSV
        engine.OUT_JSON, engine.OUT_CSV = tdp / "t.json", tdp / "t.csv"
        try:
            engine.schreibe_report(df, p)
            payload = json.loads(engine.OUT_JSON.read_text(encoding="utf-8"))
            keys = set(payload["treffer"][0].keys())
            erwartet = set(engine.KERN) | {"match"}
            check(keys == erwartet, f"Treffer-Keys == KERN + match (ist {sorted(keys)})")
            check("extra_spalte" not in keys, "fremde Spalte nicht im JSON")
            # fehlende Kernspalte (z.B. description) ist als null vorhanden, nicht abwesend
            check("description" in keys and payload["treffer"][0]["description"] is None,
                  "fehlende Kernspalte als null vorhanden")
        finally:
            engine.OUT_JSON, engine.OUT_CSV = orig_json, orig_csv


def test_leerer_report() -> None:
    print("[4] ReportAgent: leerer DataFrame (0 Treffer) bricht nicht")
    p = engine.lade_profil()
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        orig_json, orig_csv = engine.OUT_JSON, engine.OUT_CSV
        engine.OUT_JSON, engine.OUT_CSV = tdp / "t.json", tdp / "t.csv"
        try:
            n = engine.schreibe_report(pd.DataFrame(), p)
            check(n == 0, "0 Treffer gemeldet")
            payload = json.loads(engine.OUT_JSON.read_text(encoding="utf-8"))
            check(payload["treffer"] == [], "treffer ist leere Liste")
        finally:
            engine.OUT_JSON, engine.OUT_CSV = orig_json, orig_csv


def main() -> int:
    print("=== verify_engine.py (offline Mechanik-Selbsttest) ===")
    test_profil_parsing()
    test_dedup()
    test_dedup_k1()
    test_report_schema()
    test_schema_stabil()
    test_leerer_report()
    print("---")
    if FEHLER:
        print(f"ROT: {len(FEHLER)} Fehler")
        return 1
    print("GRÜN: alle Mechanik-Checks bestanden")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

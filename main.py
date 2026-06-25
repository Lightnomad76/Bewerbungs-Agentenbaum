"""main.py — Jobsuche-Agent v1 (Daten-Engine, read-only).

Pipeline: ProfileAgent -> SearchAgent -> ReportAgent.
Liest profile/jobprofil.yaml, sucht via JobSpy (Indeed/Google/...), legt
Roh-Treffer als treffer_v1.json (Bridge zur späteren Web-UI) + treffer_v1.csv ab.

Start:  py -3.11 main.py
Scope:  NUR suchen + ablegen. Kein Login, kein Auto-Bewerben, kein Scoring (= Etappe 2).
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yaml
from jobspy import scrape_jobs

BASE = Path(__file__).resolve().parent
PROFIL_PFAD = BASE / "profile" / "jobprofil.yaml"
OUT_JSON = BASE / "treffer_v1.json"
OUT_CSV = BASE / "treffer_v1.csv"

# JobSpy 'country_indeed' (steuert nur die Indeed-Domain). Profil ist DE-fixiert.
DEFAULT_COUNTRY_INDEED = "germany"
# Gültige JobSpy-site_names; quellen-Keys in der YAML müssen dazu passen.
GUELTIGE_QUELLEN = {"indeed", "google", "linkedin", "glassdoor", "zip_recruiter"}


# --------------------------------------------------------------------------- #
# ProfileAgent
# --------------------------------------------------------------------------- #
@dataclass
class Profil:
    name: str
    standort: str
    umkreis_km: int
    jobtitel: list[str]
    sprache: str
    remote: bool
    job_type: str | None
    hours_old: int | None
    results_wanted: int
    sites: list[str] = field(default_factory=list)


def lade_profil(pfad: Path = PROFIL_PFAD) -> Profil:
    """Liest jobprofil.yaml in ein Profil-Objekt (ohne Netz)."""
    if not pfad.exists():
        raise FileNotFoundError(
            f"{pfad} fehlt. Kopiere profile/jobprofil.example.yaml -> jobprofil.yaml und befülle es."
        )
    data = yaml.safe_load(pfad.read_text(encoding="utf-8")) or {}
    person = data.get("person", {}) or {}
    suche = data.get("suche", {}) or {}
    quellen = data.get("quellen", {}) or {}

    sites = [k for k, an in quellen.items() if an]
    unbekannt = [s for s in sites if s not in GUELTIGE_QUELLEN]
    if unbekannt:
        raise ValueError(f"Unbekannte Quelle(n) in jobprofil.yaml: {unbekannt} (erlaubt: {sorted(GUELTIGE_QUELLEN)})")

    jobtitel = [t for t in (suche.get("jobtitel") or []) if str(t).strip()]
    if not jobtitel:
        raise ValueError("jobprofil.yaml: suche.jobtitel ist leer — mindestens ein Suchbegriff nötig.")
    if not sites:
        raise ValueError("jobprofil.yaml: keine Quelle aktiviert (quellen.* alle false).")

    job_type = suche.get("job_type") or None  # "" -> None (= egal)

    return Profil(
        name=person.get("name", "?"),
        standort=person.get("standort", ""),
        umkreis_km=int(person.get("umkreis_km", 50)),
        jobtitel=jobtitel,
        sprache=suche.get("anzeigen_sprache", "de"),
        remote=bool(suche.get("remote")),  # null -> False
        job_type=job_type,
        hours_old=suche.get("hours_old"),
        results_wanted=int(suche.get("results_wanted", 15)),
        sites=sites,
    )


# --------------------------------------------------------------------------- #
# SearchAgent
# --------------------------------------------------------------------------- #
def suche_jobs(profil: Profil) -> pd.DataFrame:
    """Sucht pro Jobtitel über alle aktiven Quellen; sammelt Roh-Treffer.

    Ein Fehler bei einem Titel (z.B. LinkedIn-429) bricht den Lauf NICHT ab —
    er wird geloggt und übersprungen.
    """
    frames: list[pd.DataFrame] = []
    for titel in profil.jobtitel:
        google_term = f"{titel} Jobs in {profil.standort}".strip()
        try:
            df = scrape_jobs(
                site_name=profil.sites,
                search_term=titel,
                google_search_term=google_term,
                location=profil.standort,
                distance=profil.umkreis_km,
                is_remote=profil.remote,
                job_type=profil.job_type,
                results_wanted=profil.results_wanted,
                country_indeed=DEFAULT_COUNTRY_INDEED,
                hours_old=profil.hours_old,
                verbose=1,
            )
        except Exception as exc:  # eine Quelle/ein Titel down -> weiter
            print(f"  [WARN] Suche '{titel}' fehlgeschlagen: {type(exc).__name__}: {exc}", file=sys.stderr)
            continue
        if df is not None and not df.empty:
            df = df.copy()
            df["such_titel"] = titel
            frames.append(df)
            print(f"  [Suche] '{titel}': {len(df)} Roh-Treffer")
        else:
            print(f"  [Suche] '{titel}': 0 Treffer")

    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


# --------------------------------------------------------------------------- #
# ReportAgent (Minimal: dedup + JSON/CSV)
# --------------------------------------------------------------------------- #
def dedupliziere(df: pd.DataFrame) -> pd.DataFrame:
    """Entfernt Dubletten — primär per job_url, sonst (title, company, location)."""
    if df.empty:
        return df
    if "job_url" in df.columns and df["job_url"].notna().any():
        df = df.drop_duplicates(subset=["job_url"], keep="first")
    fallback = [c for c in ("title", "company", "location") if c in df.columns]
    if fallback:
        df = df.drop_duplicates(subset=fallback, keep="first")
    return df.reset_index(drop=True)


def schreibe_report(df: pd.DataFrame, profil: Profil) -> int:
    """Schreibt treffer_v1.json (+ .csv). Gibt die Treffer-Anzahl zurück."""
    df = dedupliziere(df)
    n = len(df)

    # to_json macht NaN->null, numpy-Typen + Datumswerte JSON-sicher.
    treffer = json.loads(df.to_json(orient="records", date_format="iso", force_ascii=False)) if n else []
    payload = {
        "meta": {
            "erzeugt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "profil": profil.name,
            "standort": profil.standort,
            "quellen": profil.sites,
            "such_titel": profil.jobtitel,
            "anzahl": n,
            "version": "v1",
        },
        "treffer": treffer,
    }
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    if n:
        df.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")
    return n


# --------------------------------------------------------------------------- #
# Entry
# --------------------------------------------------------------------------- #
def main() -> int:
    profil = lade_profil()
    print(f"[Profil] {profil.name} | {profil.standort} (±{profil.umkreis_km} km) | "
          f"{len(profil.jobtitel)} Titel | Quellen: {profil.sites}")
    df = suche_jobs(profil)
    n = schreibe_report(df, profil)
    print(f"[Report] {n} Treffer (dedupliziert) -> {OUT_JSON.name}" + (f" + {OUT_CSV.name}" if n else ""))
    if n == 0:
        print("[Hinweis] 0 Treffer — Quelle evtl. rate-limited oder Suchbegriff/Ort zu eng.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

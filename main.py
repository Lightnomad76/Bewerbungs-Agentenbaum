"""main.py — Jobsuche-Agent v2 (Daten-Engine + MatchAgent, read-only).

Pipeline: ProfileAgent -> SearchAgent -> ReportAgent -> MatchAgent.
Liest profile/jobprofil.yaml, sucht via JobSpy (Indeed/Google/...), dedupliziert,
scort die Treffer offline gegen profil_fuer_matching und legt sie priorisiert als
treffer_v2.json (Bridge zur späteren Web-UI) + treffer_v2.csv ab.

Start:  py -3.11 main.py
Scope:  NUR suchen + scoren + ablegen. Kein Login, kein Auto-Bewerben.
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

from match import MatchProfil, bewerte_treffer, zaehle_ausgeblendet, KERN_BERUF

BASE = Path(__file__).resolve().parent
PROFIL_PFAD = BASE / "profile" / "jobprofil.yaml"
OUT_JSON = BASE / "treffer_v2.json"
OUT_CSV = BASE / "treffer_v2.csv"
OUT_JS = BASE / "treffer_v2.js"  # JS-Bridge: erlaubt der lokalen UI file://-Doppelklick (kein fetch/CORS)

# JobSpy 'country_indeed' (steuert nur die Indeed-Domain). Profil ist DE-fixiert.
DEFAULT_COUNTRY_INDEED = "germany"
# Gültige JobSpy-site_names; quellen-Keys in der YAML müssen dazu passen.
GUELTIGE_QUELLEN = {"indeed", "google", "linkedin", "glassdoor", "zip_recruiter"}
# S1: stabiles Kernschema für die JSON-Bridge — unabhängig davon, welche Spalten
# eine Quelle/Treffermenge gerade liefert (UI-Vertrag).
KERN = ["title", "company", "location", "job_url", "date_posted",
        "min_amount", "max_amount", "description", "such_titel"]


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
    matching: MatchProfil | None = None  # ab v2: Scoring-Kriterien
    servicebund: dict | None = None  # v20: optionale service.bund-RSS-Quelle (öffentlicher Dienst)


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
    quellen_extra = data.get("quellen_extra", {}) or {}

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

    matching_roh = data.get("profil_fuer_matching", {}) or {}

    def _liste(key: str) -> list[str]:
        return [str(x).strip() for x in (matching_roh.get(key) or []) if str(x).strip()]

    matching = MatchProfil(
        skills_muss=_liste("skills_muss"),
        skills_kann=_liste("skills_kann"),
        ausschluss_keywords=_liste("ausschluss_keywords"),
        gehalt_min_eur_jahr=matching_roh.get("gehalt_min_eur_jahr"),
        standort=person.get("standort", ""),
        umkreis_km=int(person.get("umkreis_km", 50)),
        max_distanz_km=matching_roh.get("max_distanz_km"),
        kern_beruf=_liste("kern_beruf") or KERN_BERUF,
    )

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
        matching=matching,
        servicebund=(quellen_extra.get("servicebund") or None),
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
    roh = pd.concat(frames, ignore_index=True)

    # Pro-Quelle-Tally: macht sichtbar, welche Quelle wie viel beigetragen hat.
    # Google/ZipRecruiter liefern aktuell upstream 0 ("initial cursor not found",
    # JobSpy-Issue #302, offen/unfixbar von unserer Seite) — das soll nicht stumm
    # verpuffen, sonst wird es immer wieder neu debuggt.
    if "site" in roh.columns:
        pro_quelle = roh["site"].value_counts().to_dict()
        for s in profil.sites:
            print(f"  [Quelle] {s}: {int(pro_quelle.get(s, 0))} Roh-Treffer (vor Dedup)")
        if "google" in profil.sites and int(pro_quelle.get("google", 0)) == 0:
            print("  [Hinweis] google: 0 — bekannter JobSpy-Upstream-Bug (Issue #302, "
                  "'initial cursor not found'); NICHT die Query. Indeed bleibt verlässlich; "
                  "der Xing/Jobware-Umweg über Google greift erst wieder nach Upstream-Fix.",
                  file=sys.stderr)
    return roh


# --------------------------------------------------------------------------- #
# Zusatz-Quelle: service.bund.de (öffentlicher Dienst, RSS) — optional, gated
# --------------------------------------------------------------------------- #
def ergaenze_servicebund(df: pd.DataFrame, profil: Profil) -> pd.DataFrame:
    """Hängt service.bund-Treffer (öffentlicher Dienst) an die JobSpy-Roh-Treffer an.
    Aktiv NUR, wenn quellen_extra.servicebund.feed_url in der YAML steht — sonst No-Op
    (Pipeline unverändert). Schema-kompatibel (KERN), läuft danach durch dieselbe
    Dedup-/Scoring-/Report-Strecke. §3.6b: Detail-Fetch ist Crawl-delay-gedrosselt
    (in quelle_servicebund über Vorfilter + max_detail gedeckelt)."""
    cfg = profil.servicebund
    if not cfg or not cfg.get("feed_url"):
        return df
    try:
        import quelle_servicebund as qsb
        max_dist = profil.matching.max_distanz_km if profil.matching else None
        treffer = qsb.hole_stellen(
            cfg["feed_url"],
            standort=profil.standort,
            max_distanz_km=max_dist,
            titel_keywords=cfg.get("titel_keywords"),
            max_alter_tage=cfg.get("max_alter_tage", qsb.DEFAULT_MAX_ALTER_TAGE),
            detail_fetch=bool(cfg.get("detail_fetch", True)),
            max_detail=int(cfg.get("max_detail", qsb.DEFAULT_MAX_DETAIL)),
        )
    except Exception as exc:  # Quelle down/Feed-URL kaputt -> Indeed-Lauf NICHT verlieren
        print(f"  [WARN] service.bund-Quelle fehlgeschlagen: {type(exc).__name__}: {exc}",
              file=sys.stderr)
        return df
    print(f"  [Quelle] servicebund: {len(treffer)} Treffer (öffentlicher Dienst)")
    if not treffer:
        return df
    sb_df = pd.DataFrame(treffer)
    if df is None or df.empty:
        return sb_df
    return pd.concat([df, sb_df], ignore_index=True)


# --------------------------------------------------------------------------- #
# ReportAgent (Minimal: dedup + JSON/CSV)
# --------------------------------------------------------------------------- #
def _dedup_teil(teil: pd.DataFrame, subset: list[str]) -> pd.DataFrame:
    """Dedup auf subset (keep='first'); such_titel je Schlüssel zu sortierter Liste
    aggregiert (K2 — sonst geht bei keep='first' ein Such-Titel verloren).
    Daten sind klein (<~paar hundert Zeilen) -> Klarheit vor Mikro-Optimierung."""
    if "such_titel" not in teil.columns:
        return teil.drop_duplicates(subset=subset, keep="first").reset_index(drop=True)

    def schluessel(werte) -> tuple:
        # NaN-tolerant: NaN -> None, sonst matchen NaN-Schlüssel nie (NaN != NaN)
        return tuple(None if pd.isna(v) else v for v in werte)

    titel: dict[tuple, set] = {}
    for row in teil[subset + ["such_titel"]].itertuples(index=False, name=None):
        *key_vals, st = row
        if pd.notna(st):
            titel.setdefault(schluessel(key_vals), set()).add(str(st))

    dedup = teil.drop_duplicates(subset=subset, keep="first").reset_index(drop=True)
    dedup["such_titel"] = [
        sorted(titel.get(schluessel(k), set()))
        for k in dedup[subset].itertuples(index=False, name=None)
    ]
    return dedup


def dedupliziere(df: pd.DataFrame) -> pd.DataFrame:
    """Entfernt Dubletten. K1: URL-Zeilen NUR per job_url deduplizieren
    (verschiedene job_url = verschiedene Anzeigen, auch bei gleichem
    Titel/Firma/Ort). Zeilen OHNE job_url per (title, company, location).
    such_titel wird je Schlüssel gesammelt (K2)."""
    if df.empty:
        return df
    df = df.copy()
    teile: list[pd.DataFrame] = []

    hat_url = "job_url" in df.columns
    mit_url = df[df["job_url"].notna()] if hat_url else df.iloc[0:0]
    ohne_url = df[df["job_url"].isna()] if hat_url else df

    if not mit_url.empty:
        teile.append(_dedup_teil(mit_url, ["job_url"]))

    fallback = [c for c in ("title", "company", "location") if c in df.columns]
    if not ohne_url.empty:
        teile.append(_dedup_teil(ohne_url, fallback) if fallback else ohne_url)

    if not teile:
        return df.reset_index(drop=True)
    return pd.concat(teile, ignore_index=True)


def _schreibe_csv(treffer: list[dict]) -> None:
    """Review-CSV aus den gescorten Treffern (Score/ko vorn, schnell sichtbar)."""
    rows = []
    for t in treffer:
        m = t.get("match", {})
        st = t.get("such_titel")
        rows.append({
            "score": m.get("score"),
            "ko": m.get("ko"),
            "title": t.get("title"),
            "company": t.get("company"),
            "location": t.get("location"),
            "such_titel": ", ".join(st) if isinstance(st, list) else st,
            "muss_fehlt": ", ".join(m.get("muss_fehlt") or []),
            "kann_treffer": ", ".join(m.get("kann_treffer") or []),
            "ausschluss_treffer": ", ".join(m.get("ausschluss_treffer") or []),
            "date_posted": t.get("date_posted"),
            "job_url": t.get("job_url"),
        })
    pd.DataFrame(rows).to_csv(OUT_CSV, index=False, encoding="utf-8-sig")


def schreibe_report(df: pd.DataFrame, profil: Profil) -> int:
    """Dedupliziert, scort (MatchAgent) und schreibt treffer_v2.json (+ .csv).
    Gibt die Treffer-Anzahl zurück."""
    df = dedupliziere(df)
    n = len(df)

    if n:
        # S1: Kernschema erzwingen -> stabiles JSON unabhängig von Quell-Spalten.
        # to_json macht NaN->null, numpy-Typen + Datumswerte JSON-sicher.
        df_kern = df.reindex(columns=KERN)
        treffer = json.loads(df_kern.to_json(orient="records", date_format="iso", force_ascii=False))
    else:
        treffer = []

    # MatchAgent: offline scoren + priorisieren (Etappe 2) + Distanz-Filter (v13)
    ausgeblendet = 0
    max_dist = None
    if treffer and profil.matching is not None:
        max_dist = profil.matching.max_distanz_km
        if max_dist is not None:
            ausgeblendet = zaehle_ausgeblendet(treffer, profil.matching)
        treffer = bewerte_treffer(treffer, profil.matching)
    n = len(treffer)
    if ausgeblendet:
        print(f"  [Distanz] {ausgeblendet} Treffer > {max_dist} km ausgeblendet "
              f"(harte Obergrenze ab Standort)")

    payload = {
        "meta": {
            "erzeugt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "profil": profil.name,
            "standort": profil.standort,
            "quellen": profil.sites,
            "such_titel": profil.jobtitel,
            "anzahl": n,
            "max_distanz_km": max_dist,
            "ausgeblendet_zu_weit": ausgeblendet,
            "version": "v2",
        },
        "treffer": treffer,
    }
    payload_json = json.dumps(payload, ensure_ascii=False, indent=2)
    OUT_JSON.write_text(payload_json, encoding="utf-8")
    # JS-Bridge für die lokale UI (file:// blockt fetch() -> per <script> einbinden,
    # liest window.TREFFER). Immer geschrieben, auch bei 0 Treffern.
    OUT_JS.write_text(f"window.TREFFER = {payload_json};\n", encoding="utf-8")
    if treffer:
        _schreibe_csv(treffer)
    return n


# --------------------------------------------------------------------------- #
# Entry
# --------------------------------------------------------------------------- #
def main() -> int:
    profil = lade_profil()
    print(f"[Profil] {profil.name} | {profil.standort} (±{profil.umkreis_km} km) | "
          f"{len(profil.jobtitel)} Titel | Quellen: {profil.sites}")
    df = suche_jobs(profil)
    df = ergaenze_servicebund(df, profil)
    n = schreibe_report(df, profil)
    print(f"[Report] {n} Treffer (dedupliziert, gescort) -> {OUT_JSON.name}" + (f" + {OUT_CSV.name}" if n else ""))
    if n == 0:
        print("[Hinweis] 0 Treffer — Quelle evtl. rate-limited oder Suchbegriff/Ort zu eng.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

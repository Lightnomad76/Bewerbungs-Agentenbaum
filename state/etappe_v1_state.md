# Etappe v1 — State nach Abschluss

**Datum:** 2026-06-23
**ZIP:** Bewerbungs-Agentenbaum_v1_stable.zip (Daten-Engine, live-verifiziert)
**Status:** ⚠️ stable mit Known Issues

---

## Was wurde gemacht

- `main.py` gebaut — Drei-Agenten-Kette:
  - ProfileAgent (`lade_profil`): liest `profile/jobprofil.yaml`
  - SearchAgent (`suche_jobs`): pro Jobtitel über alle aktiven Quellen, fehlertolerant — ein 429/Fehler pro Titel killt den Lauf nicht
  - ReportAgent: `dedupliziere` (per job_url + Fallback (title, company, location)); `schreibe_report` → `treffer_v1.json` mit Schema {meta, treffer} als UI-Bridge + `treffer_v1.csv`
- `verify_engine.py`: offline Mechanik-Selbsttest (kein Netz) — Profil-Parsing, Dedup, JSON/CSV-Schema, NaN/NaT-JSON-Sicherheit, Leer-Fall. 15/15 Checks grün (exit 0)
- Start: `py -3.11 main.py` · Verify: `py -3.11 verify_engine.py`

## Was wurde verworfen (und warum)

- Python 3.14 für dieses Projekt verworfen: 3.14 erzwingt numpy==1.26.3 Source-Build → kein MSVC → Abbruch. Empirisch via dry-run bestätigt, deckt sich mit lib-version-checker + CLAUDE.md-Fallback. → Interpreter fix `py -3.11`, JobSpy v1.1.82 auf 3.11 installiert. Nicht erneut auf 3.14 versuchen.
- Google als verlässliche Quelle (vorerst): liefert aktuell 0 Treffer ("initial cursor not found"). Der Xing/Jobware-via-Google-Umweg greift faktisch (noch) nicht — Indeed trägt allein.

## Known Issues (verbleibend in v1)

- **Global-pip-Nebenwirkung (VERTAGT, User-Entscheid):** JobSpy-Install hat global numpy 2.4.6→1.26.3 + regex 2026.1.15→2024.11.6 heruntergestuft → crewai broken (requires regex~=2026.1.15). Bewusst NICHT gefixt in v1, später adressieren (z.B. venv-Isolation erwägen).
- Google-Quelle liefert 0 Treffer ("initial cursor not found") → Xing/Jobware-Umweg inaktiv; aktuell Indeed-only de facto.

## Offene Punkte

- Google-Query nachjustieren (`google_search_term`) ODER bewusst auf Indeed-only setzen — Entscheidung offen.
- Global-pip-Nebenwirkung (siehe Known Issues) auflösen — vertagt.

## Test-Status

- Empirisch (live, Netz): 1 Indeed-Call gemessen = 0.3s; voller Lauf (6 Titel × Indeed+Google) = 2.7s → 36 deduplizierte reale DE-Treffer (DE-Zielregion). ZIP-GO-Kriterium (≥1 realer Treffer aus ≥1 Quelle) erfüllt.
- Empirisch (offline): `verify_engine.py` 15/15 grün, exit 0.
- Nicht getestet / unbestätigt: Google-Quelle liefert real 0 Treffer (Defekt, kein Erfolg); LinkedIn-Pfad in diesem Lauf nicht durchlaufen; Verhalten bei echtem 429 nur durchdacht (Fehlertoleranz strukturell drin, nicht live provoziert).

## Nächste sinnvolle Etappe (Vorschlag)

v2 = MatchAgent (Marek): Keyword-Scoring offline gegen `profil_fuer_matching` (skills_muss = K.o., skills_kann = Bonus, ausschluss_keywords abwerten), deterministisch. `brief-writer` für den v2-Brief. Optional vorgezogen, falls Indeed-only-Treffer-Qualität es erfordert: Google-Query-Entscheidung.

## Verweis-Quellen

- Release-Notes: (noch keine erstellt)
- Vorgänger-State: keiner (Etappe 1 = erste Etappe)
- Vorgänger-Brief: briefs/etappe_v1_brief.md
- Relevante User-Messages: 2026-06-23 (ZIP-/Live-Verifikations-Bestätigung, global-pip-Vertagungs-Entscheid)

## Etappen-Brief: v1 — Gerüst + Suche (Roh-Treffer)

**Ziel der Etappe (1 Zeile):**
Lauffähiges Python-Gerüst, das mit JobSpy LinkedIn/Indeed/Google nach dem Jobprofil
durchsucht und Roh-Treffer als CSV ablegt.

**Kontext (max 3 Bullets):**
- Pre-Code-Projekt; Konzeption + Tool-Wahl stehen [aus state/konzept_state.md].
- Host: Win11, Python 3.14.4 + 3.11.9 parallel, `py -m pip` global, kein venv [globale CLAUDE.md §6].
- Read-only Scope ist gesetzt; kein Login, kein Auto-Bewerben [HANDOFF.md].

**Aufgaben (max 5 Bullets):**
- JobSpy installieren — **vorher** cp314-Wheel-Status via lib-version-checker prüfen; bei
  Bruch auf `py -3.11` ausweichen (JobSpy verlangt python ^3.10).
- ProfileAgent: liest `jobprofil.yaml` (Titel/Skills/Ort/Remote/Gehalt/Sprache).
- SearchAgent: ruft `scrape_jobs(site_name=[...], search_term=..., location=..., results_wanted=..., hours_old=...)`.
- ReportAgent (Minimal): dedupliziert, schreibt `treffer_v1.csv`.
- CLI-Entry: `py main.py` startet einen Durchlauf mit dem Profil.

**Out of Scope (mindestens 1 Bullet):**
- Kein Matching/Scoring (das ist Etappe 2), keine Anschreiben, keine Web-UI, kein Xing/Jobware-Native.

**Erfolgs-Kriterium für ZIP-GO:**
`py main.py` liefert auf Win11 eine `treffer_v1.csv` mit ≥1 realen Treffer aus mind. einer Quelle.

**Bekannte Risiken (max 2):**
- JobSpy-cp314-Wheel evtl. nicht vorhanden → Fallback `py -3.11`.
- LinkedIn rate-limit / 429 → Indeed+Google als verlässlichere Default-Quellen, LinkedIn optional.

**Offene Frage an den Senior (NICHT selbst entscheiden):**
- Matching-Verfahren (Keyword vs. semantisch) — erst in Etappe 2 relevant, hier nur Roh-Daten.
- Interface (CLI vs. Web-UI) — Etappe 1 bleibt CLI, Entscheidung betrifft spätere Etappen.

**Quellen:**
- state/konzept_state.md, HANDOFF.md
- JobSpy README (speedyapply/JobSpy), Recherche 2026-06-22
- profile/jobprofil.example.yaml

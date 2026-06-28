# CLAUDE.md — Jobsuche-Agent (Bewerbungshilfe)

**Stack:** Python 3.11 in **projekt-eigenem venv** `.venv` (PyYAML + `python-jobspy` darin isoliert) · **AUSNAHME zur globalen „kein venv"-Regel** (Etappe v6, 2026-06-28): JobSpys regex-Constraint `<2025.0.0` ist **disjunkt** zu crewais `~=2026.1.15` im global-py311-AI-Stack → ein gemeinsamer Topf ist mathematisch unmöglich. Darum JobSpy isoliert ins venv, global bleibt crewai/LangChain-autoritativ. Detail: `state/etappe_v6_state.md`.
**BASE_DIR:** C:\Users\adam2\.Projekte\Bewerbungs-Agentenbaum
**Start-Befehl:** `.\.venv\Scripts\python.exe main.py` (venv-Python — NICHT `py -3.11`, global hat kein jobspy mehr)
**Verify-Befehl:** `.\.venv\Scripts\python.exe verify_*.py` (Mechanik-Selbsttest, exit 0 = grün). Ausnahme: `profile/`-Generatoren (gen_cv/gen_bewerbung, kein jobspy) laufen weiter über global `py -3.11`.
**Versionsschema:** v_N; Git = datierte Kette + Rollback; ZIP-Snapshot nur bei `_stable` via `make_backup.py`; `_stable`-ZIPs + Git-History nie löschen
**Projekt-Subagent-Overrides:**
- Code-Etappen (Engine/Scoring) = **Marek** (Default).
- Scraping/Rate-Limit/Legal-Grauzone = **Wolf** konsultativ (Etappe 1) bzw. führend (nativer Scraper, optionale Etappe 4).
- Lokale HTML-Web-UI = **edyta** (eigene GUI-Etappe 3).
- JobSpy-/Lib-Kompatibilität = `lib-version-checker` (erster Schritt Etappe 1).

**Besonderheiten (projekt-spezifisch, NICHT in globaler §6):**
- **Read-only Scope, hart:** nur Suchen + Scoren + Vorschlagen. KEIN Login, KEIN Auto-Bewerben, KEIN Profil-Steuern (AGB-Verstoß + Account-Sperrgefahr LinkedIn/Xing/Jobware). Tool bleibt login-frei.
- **Matching = Keyword-Scoring offline/gratis** (deterministisch). Semantik/Anthropic-API nur später optional.
- **Xing/Jobware = Google-Jobs-Umweg** (gratis). Nativer Scraper nur optionale Spät-Etappe.
- **Interface = lokale HTML-Web-UI, projektordner-bezogen** → Engine-Output als **JSON** (Bridge zur UI), nicht nur CSV.
- **`jobprofil.yaml` ist persönliche Nutzerdaten → gitignored** (nur `jobprofil.example.yaml` ist eingecheckt).
- **JobSpy LinkedIn stark rate-limited** (429 ab ~Seite 10) → Indeed+Google als verlässliche Default-Quellen.

(Globale Workflow-Regeln §3, Subagent-Tabelle §1, Vertical-Agents §2, Dev-Host §6 gelten
automatisch — hier NICHT wiederholt. Plan + offene Punkte: `HANDOFF.md`.)

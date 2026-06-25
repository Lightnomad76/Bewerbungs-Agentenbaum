# HANDOFF — Jobsuche-Agent (Bewerbungshilfe)

**Erstellt:** 2026-06-22 · **Aktualisiert:** 2026-06-25 (Quellen-/Dependency-Snapshot + Upgrade-Suche)
**Phase:** **Etappe 1 (Daten-Engine) ABGESCHLOSSEN** — Detail: `state/etappe_v1_state.md`. Nächstes = Etappe 2 (MatchAgent).
**Ziel-Session:** Claude Code CLI (Senior Dev / Marek)
**Sprache:** Deutsch, technische Begriffe Englisch lassen

!ETAPPE-GATE: etappe-1=eigene-frische-session(NICHT an Planung hängen); lib-version-checker=erster-schritt-etappe-1(JobSpy cp314); live-jobspy-run=netz-posten(wall-clock+erfolgsrate ERST beim echten run messbar, eigener schritt); web-ui=eigene-gui-etappe(edyta, nach etappe1+2); agenten-roadmap=EIGENE-NEUE-SESSION-MIT-MAREK(User-Entscheid 2026-06-24, NICHT anhängen; Grundlage state/agenten_roadmap.md: Critic/FactGrounding/JDParser + ATS-Zwei-Pfad)

---

## Was ist das

Ein **read-only Job-Such- & Matching-Agent**: durchsucht Jobbörsen, scored die Treffer
gegen das Jobprofil des Users und liefert priorisierte Vorschläge. **Kein** Auto-Bewerben,
**kein** Profil-Steuern (siehe Caveats).

## Sofort-Einstieg für die CLI-Session (Stand 2026-06-23 — STARTKLAR)

Alle Blocker vor Etappe 1 sind gelöst: 5 Fragen geklärt, `profile/jobprofil.yaml` befüllt,
Repo gebootstrappt (git + CLAUDE.md + .gitignore).
1. Dieses HANDOFF + `briefs/etappe_v1_brief.md` lesen (Brief sagt noch „CSV" → gilt jetzt **JSON**).
2. Direkt **Etappe 1 bauen** nach „Ausgearbeiteter Etappen-Plan" unten — reihenfolgetreu (§3.11).
3. Selbstcheck → auf „ZIP" warten → `etappe-tracker`.

## Entschieden (mit Quelle — nicht neu aufrollen)

- **Primär-Tool: `speedyapply/JobSpy`** (Python, PyPI `python-jobspy` v1.1.82, aktiv 2026).
  Deckt LinkedIn, Indeed, Glassdoor, Google Jobs, ZipRecruiter ab. [Recherche 2026-06-22]
- **Implementierungssprache: Python** (folgt zwingend aus JobSpy). [JobSpy = Python]
- **Architektur:** ProfileAgent / SearchAgents / MatchAgent / ReportAgent. [Konzept-Chat]
- **Xing/Jobware-Default: Google-Jobs-Umweg** — Google indexiert viele dieser Anzeigen,
  kostenlos über JobSpy mitgreifbar. (Native Anbindung = Etappe 3, optional.) [Recherche]

## Verworfen (NICHT erneut versuchen)

- **Profile „steuern" / Auto-Bewerben / Auto-Posting** — AGB-Verstoß bei LinkedIn/Xing/Jobware,
  reale Account-Sperrgefahr. Bewusst raus. [User-Bestätigung ausstehend, Frage 1]
- **Natives Xing-API** — öffentliches XING-API ist eingestellt (New Work SE). Nur noch
  bezahlte Drittanbieter-Scraper oder riskantes Login-Scraping. [Recherche 2026-06-22]

## GEKLÄRT — Entscheidungen 2026-06-23 (nicht neu aufrollen)

1. **Scope:** ✅ **read-only** — nur Suchen + Scoren + Vorschlagen. Kein Login/Auto-Bewerben.
2. **Matching:** ✅ **Keyword-Scoring offline/gratis** (deterministisch, keine API-Kosten). Semantik/Anthropic-API später optional aufrüstbar.
3. **Xing/Jobware:** ✅ **Google-Jobs-Umweg** reicht (gratis, fängt viele mit). Nativer Scraper nur als optionale Spät-Etappe.
4. **Profil:** ✅ **`profile/jobprofil.yaml` befüllt** (Industriemechaniker + Qualitätssicherung, Standort/Umkreis gesetzt; der Beispiel-YAML-Default galt nicht). Jobtitel + skills_muss/kann gesetzt. Gitignored (persönliche Daten). Feinjustierbar.
5. **Interface:** ✅ **Lokale HTML-Web-UI, projektordner-bezogen** (statisches HTML/JS, lädt Treffer aus dem Projektordner). → Etappe 1/2 liefern Output als **JSON** (Bridge zur UI); UI selbst = eigene GUI-Etappe (edyta).

## Ausgearbeiteter Etappen-Plan (je eigene frische Session)

- **Etappe 1 — Daten-Engine (Marek): ✅ ERLEDIGT 2026-06-23.** `main.py` + `verify_engine.py` gebaut, `py -3.11` fixiert (3.14 = numpy-Source-Build-Bruch), JobSpy v1.1.82 installiert. Live-Run: 2.7s, 36 reale DE-Treffer (alle Indeed; Google liefert 0). Output `treffer_v1.json`+`.csv`. Detail: `state/etappe_v1_state.md`.
  - ⚠️ **VERTAGT (User):** global-pip-Nebenwirkung — JobSpy-Install stufte global numpy 2.4.6→1.26.3 + regex 2026.1.15→2024.11.6 herunter → **crewai broken** (`requires regex~=2026.1.15`). Bewusst offen, später adressieren (crewai eigenes venv o.ä.).
  - Offen: Google-Query nachjustieren oder Indeed-only; `_stable`-ZIP via `make_backup.py` vor v2 noch nicht erzeugt.
- **Etappe 2 — MatchAgent (Marek):** Keyword-Scoring offline gegen `profil_fuer_matching` (skills_muss = K.o., skills_kann = Bonus, ausschluss_keywords abwerten, gehalt). Priorisierte/gescorte JSON-Liste. `brief-writer` für v2-Brief.
  - **⚠️ ZUERST: Marek-Review-Fixes aus Etappe 1 anwenden** (Review 2026-06-23, Engine-Bugs die Etappe 2 beißen):
    - **K1 (kritisch, Datenverlust):** `main.py:137-142` `dedupliziere` — die `(title,company,location)`-Fallback-Stufe läuft auf dem GANZEN Frame und löscht echte verschiedene Anzeigen derselben Firma/Titel (verschiedene `job_url`). Fix: Fallback nur auf Zeilen **ohne** `job_url` (`df["job_url"].isna()`), URL-Zeilen unangetastet. (Der state-File-Text „Dedup per job_url + Fallback" ist als Feature beschrieben, ist aber dieser Bug.)
    - **K2 (kritisch):** `such_titel` geht beim Dedup verloren (`keep="first"` willkürlich). Fix: vor Dedup `such_titel` pro Schlüssel zu Set aggregieren — relevant fürs Scoring.
    - **S1 (Schema-Vertrag):** `main.py:151` `to_json` serialisiert nur vorhandene Spalten → JSON-Schema schwankt je Quelle/Treffermenge. Fix: Kernschema per `df.reindex(columns=KERN)` erzwingen (title,company,location,job_url,date_posted,min/max_amount,description,such_titel) — macht UI-Bridge vertragsfest.
    - **S2 (sicherer Win):** `main.py:114-116` `try/except Exception` umschließt auch die DataFrame-Nachbearbeitung → verschluckt echte Bugs als stille 0-Treffer. Fix: `try` nur um den `scrape_jobs()`-Call ziehen.
    - **N1/N2:** `verify_engine.py` um Tests für K1 (gleicher Titel/Firma/Ort, andere URL → muss 2 bleiben) + K2 + Schema-Stabilität erweitern.
    - **S3 (nur Einschätzung):** Google-0 ist mutmaßlich JobSpy-seitig (Cursor-Token), nicht unser `google_search_term` — vor eigenem Debugging via `lib-version-checker` gegen offene Issues checken, kein Query-Tweak.
- **Etappe 3 — Lokale HTML-Web-UI (edyta):** statisches HTML/JS im Projektordner, lädt die gescorte JSON, zeigt sortiert/filterbar. `brief-writer` für v3-Brief.
- **Etappe 4 (optional) — natives Xing/Jobware-Scraping (Wolf):** nur falls Google-Umweg-Abdeckung später unzureichend.

## Harte Caveats (Konfidenz-ehrlich)

- **Legal:** read-only Scraping bewegt sich in einer AGB-Grauzone; einloggen/automatisieren
  von Konten ist die rote Linie. Tool bleibt deshalb login-frei.
- **JobSpy LinkedIn:** stark rate-limited (Block oft ab ~Seite 10), Proxies empfohlen.
  Indeed/Google am stabilsten. Tatsächliche Erfolgsrate **erst beim ersten echten Run messbar**.
- **Host-Constraints** (aus globaler CLAUDE.md): Win11, Python 3.14.4 primär + 3.11.9 parallel,
  `py -m pip` global, kein venv. JobSpy braucht `python = "^3.10"` → mit 3.14 wheel-Status
  vor Einbau via lib-version-checker prüfen.

## Quellen-/Dependency-Stand (2026-06-25)

- **Snapshot + Upgrade-Befunde:** `state/quellen_stand_2026-06-25.md` (Ist-Stand als Rollback-Basis).
- **JobSpy 1.1.82 = installiert = neuester PyPI-Release** — kein pip-Upgrade. GitHub-`main` ist neuer
  (LinkedIn-Datums-Fix, numpy-Constraint gelockert) → nur via Git-Install ziehen, falls real gebraucht.
- **Major-Updates (pandas 3 / numpy 2 / markdownify 1) NICHT blind** — global pip ohne venv, Bruch träfe
  auch crewai. Vor jedem Major erst `lib-version-checker` gegen JobSpy-Kompat. Bewusst NICHTS upgegradet.
- **Push offen:** Repo hat kein Git-Remote (lokale Kette). GitHub-Repo noch nicht angelegt (User pausiert).

## Offene Punkte (nicht blockierend für Etappe 1)

- **Persönliche Bewerbungs-Artefakte (Firmenhistorie, Lebenslauf-/Anschreiben-Tailoring, konkrete
  Stellen-Bewerbungen):** liegen bewusst **außerhalb dieses Repos** (gitignored bzw. nur lokal) —
  personenbezogene Daten gehören nicht in ein öffentliches Repo. Details/Stand dazu nur lokal.

# HANDOFF — Jobsuche-Agent (Bewerbungshilfe)

**Erstellt:** 2026-06-22 · **Aktualisiert:** 2026-06-25 (Etappe 2 abgeschlossen + committed + _stable-ZIP; Ausschluss-Fix nachgezogen; geschärft für Etappe 3 Web-UI)
**Phase:** **Etappe 2 (MatchAgent) ABGESCHLOSSEN** — Detail: `state/etappe_v2_state.md`. **Nächstes = Etappe 3 (lokale HTML-Web-UI, edyta) in FRISCHEM Chat.**
**Ziel-Session:** Claude Code CLI (Etappe 3 = edyta / GUI-Hut)
**Sprache:** Deutsch, technische Begriffe Englisch lassen
**Repo:** öffentlich auf github.com/Lightnomad76/Bewerbungs-Agentenbaum — **PII-Dateien NIE pushen** (jobprofil.yaml, firmenhistorie_enriched.md, etappe_bewerbung_guetepruefer_state.md, treffer_v*.json/.csv mit echten Treffern, Lebensläufe/Anschreiben; alle gitignored). Memory: `github-repo-public`.

!ETAPPE-GATE: etappe-1=ABGESCHLOSSEN; etappe-2=ABGESCHLOSSEN+COMMITTED(MatchAgent match.py + Fixes K1/K2/S1 + verify_match.py; live 35 Treffer/2.78s; skills_muss bewusst leer; Ausschluss nur im Titel = AUSSCHLUSS_FELDER, False-Positives behoben; commits da545d5+5e53391; _stable-ZIP v2 gezogen — siehe state); etappe-3=EIGENE-FRISCHE-SESSION-MIT-EDYTA(lokale HTML-Web-UI, lädt treffer_v2.json, sortiert/filterbar; brief-writer für v3-Brief); live-jobspy-run=netz-posten(billig ~2.8s, kein laufzeit-gate); agenten-roadmap=EIGENE-NEUE-SESSION-MIT-MAREK(User-Entscheid 2026-06-24, NICHT anhängen; Grundlage state/agenten_roadmap.md: Critic/FactGrounding/JDParser + ATS-Zwei-Pfad); public-repo=KEIN-PII-pushen

---

## Was ist das

Ein **read-only Job-Such- & Matching-Agent**: durchsucht Jobbörsen, scored die Treffer
gegen das Jobprofil des Users und liefert priorisierte Vorschläge. **Kein** Auto-Bewerben,
**kein** Profil-Steuern (siehe Caveats).

## Sofort-Einstieg Etappe 3 — lokale HTML-Web-UI (frischer Chat, mit edyta)

Etappe 2 läuft (35 reale Treffer, gescort; `verify_engine.py` + `verify_match.py` grün). Reihenfolge:
0. **ZUERST lesen:** `briefs/etappe_v3_brief.md` — vollständiger v3-Kontext-Brief (UI-Vertrag, Erkenntnisse, file://-Constraint, Dev-Host-UI, Workflow). Ersetzt die Chat-Historie.
1. **Lesen:** dieses HANDOFF + `state/etappe_v2_state.md` (Ist-Stand Engine+MatchAgent).
2. **Environment-Smoke (§3.11):** `py -3.11 verify_engine.py` UND `py -3.11 verify_match.py` müssen exit 0 sein.
3. **UI bauen (edyta / GUI-Hut):** statisches HTML/JS im Projektordner, lädt `treffer_v2.json` (Schema: `{meta, treffer[]}`; jeder Treffer hat `match.{score,ko,muss_treffer,muss_fehlt,kann_treffer,ausschluss_treffer,gehalt_unter_min}` + Kernfelder title/company/location/job_url/date_posted/min_amount/max_amount/description/such_titel[Liste]). Sortierbar nach Score, filterbar (z.B. Ausschluss ein/aus, Min-Score), Skill-Treffer sichtbar.
4. **Wichtig fürs lokale Laden:** Browser blockt `fetch()` von `file://` (CORS) → UI muss entweder das JSON inline/per `<script>`-Bridge laden ODER mit `py -3.11 -m http.server` im Projektordner serviert werden. edyta entscheidet den Weg.
5. Selbstcheck (§3.5) → auf „ZIP"/„go" warten → `state/etappe_v3_state.md`.
- **v3-Brief liegt vor:** `briefs/etappe_v3_brief.md` (kein brief-writer-Spawn mehr nötig).
- **Achtung public Repo:** `treffer_v2.json/.csv` (+ etwaige `treffer_v2.js`-Bridge) enthalten echte Treffer → vor `git push` prüfen, dass weder die noch andere PII getrackt werden (gitignored halten).

## Etappe 2 — Abschluss-Stand (erledigt)
- **Committed:** `da545d5` (MatchAgent + Fixes K1/K2/S1), `5e53391` (Ausschluss nur im Titel, False-Positives behoben). `_stable`-ZIP `Bewerbungs-Agentenbaum_v2_stable.zip` gezogen (lokal, gitignored).
- **Live-Stand:** 35 reale Treffer, sinnvolles Ranking (score 30..0), 0 False-Positive-Ausschlüsse. `treffer_v2.json/.csv` lokal vorhanden (gitignored).

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
- **Etappe 2 — MatchAgent (Marek): ✅ ERLEDIGT 2026-06-25.** `match.py` (offline Keyword-Scoring), Fixes K1/K2/S1 angewandt (S2 war bereits korrekt), `verify_engine.py` erweitert + `verify_match.py` neu (34 Checks grün). Live: 2.78s, 35 Treffer, sinnvolles Ranking. `skills_muss` bewusst **leer** gesetzt (Zwei-Berufsrichtungen-Profil hat keinen sinnvollen UND-K.o.-Term; Berufs-Keywords als Bonus). Output `treffer_v2.json/.csv`. Detail: `state/etappe_v2_state.md`.
  - **Restpunkte (nicht blockierend):** Ausschluss `"Ausbildung"` zu breit (matcht „abgeschlossene Ausbildung"); Google weiter 0 (S3 — JobSpy-seitig, vor Debugging via `lib-version-checker` offene Issues checken); `_stable`-ZIP + Commit ausstehend (auf User-go).
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

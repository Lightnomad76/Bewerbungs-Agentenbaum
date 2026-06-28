# HANDOFF — Jobsuche-Agent (Bewerbungshilfe)

**Erstellt:** 2026-06-22 · **Aktualisiert:** 2026-06-28 (Etappe v8 = Roadmap E-C **CVTailoring-Kern** TailoringAgent/GapAnalysis ABGESCHLOSSEN: `tailoring.py` + `verify_tailoring.py`, Marek, deterministisch/offline, 30/30 grün; danach Teil 3 = ATS-Linter geplant)
**Phase:** **Etappe v8 (E-C TailoringAgent/GapAnalysis, Marek) ABGESCHLOSSEN+COMMITTED** — Anzeige↔CV Keyword-Abgleich (Entscheidungs-Kern von CVTailoring, ohne Text-Gen); 80k-Schnitt (User 2026-06-28). **Nächstes: E-C Teil 3 (ATS-Linter `ats_lint.py`)**, danach Text-Writer (volles ~150k-Paket).
**Ziel-Session:** Claude Code CLI (nächste Etappe = E-C Teil 3 ATS-Linter / Marek; Text-Writer eigene Session)
**⚠️ RUN-BEFEHL GEÄNDERT (ab v6):** Engine/Verify laufen über `.\.venv\Scripts\python.exe <datei>.py` — **NICHT** mehr `py -3.11` (global hat kein jobspy mehr → ModuleNotFoundError). `profile/`-Generatoren bleiben global `py -3.11`.
**Sprache:** Deutsch, technische Begriffe Englisch lassen
**Repo:** öffentlich auf github.com/Lightnomad76/Bewerbungs-Agentenbaum — **PII-Dateien NIE pushen** (jobprofil.yaml, firmenhistorie_enriched.md, etappe_bewerbung_guetepruefer_state.md, treffer_v*.json/.csv mit echten Treffern, Lebensläufe/Anschreiben; alle gitignored). Memory: `github-repo-public`.

!ETAPPE-GATE: etappe-1=ABGESCHLOSSEN; etappe-2=ABGESCHLOSSEN+COMMITTED(MatchAgent match.py + Fixes K1/K2/S1 + verify_match.py; live 35 Treffer/2.78s; skills_muss bewusst leer; Ausschluss nur im Titel = AUSSCHLUSS_FELDER, False-Positives behoben; commits da545d5+5e53391; _stable-ZIP v2 gezogen — siehe state); etappe-3=ABGESCHLOSSEN+COMMITTED(lokale HTML-Web-UI ui/index.html+app.js+style.css, edyta; JS-Bridge ../treffer_v2.example.js Default, Doppelklick/file:// kein Server; sortier-/filterbar, kann_treffer-Chips, ko-/Ausschluss-/Gehalt-Badges, null→k.A.; headless 16/16 + live in Chrome abgenommen 2026-06-27; nur ui/ committed, Bridge/Treffer gitignored — siehe state/etappe_v3_state.md); live-jobspy-run=netz-posten(billig ~2.8s, kein laufzeit-gate); etappe-4=ABGESCHLOSSEN+COMMITTED(Roadmap E-A CriticAgent critic.py + verify_critic.py, Marek; deterministisch/offline/keine-API, flaggt-ändert-nichts; API pruefe()/hat_fehler() = Pipeline-Gate, CLI exit 1=FEHLER/0=sauber, --json; Floskel-Blacklist+Pflichtfelder=FEHLER, Adjektiv/Länge/7-Sek/Betreff=WARNUNG; verify 24/24 grün; live gegen echten Brief 346W 0F/0W = kein False-Positive; beide Dateien=Code/kein-PII committed; echter Brief nur gelesen — siehe state/etappe_v4_state.md); critic-eingehängt=JA(2026-06-27, in profile/gen_bewerbung_guetepruefer.py = LOKAL/gitignored/PII; build_anschreiben()->（pfad,text), pruefe()+report() nach Build, read-only flaggt-nur; critic.py _report->report committed; verify 24/24); etappe-5=ABGESCHLOSSEN+COMMITTED(Roadmap E-B FactGroundingAgent factground.py + verify_factground.py, Marek; deterministisch/offline/keine-API, flaggt-ändert-nichts; SCOPE-KORREKTUR: Wahrheitsquelle NICHT jobprofil.yaml=Suchprofil-ohne-CV-Fakten sondern CV-STAMMDATEN-REINGEFÜTTERT via sammle_fakten(*quellen); API pruefe(text,fakten)+hat_fehler()=Gate, CLI factground.py <text> <wahrheit...> exit1=FEHLER --json; Known-Facts-Whitelist: Firma-mit-Rechtsform-nicht-in-Historie+Erfahrungsdauer-N-Jahre-nicht-gedeckt=FEHLER, Akronym/Jahr-nicht-belegt=WARNUNG; verify 31/31 grün; live echter Brief 0F/0W kein-FP + Negativ-Kontrolle Thyssenkrupp/40Jahre/WIG geflaggt; beide Dateien Code/kein-PII committed — siehe state/etappe_v5_state.md); factground-eingehängt=JA(2026-06-27, in gen_bewerbung_guetepruefer.py LOKAL/gitignored/PII; fakten aus EXPERIENCE/ALPHA/WEITERE/SAMSON/COPERION/KURZPROFIL+STAMMDATEN_EXTRA+CV_DATE_LINE; nach build_anschreiben() neben critic; read-only flaggt-nur; end-to-end 0/0); crewai-fix=ABGESCHLOSSEN+COMMITTED(v6 2026-06-28 Wolf; Befund: crewai NICHT laufzeit-broken nur pip-check-Warnung, Constraints DISJUNKT jobspy-regex<2025-vs-crewai>=2026 → Reconcile mathematisch unmöglich; Lösung=JobSpy-in-projekt-.venv-isoliert NICHT-crewai-anfassen=Opfer-nicht-Verursacher; global geheilt: jobspy-uninstall+regex==2026.1.15→pip-check-sauber+crewai/crewai-tools-importieren; venv 4/4-Verifies-grün; numpy-bewusst-1.26.3-gelassen; RUN-BEFEHL-jetzt-.venv\Scripts\python.exe NICHT-py-3.11; neue-Regel=global-nie-für-Projekt-Konflikt-opfern; Detail state/etappe_v6_state.md); etappe-7=ABGESCHLOSSEN+COMMITTED(Roadmap E-C Teil 1 JDParserAgent jdparser.py + verify_jdparser.py, Marek; deterministisch/offline/keine-API, extrahiert-ändert-nichts; E-C-Schnitt User 2026-06-28 = nur JDParser=Fundament; API parse(text)->{keywords,anforderungen,abschnitte,meta,stats} + keywords_flach()=ATS-Liste + report(); CLI .venv\Scripts\python.exe jdparser.py <datei> --json exit0 (kein-jobspy→auch global py-3.11); kuratiertes KEYWORD_KATALOG fertigung/mess_qs/steuerung_it/normen/soft/sprachen Industriemechaniker+QS erweiterbar; Muss/Kann via zeilen-Trigger zwingend→muss von-Vorteil→kann muss-Vorrang; Abschnitts-Segmentierung Aufgaben/Profil/Angebot; Meta titel/ansprechpartner(→Critic-Anrede)/abschluss/schicht/reise; Umlaut-Folding ä↔ae auf Text+Muster; verify 38/38 grün + Live-CLI-Smoke; beide Dateien Code/kein-PII committed; NICHT in PII-Generator eingehängt=separater-Schritt; Detail state/etappe_v7_state.md); etappe-8=ABGESCHLOSSEN+COMMITTED(Roadmap E-C CVTailoring-Kern TailoringAgent/GapAnalysis tailoring.py + verify_tailoring.py, Marek; deterministisch/offline/keine-API, flaggt-ändert-nichts; 80k-Schnitt User 2026-06-28 = Entscheidungs-Kern vorgezogen NICHT Text-Gen; Brücke JDParser↔CV beide via jdparser.parse()/KEYWORD_KATALOG=kein-Schreibweisen-Drift; API abgleich(jd_result,cv_result)+abgleich_texte(txt,txt)+hat_luecke()=Gate+report(); CLI python tailoring.py <anzeige> <cv> --json exit1=MUSS-Keyword-fehlt; Ausgabe vorhanden/fehlend(+kategorien)/muss_fehlt(vorrang)/kann_fehlt/abdeckung_prozent(div0-sicher); verify 30/30 grün + Live-CLI-Smoke 38%-Abdeckung-Fräsen-Lücke; beide Code/kein-PII committed; NICHT in PII-Generator eingehängt; Detail state/etappe_v8_state.md); agenten-roadmap-E-C-teil3=NÄCHSTE-MAREK(ATS-Linter ats_lint.py: CV-.docx auf ATS-Risiken Tabellen/Mehrspaltig/Header-Footer-Kontakt/Nicht-Standard-Überschriften prüfen, python-docx→global-py-3.11, adressiert §3.6a; Grundlage state/agenten_roadmap.md C); agenten-roadmap-E-C-textwriter=EIGENE-FRISCHE-SESSION-MAREK(CoverLetterWriter+CVTailoring-Text konsumieren parse()+abgleich(), volles ~150k-Paket); etappe-optional=natives-Xing/Jobware-Scraping-Wolf(nur falls Google-Umweg unzureichend); public-repo=KEIN-PII-pushen

---

## Was ist das

Ein **read-only Job-Such- & Matching-Agent**: durchsucht Jobbörsen, scored die Treffer
gegen das Jobprofil des Users und liefert priorisierte Vorschläge. **Kein** Auto-Bewerben,
**kein** Profil-Steuern (siehe Caveats).

## crewai-Fix (Etappe v6) — ABGESCHLOSSEN 2026-06-28 (Wolf)

Erledigt. Kurz (Detail: `state/etappe_v6_state.md`): crewai war **nicht** laufzeit-broken, nur eine
`pip check`-Warnung; die regex-Constraints sind **disjunkt** (jobspy `<2025` vs crewai `>=2026`) →
Reconcile war mathematisch unmöglich. Lösung = **JobSpy ins projekt-eigene `.venv` isoliert** (nicht
crewai anfassen = Opfer ≠ Verursacher); global geheilt (`pip check` sauber, crewai/crewai-tools
importieren). **Run-Befehl ab jetzt `.\.venv\Scripts\python.exe …`** (siehe Kopf). Daraus die Regel:
*global nie für einen Projekt-Konflikt opfern — den jüngeren Eindringling isolieren.*

---

## Sofort-Einstieg NÄCHSTE Etappe — Roadmap E-C Teil 3 (ATS-Linter `ats_lint.py`) (frischer Chat, Marek)

Etappe 1–8 fertig (Engine + MatchAgent + Web-UI + CriticAgent + FactGroundingAgent + crewai-Fix +
**JDParserAgent** + **TailoringAgent/GapAnalysis**). Reihenfolge:
0. **ZUERST lesen:** `state/agenten_roadmap.md` **Abschnitt C** (ATS-Befund: Single-Column statt
   randlose Tabellen, Kontakt Plain-Text oben, antichronologisch) + `state/etappe_v8_state.md`.
1. **Lesen:** dieses HANDOFF + bei Bedarf `state/etappe_v7_state.md` (JDParser) + `state/etappe_v5/4_state.md`.
2. **Environment-Smoke (§3.11):** venv-Python: `verify_engine.py` + `verify_match.py` + `verify_critic.py`
   + `verify_factground.py` + `verify_jdparser.py` + `verify_tailoring.py` exit 0.
   ⚠️ **ATS-Linter braucht `python-docx`** → läuft über **global `py -3.11`** (wie `profile/`-Generatoren),
   NICHT venv. Vor Bau prüfen: `py -3.11 -c "import docx"`.
3. **Mit Marek** ATS-Linter bauen: `ats_lint.py` prüft ein CV-`.docx` deterministisch auf ATS-Risiken
   (Tabellen, Mehrspaltigkeit, Kontakt in Header/Footer/Textbox, Nicht-Standard-Überschriften,
   Bild-only) → `pruefe()`/`hat_fehler()`-Gate, CLI + `verify_ats_lint.py`. Muster wie critic/factground.
4. Selbstcheck (§3.5) → auf „go"/„ZIP" warten → `state/etappe_v<N>_state.md`.
- **Danach (eigene ~150k-Session):** Text-Writer CoverLetterWriter + CVTailoring (konsumieren `parse()`
  + `abgleich()`). **Optional/Wolf:** natives Xing/Jobware-Scraping (nur falls Google-Umweg-Abdeckung dünn).
- **Muster (belegt):** critic.py + factground.py + jdparser.py + **tailoring.py** sind die Vorbilder
  (deterministisch, offline, importierbare API + CLI + eigenes `verify_*.py`, flaggt-ändert-nichts).

## Etappe 3 — Abschluss-Stand (erledigt 2026-06-27)
- **Lokale HTML-Web-UI (edyta)** unter `ui/` — `index.html` + `app.js` + `style.css`, vanilla, keine
  Dependencies, hell/nüchtern, Ultrawide-Card-Grid. JS-Bridge (`../treffer_v2.example.js` Default,
  echte `treffer_v2.js` umschaltbar), Doppelklick/`file://`, kein Server.
- Sortier-/filterbar (Score/Datum, Min-Score-Slider, Such-Titel, Freitext, Ausschluss-Toggle);
  `kann_treffer`-Chips, ko-/Ausschluss-/Gehalt-Warn-Badges, null→„k.A.".
- **Test:** headless 16/16 gegen Fixtures + `node --check` grün; **live in Chrome abgenommen** (User).
- **Committed:** nur `ui/`-Code (+ State/HANDOFF). Bridge/echte Treffer gitignored (per `check-ignore`
  bestätigt). Bedien-Hinweis: nackten Pfad NICHT in Chrome-Adresszeile tippen (→ Suche); Explorer-
  Doppelklick oder `file:///…/ui/index.html`. Detail: `state/etappe_v3_state.md`.

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
  - **Restpunkte (nicht blockierend):** Ausschluss `"Ausbildung"` zu breit (matcht „abgeschlossene Ausbildung"); ~~Google weiter 0~~ **DIAGNOSTIZIERT 2026-06-27** (s. u.); `_stable`-ZIP + Commit ausstehend (auf User-go).
- **Etappe 3 — Lokale HTML-Web-UI (edyta): ✅ ERLEDIGT 2026-06-27.** `ui/index.html`+`app.js`+`style.css`, vanilla, JS-Bridge/Doppelklick (`file://`, kein Server), sortier-/filterbar, `kann_treffer`-Chips + Warn-Badges, null→„k.A."; headless 16/16 + live in Chrome abgenommen. Nur `ui/` committed, Bridge/Treffer gitignored. Detail: `state/etappe_v3_state.md`.
- **Agenten-Roadmap E-A — CriticAgent (Marek): ✅ ERLEDIGT 2026-06-27.** `critic.py` (deterministisch/offline, keine API, flaggt-ändert-nichts) + `verify_critic.py` (24/24 grün); Pipeline-Gate `pruefe()`/`hat_fehler()`, CLI exit 1=FEHLER/0=sauber, `--json`. Live gegen echten Brief: 346 W, 0 Fehler/0 Warnungen (kein False-Positive). Detail: `state/etappe_v4_state.md`.
- **Critic in Pipeline eingehängt: ✅ ERLEDIGT 2026-06-27** — in `profile/gen_bewerbung_guetepruefer.py` (lokal/gitignored/PII): nach `build_anschreiben()` läuft `pruefe()`+`report()`, read-only (flaggt, ändert nichts). Nur `critic.py` (`report`-Rename) committed. Detail: `state/etappe_v4_state.md`.
- **Agenten-Roadmap E-B — FactGroundingAgent (Marek): ✅ ERLEDIGT 2026-06-27.** `factground.py` (deterministisch/offline, keine API, flaggt-ändert-nichts) + `verify_factground.py` (31/31 grün). **Scope-Korrektur:** Wahrheitsquelle = **CV-Stammdaten reingefüttert** (nicht `jobprofil.yaml` = Suchprofil ohne CV-Fakten); API `sammle_fakten(*quellen)` + `pruefe(text, fakten)` + `hat_fehler()`. Known-Facts-Whitelist: Firma-mit-Rechtsform-nicht-in-Historie + Erfahrungsdauer-nicht-gedeckt = FEHLER; Akronym/Jahr-nicht-belegt = WARNUNG. Live: echter Brief 0F/0W (kein FP) + Negativ-Kontrolle geflaggt. In Generator eingehängt (lokal/PII). Detail: `state/etappe_v5_state.md`.
- **Agenten-Roadmap E-C Teil 1 — JDParserAgent (Marek): ✅ ERLEDIGT 2026-06-28 (v7).** `jdparser.py` (deterministisch/offline, keine API, extrahiert-ändert-nichts) + `verify_jdparser.py` (38/38 grün). E-C geschnitten (User): nur JDParser=Fundament. API `parse(text)` + `keywords_flach()`=ATS-Liste + `report()`; CLI `--json`. Kuratiertes `KEYWORD_KATALOG` (Industriemechaniker/QS, erweiterbar), Muss/Kann via zeilen-Trigger (muss-Vorrang), Abschnitts-Segmentierung, Umlaut-Folding ä↔ae. Beide Code/kein-PII committed; NICHT in PII-Generator eingehängt. Detail: `state/etappe_v7_state.md`.
- **Agenten-Roadmap E-C CVTailoring-Kern — TailoringAgent/GapAnalysis (Marek): ✅ ERLEDIGT 2026-06-28 (v8).** `tailoring.py` (deterministisch/offline, keine API, flaggt-ändert-nichts) + `verify_tailoring.py` (30/30 grün). Brücke JDParser↔CV: `abgleich()`/`abgleich_texte()` → vorhanden/fehlend + muss_fehlt/kann_fehlt + Abdeckung%; Gate `hat_luecke()`, CLI exit 1 bei MUSS-Lücke. Entscheidungs-Kern (kein Text-Gen). Beide Code/kein-PII committed. Detail: `state/etappe_v8_state.md`.
- **Agenten-Roadmap E-C Teil 3 — ATS-Linter `ats_lint.py` (Marek): NÄCHSTE Etappe.** CV-`.docx` auf ATS-Risiken prüfen (python-docx → global `py -3.11`); adressiert §3.6a. Grundlage `state/agenten_roadmap.md` C.
- **Agenten-Roadmap E-C Text-Writer — CoverLetterWriter + CVTailoring-Text (Marek): eigene ~150k-Session.** Konsumieren `parse()` + `abgleich()`. Grundlage `state/agenten_roadmap.md` A.4 + B.
- **Google-Quelle 0 Treffer — DIAGNOSTIZIERT 2026-06-27 (Marek):** JobSpy-Upstream-Bug [#302](https://github.com/speedyapply/JobSpy/issues/302) (`initial cursor not found`, offen/kein Fix, betrifft nur Google+ZipRecruiter), **nicht** unsere Query (5 Phrasen-Varianten alle 0 in ~0.2s, Indeed 39). Engine zeigt jetzt Pro-Quelle-Tally + Hinweis bei `google:0`; `jobprofil.example.yaml`-Kommentar ehrlich; Google-Default an gelassen (greift wieder nach Upstream-Fix). **Konsequenz:** Xing/Jobware-Umweg greift derzeit NICHT → Abdeckung allein aus Indeed. Memory `jobspy-google-broken`.
- **Etappe (optional) — natives Xing/Jobware-Scraping (Wolf):** jetzt relevanter (Google-Umweg derzeit tot, s. o.) — angehen falls Indeed-Abdeckung zu dünn.
- **global-pip/crewai gebrochen → ✅ ERLEDIGT 2026-06-28 (v6, Wolf):** JobSpy ins projekt-eigene `.venv` isoliert (disjunkte regex-Constraints), global crewai/LangChain geheilt (`pip check` sauber). Run-Befehl ab v6 = `.\.venv\Scripts\python.exe`. Detail: `state/etappe_v6_state.md`.
- **Weiter offene Altlast:** echter ATS-Parser-Durchlauf des CV-Outputs (§3.6a-Smoke — externer Upload, User-Aktion; Claude kann nur docx + Checkliste vorbereiten).

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

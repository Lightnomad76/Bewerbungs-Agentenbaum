# HANDOFF — Jobsuche-Agent (Bewerbungshilfe)

**Erstellt:** 2026-06-22 · **Aktualisiert:** 2026-06-27 (Etappe 5 = Agenten-Roadmap E-B: FactGroundingAgent gebaut + verifiziert + eingehängt + committed; nächste Session = E-C JDParser/getrennte Writer/ATS mit Marek+Wolf)
**Phase:** **Etappe 5 (Agenten-Roadmap E-B, FactGroundingAgent, Marek) ABGESCHLOSSEN** + Google-Altlast diagnostiziert (#302). **Nächstes (User-Entscheid 2026-06-27): ZUERST crewai-Fix (eigene Etappe), DANN E-C** — beides je FRISCHER Chat.
**Ziel-Session:** Claude Code CLI (nächste Etappe = crewai-Fix / Wolf; danach Roadmap E-C / Marek+Wolf)
**Sprache:** Deutsch, technische Begriffe Englisch lassen
**Repo:** öffentlich auf github.com/Lightnomad76/Bewerbungs-Agentenbaum — **PII-Dateien NIE pushen** (jobprofil.yaml, firmenhistorie_enriched.md, etappe_bewerbung_guetepruefer_state.md, treffer_v*.json/.csv mit echten Treffern, Lebensläufe/Anschreiben; alle gitignored). Memory: `github-repo-public`.

!ETAPPE-GATE: etappe-1=ABGESCHLOSSEN; etappe-2=ABGESCHLOSSEN+COMMITTED(MatchAgent match.py + Fixes K1/K2/S1 + verify_match.py; live 35 Treffer/2.78s; skills_muss bewusst leer; Ausschluss nur im Titel = AUSSCHLUSS_FELDER, False-Positives behoben; commits da545d5+5e53391; _stable-ZIP v2 gezogen — siehe state); etappe-3=ABGESCHLOSSEN+COMMITTED(lokale HTML-Web-UI ui/index.html+app.js+style.css, edyta; JS-Bridge ../treffer_v2.example.js Default, Doppelklick/file:// kein Server; sortier-/filterbar, kann_treffer-Chips, ko-/Ausschluss-/Gehalt-Badges, null→k.A.; headless 16/16 + live in Chrome abgenommen 2026-06-27; nur ui/ committed, Bridge/Treffer gitignored — siehe state/etappe_v3_state.md); live-jobspy-run=netz-posten(billig ~2.8s, kein laufzeit-gate); etappe-4=ABGESCHLOSSEN+COMMITTED(Roadmap E-A CriticAgent critic.py + verify_critic.py, Marek; deterministisch/offline/keine-API, flaggt-ändert-nichts; API pruefe()/hat_fehler() = Pipeline-Gate, CLI exit 1=FEHLER/0=sauber, --json; Floskel-Blacklist+Pflichtfelder=FEHLER, Adjektiv/Länge/7-Sek/Betreff=WARNUNG; verify 24/24 grün; live gegen echten Brief 346W 0F/0W = kein False-Positive; beide Dateien=Code/kein-PII committed; echter Brief nur gelesen — siehe state/etappe_v4_state.md); critic-eingehängt=JA(2026-06-27, in profile/gen_bewerbung_guetepruefer.py = LOKAL/gitignored/PII; build_anschreiben()->（pfad,text), pruefe()+report() nach Build, read-only flaggt-nur; critic.py _report->report committed; verify 24/24); etappe-5=ABGESCHLOSSEN+COMMITTED(Roadmap E-B FactGroundingAgent factground.py + verify_factground.py, Marek; deterministisch/offline/keine-API, flaggt-ändert-nichts; SCOPE-KORREKTUR: Wahrheitsquelle NICHT jobprofil.yaml=Suchprofil-ohne-CV-Fakten sondern CV-STAMMDATEN-REINGEFÜTTERT via sammle_fakten(*quellen); API pruefe(text,fakten)+hat_fehler()=Gate, CLI factground.py <text> <wahrheit...> exit1=FEHLER --json; Known-Facts-Whitelist: Firma-mit-Rechtsform-nicht-in-Historie+Erfahrungsdauer-N-Jahre-nicht-gedeckt=FEHLER, Akronym/Jahr-nicht-belegt=WARNUNG; verify 31/31 grün; live echter Brief 0F/0W kein-FP + Negativ-Kontrolle Thyssenkrupp/40Jahre/WIG geflaggt; beide Dateien Code/kein-PII committed — siehe state/etappe_v5_state.md); factground-eingehängt=JA(2026-06-27, in gen_bewerbung_guetepruefer.py LOKAL/gitignored/PII; fakten aus EXPERIENCE/ALPHA/WEITERE/SAMSON/COPERION/KURZPROFIL+STAMMDATEN_EXTRA+CV_DATE_LINE; nach build_anschreiben() neben critic; read-only flaggt-nur; end-to-end 0/0); crewai-fix=NÄCHSTE-EIGENE-FRISCHE-SESSION-ZUERST(User 2026-06-27; globale-py311-Env NICHT-Projekt-Code; regex-Konflikt crewai-will~=2026.1.15-vs-global-2024.11.6-von-JobSpy; numpy-1.26.3-geteilt; empfohlen=crewai-eigenes-venv statt global-reconcile=re-bricht-JobSpy; Wolf-Hut; Snapshot+Plan in Sofort-Einstieg); agenten-roadmap-E-C=DANACH-EIGENE-FRISCHE-SESSION-MIT-MAREK+WOLF(JDParserAgent/KeywordExtractor + getrennte Writer CoverLetter/CVTailoring + ATS-Zwei-Pfad fest in ReportAgent; Grundlage state/agenten_roadmap.md A.3/A.4+C); etappe-optional=natives-Xing/Jobware-Scraping-Wolf(nur falls Google-Umweg unzureichend); public-repo=KEIN-PII-pushen

---

## Was ist das

Ein **read-only Job-Such- & Matching-Agent**: durchsucht Jobbörsen, scored die Treffer
gegen das Jobprofil des Users und liefert priorisierte Vorschläge. **Kein** Auto-Bewerben,
**kein** Profil-Steuern (siehe Caveats).

## Sofort-Einstieg NÄCHSTE Etappe — crewai-Fix (frischer Chat, Wolf-Hut) — ZUERST

**Kontext:** Nicht Projekt-Code, sondern Aufräumen einer Nebenwirkung: JobSpy-Install (Etappe 1)
hat global `regex 2026.1.15→2024.11.6` + `numpy 2.4.6→1.26.3` heruntergestuft → **crewai gebrochen**.
**Read-only Env-Snapshot (2026-06-27, `py -3.11 -m pip show`):**
- `numpy 1.26.3` — required-by: chromadb, lancedb, langchain-community, onnxruntime, pandas, **python-jobspy**
- `regex 2024.11.6` — required-by: **crewai**, **python-jobspy**, tiktoken  ← der eigentliche Konflikt
- `crewai 1.14.6` (will `regex~=2026.1.15`) · `python-jobspy 1.1.82`

**Plan (Wolf):**
1. **Env-Smoke zuerst:** `py -3.11 verify_engine.py` + `verify_match.py` exit 0 (JobSpy-Stack intakt) —
   das ist die Baseline, die NICHT brechen darf.
2. **Entscheid Isolation vs. Reconcile:** **empfohlen = crewai in eigenes venv** (volle Isolation,
   0 Risiko für JobSpy). Reconcile im global-env (regex/numpy hochziehen) riskiert JobSpy-Re-Bruch —
   nur wenn JobSpys echte Constraints (`pip show`/Metadaten) `regex 2026.x` + `numpy<2` zulassen;
   vorher `lib-version-checker` gegen JobSpy-Kompat.
3. Nach dem Fix: **beide** prüfen — JobSpy-Verifies grün **und** `py -3.11 -c "import crewai"` ok.
4. Selbstcheck (§3.5) → „go" → `state/etappe_v<N>_state.md`. **Kein** Major-Upgrade blind (§ Quellen-Stand).

---

## Danach — Roadmap E-C (JDParser + getrennte Writer + ATS) (frischer Chat, Marek+Wolf)

Etappe 1–5 fertig (Engine + MatchAgent + lokale Web-UI + CriticAgent + FactGroundingAgent). E-C =
**eigene frische Session**, NICHT anhängen. Reihenfolge:
0. **ZUERST lesen:** `state/agenten_roadmap.md` — Recherche-Befunde (JDParser-Erweiterung,
   getrennte Writer, ATS-Zwei-Pfad-CV/Abschnitt C, Stil-Checkliste). Das ist die Arbeitsgrundlage.
1. **Lesen:** dieses HANDOFF + `state/etappe_v5_state.md` (FactGrounding) + `state/etappe_v4_state.md`
   (Critic) + bei Bedarf `state/etappe_v2_state.md` (Engine/Match).
2. **Environment-Smoke (§3.11):** `py -3.11 verify_engine.py` UND `py -3.11 verify_match.py` UND
   `py -3.11 verify_critic.py` UND `py -3.11 verify_factground.py` exit 0.
3. **Mit Marek (Wolf bei ATS/Parsing)** den Roadmap-Umfang in eine konkrete Etappe schneiden
   (Session-Budget ~150k beachten, ggf. splitten — JDParser + 2 Writer + ATS ist groß, brief-writer
   nutzen). Scope-Grenze: read-only, login-frei, deterministisch/offline — Semantik/API nur bewusst+optional.
4. Selbstcheck (§3.5) → auf „go"/„ZIP" warten → `state/etappe_v<N>_state.md`.
- **Alternativ** optionale Etappe (natives Xing/Jobware-Scraping, Wolf) — nur falls Google-Umweg-
  Abdeckung später unzureichend; aktuell nicht priorisiert.
- **Muster für E-C:** critic.py + factground.py sind die belegten Vorbilder (deterministisch, offline,
  `pruefe()`/`hat_fehler()`-Gate, CLI + importierbare API, eigenes `verify_*.py`, flaggt-ändert-nichts).

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
- **Agenten-Roadmap E-C — JDParser + getrennte Writer + ATS (Marek/Wolf): NÄCHSTE Etappe**, eigene frische Session. JDParserAgent/KeywordExtractor + CoverLetterWriter + CVTailoring + ATS-Zwei-Pfad fest in ReportAgent. Grundlage `state/agenten_roadmap.md` A.3/A.4 + C.
- **Google-Quelle 0 Treffer — DIAGNOSTIZIERT 2026-06-27 (Marek):** JobSpy-Upstream-Bug [#302](https://github.com/speedyapply/JobSpy/issues/302) (`initial cursor not found`, offen/kein Fix, betrifft nur Google+ZipRecruiter), **nicht** unsere Query (5 Phrasen-Varianten alle 0 in ~0.2s, Indeed 39). Engine zeigt jetzt Pro-Quelle-Tally + Hinweis bei `google:0`; `jobprofil.example.yaml`-Kommentar ehrlich; Google-Default an gelassen (greift wieder nach Upstream-Fix). **Konsequenz:** Xing/Jobware-Umweg greift derzeit NICHT → Abdeckung allein aus Indeed. Memory `jobspy-google-broken`.
- **Etappe (optional) — natives Xing/Jobware-Scraping (Wolf):** jetzt relevanter (Google-Umweg derzeit tot, s. o.) — angehen falls Indeed-Abdeckung zu dünn.
- **global-pip/crewai gebrochen → JETZT GEPLANT als nächste Etappe (ZUERST, eigener frischer Chat, Wolf):** Snapshot + Plan oben im Sofort-Einstieg. Globale Env, nicht Projekt-Code; empfohlen crewai eigenes venv.
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

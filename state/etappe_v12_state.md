# Etappe v12 — State nach Abschluss (E-C Generator-Integration + CV-Rendering + ats_lint)

**Datum:** 2026-06-28
**ZIP:** (auf Freigabe; `_stable`-Capstone via `make_backup.py` angeboten)
**Status:** ✅ funktionsfähig + verifiziert (Repo 10/10 Verify-Suites grün; PII-Generator-Pfade in TEMP gesmoket)
**Persona:** Marek (Code). Besonderheit: **mehrere Posten in EINER Session gekettet** (§3.11-Fix, s. u.).

---

## Kontext: Session-Modus (User-Entscheid 2026-06-28)

§3.11 wurde geschärft (CLAUDE.md v4.30): **150k = Ziel zum Füllen, kleine deterministische Posten
ketten** statt jeden als „eigene Session" zu handoffen. Diese Session hat das gelebt: 11 Posten,
Budget-Beobachtung per UI-% (Memory `session-budget-60-percent`: Ziel ~60%, dann Abschluss).

## Was wurde gemacht (committed = Repo-Code, kein PII)

- **v11 CVTailoringAgent** `cvtailoring.py` + `verify_cvtailoring.py` (`8c7e73e`) — Stationen/Bullets
  nach Anzeigen-Relevanz, read-only; **Chronologie-Option** `station_reihenfolge=relevanz|chronologisch`
  + CLI `--chrono` (`132ac93`, behebt v11-Known-Issue). verify 43→54 grün.
- **KEYWORD_KATALOG erweitert** (`481e955`) — mess_qs um Güteprüfung/QS (Maß-/Festigkeits-/Druck-/
  Leckage-/Dichtheits-/Sichtprüfung, Toleranz, Abnahmeprüfung; Qualitätssicherung-regex +qualitätsprüfung).
  Single-Source → wirkt auf jdparser/tailoring/cvtailoring; alle 3 Verifies grün, kein Fixture-Bruch.
- **`verify_pipeline.py`** (`c6b81fe`) — End-to-End-Kompositionstest der Kette (Single-Source-Keyword-
  Konsistenz, durchgängige Ehrlichkeit muss_fehlt-nie-im-Brief, critic+factground 0 FEHLER, Determinismus,
  Bequemlichkeits-Pfad-Äquivalenz). 14/14. Schließt Lücke: Modul-Komposition war ungetestet.
- **`verify_all.py`** (`20904b4`) — Runner über alle Suites, codiert Interpreter-Split (ats_lint→global
  py-3.11, Rest→venv). `py -3.11 verify_all.py` = 10/10 grün.
- **README** (`5080b93`) — Bewerbungs-Pipeline-Sektion + Setup auf venv korrigiert (`py -3.11 main.py`
  war seit v6 falsch) + Roadmap-Status (E-A…E-C ✅).

## Was wurde gemacht (lokal/PII = `profile/gen_bewerbung_guetepruefer.py`, gitignored, NICHT committed)

- **JD-Pipeline-Integration** — jdparser/tailoring/cvtailoring/coverletter als read-only Report-Block am
  `__main__`-Ende (wie critic/factground), gated über `ANZEIGE_DATEI` (Default None = Hinweis).
  `build_bewerber()` mappt CV-Stammdaten-Tupel ins coverletter/cvtailoring-Schema (Single-Source).
- **`build_bewerber`-Stammdaten** real-belegte Skills ergänzt → Smoke-Abdeckung 56%→78%.
- **CV-RENDERING (großer Posten, User-green-light über Handoff-Grenze)** — `build_cv`/`build_cv_ats`
  ordnen Bullets je Station nach Anzeigen-Relevanz via `_order_bullets`+`_TAILOR_MAP` (`aktiviere_tailoring`,
  Modus chronologisch = Stationen antichronologisch). **DEFAULT unverändert** (nur bei gesetzter
  ANZEIGE_DATEI). Read-only: keine Bullets entfernt (Score-0 ans Ende).
- **ats_lint-Hook** — lintet die `build_cv_ats`-Ausgabe im `__main__` (schließt offene Roadmap-Lücke).

## Test-Status

- **Repo:** `verify_all.py` 10/10 Suites grün (engine/match/critic/factground/jdparser/tailoring/
  cvtailoring/coverletter/pipeline + ats_lint).
- **PII-Generator (in TEMP gesmoket, echte CVs NICHT überschrieben):** Default-Identität ohne Anzeige;
  SAMSON-Bullet-Reorder read-only 6/6; voller 3-docx-Build mit Tailoring aktiv ohne Crash; ats_lint auf
  ATS-Variante **0 FEHLER/0 WARNUNGEN** (0 Tabellen, 1 Spalte, 8 Headings) = ATS-sauber.
- **Hygiene:** Generator-Backup (.bak) zunächst versehentlich im Repo (nicht gitignored!) → in Scratchpad
  verschoben, PII-Leak abgewendet.

## Was wurde verworfen / bewusst nicht gemacht

- **Stationen-Reorder im gerenderten CV** — bewusst NICHT (bricht antichronologische Konvention =
  Recruiter-Warnsignal); nur Bullets stationsintern. cvtailoring kann Stationen reordern (Report), das CV nicht.
- **Natives Xing/Jobware-Scraping** — bleibt offener GROSSER Posten (Wolf, Domänenwechsel, eigene Session).
- **CLAUDE.md §3.11 numerisch 150k→~60%** — bewusst erst NÄCHSTE Session (User: „nächste session umsetzen");
  diese Session nur beobachtet (Memory hält die 60%-Regel).

## Known Issues / Offene Punkte

- **§3.6a (unverändert):** echter externer ATS-Parser-Durchlauf des CV-Outputs offen (ats_lint ≠ echter Parser).
- **Google-Quelle 0** (JobSpy #302) unverändert.
- **CLAUDE.md §3.11** numerische 60%-Umstellung steht für nächste Session aus.

## Nächste sinnvolle Etappe

- **Optional/Wolf:** natives Xing/Jobware-Scraping (großer Posten).
- **Nächste Session zuerst:** §3.11 numerisch auf ~60% umstellen (Memory `session-budget-60-percent`).

## Verweis-Quellen

- Vorgänger: `state/etappe_v11_state.md` (CVTailoring), `etappe_v10_state.md` (CoverLetter), `_v8` (Tailoring)
- Planungsgrundlage: `state/agenten_roadmap.md`; lebende Plandatei: `HANDOFF.md` (!ETAPPE-GATE)
- Memories: `session-budget-60-percent`, `agenten-roadmap-ats`, `venv-exception-jobspy-isolated`

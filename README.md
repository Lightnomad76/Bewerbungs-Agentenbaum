# Jobsuche-Agent

Ein **read-only** Job-Such- & Matching-Agent: durchsucht Jobbörsen, scored die Treffer gegen
ein Jobprofil und liefert priorisierte Vorschläge als JSON/CSV. **Kein** Login, **kein**
Auto-Bewerben, **kein** Profil-Steuern — bewusst login-frei (AGB/Account-Sperrgefahr).

## Funktionsweise

Pipeline `ProfileAgent → SearchAgent → ReportAgent`:

1. **ProfileAgent** liest `profile/jobprofil.yaml` (Suchbegriffe, Standort/Umkreis, aktive Quellen).
2. **SearchAgent** sucht je Titel über alle aktiven Quellen via [JobSpy](https://github.com/speedyapply/JobSpy)
   (Indeed, Google Jobs, LinkedIn, Glassdoor, ZipRecruiter). Eine ausgefallene Quelle bricht den Lauf nicht ab.
3. **ReportAgent** dedupliziert und schreibt `treffer_v1.json` (Bridge zu einer späteren Web-UI) + `treffer_v1.csv`.

## Setup & Start

JobSpy ist in einem projekt-eigenen venv (`.venv`) isoliert — sein regex-Constraint (`<2025`)
kollidiert mit dem globalen AI-Stack (`>=2026`), ein gemeinsamer Topf ist unmöglich. Engine +
Verifies laufen deshalb über das venv-Python (nicht global `py -3.11` — global hat kein JobSpy):

```bash
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install python-jobspy pandas pyyaml
cp profile/jobprofil.example.yaml profile/jobprofil.yaml   # dann ausfüllen
.\.venv\Scripts\python.exe main.py            # Suche ausführen -> treffer_v1.json + .csv
.\.venv\Scripts\python.exe verify_engine.py   # Offline-Mechanik-Selbsttest (exit 0 = grün)
```

Die deterministischen Bewerbungs-Agenten (unten) brauchen **kein** JobSpy → sie laufen unter
dem venv **oder** global `py -3.11` (`ats_lint.py` zusätzlich `python-docx`).

## Konfiguration

`profile/jobprofil.yaml` (Vorlage: `profile/jobprofil.example.yaml`) steuert Suchbegriffe,
Standort + Umkreis, Remote/Job-Type und die aktiven Quellen. Die echte `jobprofil.yaml` ist
gitignored (persönliche Daten) — nur das `.example` ist eingecheckt.

## Quellen-Hinweise

- **Indeed / Google** = verlässliche Default-Quellen.
- **LinkedIn** ist stark rate-limited (oft Block ab ~Seite 10) → Proxies empfohlen.
- **Xing/Jobware** werden über den Google-Jobs-Umweg mitgegriffen (kein nativer Scraper).
- Stand der installierten Libs/Quellen: `state/quellen_stand_2026-06-25.md`.

## Bewerbungs-Pipeline (deterministisch, offline, keine API)

Über die Job-Suche hinaus bündelt das Repo eine Kette deterministischer Agenten, die eine
Bewerbung gegen eine **konkrete Stellenanzeige** prüfen und zuschneiden — alle offline, ohne
LLM-API, read-only (sie **flaggen/sortieren, erfinden nichts**). Jedes Modul hat ein eigenes
`verify_*.py` (Offline-Selbsttest, exit 0 = grün):

| Modul | Rolle |
|---|---|
| `jdparser.py` | parst die Anzeige → Keywords + Muss/Kann-Anforderungen (kuratiertes Domänen-Wörterbuch) |
| `tailoring.py` | Abgleich Anzeige ↔ CV: vorhanden / fehlend (Muss-Vorrang) + Abdeckung % |
| `cvtailoring.py` | sortiert CV-Stationen/Bullets nach Anzeigen-Relevanz (`--chrono`: antichronologisch); weist Weggelassenes aus |
| `coverletter.py` | baut ein JD-getriebenes Anschreiben aus den CV-Stammdaten (nennt nur Gedecktes) |
| `critic.py` | Stil-/Pflichtfeld-Check (Floskel-Blacklist, DIN-5008-Felder) → FEHLER/WARNUNG |
| `factground.py` | gleicht jede Aussage gegen die CV-Stammdaten ab — nicht gedeckte Fakten werden geflaggt |
| `ats_lint.py` | prüft das CV-`.docx` auf ATS-Parsing-Risiken (Tabellen/Mehrspaltig/Header-Kontakt) |

Kette: `jdparser → tailoring → {cvtailoring, coverletter}`; der Brief-Output besteht `critic`
**und** `factground` mit 0 FEHLERN — end-to-end mechanisch geprüft in `verify_pipeline.py`.

```bash
.\.venv\Scripts\python.exe cvtailoring.py <anzeige.txt> <bewerber.json> [--json] [--chrono]
.\.venv\Scripts\python.exe verify_pipeline.py        # End-to-End-Kompositionstest
```

## Roadmap

| Etappe | Inhalt | Status |
|---|---|---|
| 1 | Daten-Engine (Suchen + JSON/CSV-Report) | ✅ |
| 2 | MatchAgent — deterministisches Keyword-Scoring offline | ✅ |
| 3 | Lokale HTML-Web-UI (lädt die gescorte JSON) | ✅ |
| E-A…E-C | Bewerbungs-Pipeline (Critic · FactGrounding · JDParser · Tailoring · ATS-Linter · CoverLetter · CVTailoring) | ✅ |
| 4 | Natives Xing/Jobware-Scraping | optional |

## Projekt-Doku

Der laufende Projektstand wird als lebendes Dashboard in einem separaten (privaten) Obsidian-Vault
gepflegt; `HANDOFF.md` (Plan + offene Punkte) und `state/` (Detail-Changelog je Etappe) in diesem
Repo bleiben die **Quelle der Wahrheit**.

## Scope / Caveats

- **Read-only Scraping** bewegt sich in einer AGB-Grauzone; Einloggen/Automatisieren von Konten
  ist die rote Linie — das Tool bleibt deshalb login-frei.
- Matching ist deterministisch & offline (gratis); semantische/LLM-Erweiterung optional später.
- Tatsächliche Erfolgsrate je Quelle ist erst beim echten Lauf messbar.

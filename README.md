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

Python (primär `py -3.11`; JobSpy-Stack ist unter 3.11 stabil, 3.14 bricht beim numpy-Source-Build).

```bash
py -3.11 -m pip install python-jobspy pandas pyyaml
cp profile/jobprofil.example.yaml profile/jobprofil.yaml   # dann ausfüllen
py -3.11 main.py            # Suche ausführen -> treffer_v1.json + .csv
py -3.11 verify_engine.py   # Offline-Mechanik-Selbsttest (exit 0 = grün)
```

## Konfiguration

`profile/jobprofil.yaml` (Vorlage: `profile/jobprofil.example.yaml`) steuert Suchbegriffe,
Standort + Umkreis, Remote/Job-Type und die aktiven Quellen. Die echte `jobprofil.yaml` ist
gitignored (persönliche Daten) — nur das `.example` ist eingecheckt.

## Quellen-Hinweise

- **Indeed / Google** = verlässliche Default-Quellen.
- **LinkedIn** ist stark rate-limited (oft Block ab ~Seite 10) → Proxies empfohlen.
- **Xing/Jobware** werden über den Google-Jobs-Umweg mitgegriffen (kein nativer Scraper).
- Stand der installierten Libs/Quellen: `state/quellen_stand_2026-06-25.md`.

## Roadmap

| Etappe | Inhalt | Status |
|---|---|---|
| 1 | Daten-Engine (Suchen + JSON/CSV-Report) | ✅ |
| 2 | MatchAgent — deterministisches Keyword-Scoring offline | geplant |
| 3 | Lokale HTML-Web-UI (lädt die gescorte JSON) | geplant |
| 4 | Natives Xing/Jobware-Scraping | optional |

## Scope / Caveats

- **Read-only Scraping** bewegt sich in einer AGB-Grauzone; Einloggen/Automatisieren von Konten
  ist die rote Linie — das Tool bleibt deshalb login-frei.
- Matching ist deterministisch & offline (gratis); semantische/LLM-Erweiterung optional später.
- Tatsächliche Erfolgsrate je Quelle ist erst beim echten Lauf messbar.

# Quellen-/Dependency-Stand — Snapshot 2026-06-25

**Zweck:** Ist-Stand der Job-Quellen (JobSpy + Treiber-Libs) VOR der Upgrade-Suche festhalten —
Rollback-Basis (§3.2) + Vergleichsbasis für den Upgrade-Check.

## Interpreter
- **Pin:** `py -3.11` (3.11.9) — JobSpy-Stack hier installiert. Grund: 3.14 = numpy-Source-Build-Bruch (Memory `jobspy-py311-pin`).
- 3.14.4 parallel vorhanden, aber NICHT für dieses Projekt genutzt.

## Quellen (Job-Boards) — alle via JobSpy
- Aktiv/abgedeckt: Indeed (DE, stabil), Google Jobs, LinkedIn (stark rate-limited), Glassdoor, ZipRecruiter.
- `GUELTIGE_QUELLEN` in `main.py:30`: indeed, google, linkedin, glassdoor, zip_recruiter.
- Xing/Jobware = Google-Jobs-Umweg (kein nativer Scraper).

## Installierte Versionen (py -3.11, `pip freeze`, Stand 2026-06-25)
| Paket | Version | Rolle |
|---|---|---|
| python-jobspy | **1.1.82** | Primär-Tool (alle Quellen) |
| pandas | 2.3.3 | DataFrame / Report |
| PyYAML | 6.0.3 | jobprofil.yaml |
| numpy | 1.26.3 | (↓ von 2.4.6 bei JobSpy-Install — siehe crewai-Caveat) |
| pydantic | 2.12.5 | JobSpy-Modelle |
| requests | 2.34.2 | HTTP |
| tls-client | 1.0.1 | TLS-Fingerprint-Scraping |
| beautifulsoup4 | 4.13.5 | HTML-Parsing |
| markdownify | 0.13.1 | Job-Description → Markdown |
| regex | 2024.11.6 | (↓ von 2026.1.15 bei JobSpy-Install) |

**JobSpy `Requires`:** beautifulsoup4, markdownify, numpy, pandas, pydantic, regex, requests, tls-client.

## Bekannte Nebenwirkung (NICHT vergessen vor Upgrade)
- JobSpy-Install hatte global numpy 2.4.6→1.26.3 + regex 2026.1.15→2024.11.6 heruntergestuft
  → **crewai broken** (`requires regex~=2026.1.15`). Global pip, kein venv → jedes Upgrade
  kann andere globale Tools (crewai) treffen. Vor Quellen-Upgrade abwägen / ggf. venv.

## Letzter verifizierter Lauf
- Etappe 1 (2026-06-23): 2.7s, 36 reale DE-Treffer (alle Indeed; Google lieferte 0).

---

# Upgrade-Suche — Befunde 2026-06-25 (PyPI + GitHub, web-verifiziert)

## Kernbefund: JobSpy
- **PyPI `python-jobspy` 1.1.82 = installiert = neuester Release** (2025-07-28). **Kein pip-Upgrade.**
- **ABER GitHub-`main` ist neuer als PyPI** (letzte Commits bis **2026-02-18**), Fixes NICHT auf PyPI:
  - `fix(linkedin): add fallback for date parsing on new job listings` (2026-02-18) — direkt relevant (LinkedIn = unsere wackligste Quelle).
  - `fix: relax numpy version constraint to >=1.26.0` — würde den harten numpy-Downgrade (→ crewai-Bruch) entschärfen.
  - `Fix: BDJobs user_agent kwarg` (nicht relevant für DE).
  - ⇒ Optionales Upgrade nur via Git-Install (`pip install git+https://github.com/speedyapply/JobSpy`) = **unreleased/ungetestet**, riskanter als PyPI-Pin.

## Transitive Libs (latest auf PyPI vs. installiert)
| Paket | installiert | latest | Bewertung |
|---|---|---|---|
| requests | 2.34.2 | 2.34.2 | aktuell |
| pyyaml | 6.0.3 | 6.0.3 | aktuell |
| tls-client | 1.0.1 | 1.0.1 | aktuell |
| pydantic | 2.12.5 | 2.13.4 | minor, safe |
| beautifulsoup4 | 4.13.5 | 4.15.0 | minor, wahrsch. safe |
| regex | 2024.11.6 | 2026.5.9 | **Upgrade würde crewai-Bruch heilen** — aber JobSpy hatte's bewusst gepinnt; erst Kompat prüfen |
| markdownify | 0.13.1 | **1.2.2** | MAJOR-Sprung — JobSpy-Kompat unklar, nicht blind |
| numpy | 1.26.3 | **2.5.0** | MAJOR — JobSpy-`main` lockert Constraint, aber pandas/jobspy-Kompat erst prüfen |
| pandas | 2.3.3 | **3.0.3** | MAJOR — JobSpy auf pandas 3 NICHT verifiziert, hohes Bruch-Risiko |

## Empfehlung (Konfidenz-ehrlich)
- **JobSpy selbst:** kein Handlungsdruck — Tool steht still, PyPI = installiert. Git-`main` nur ziehen,
  wenn LinkedIn-Datumsfehler real auftritt (dann gezielt, nicht prophylaktisch).
- **Major-Upgrades (pandas 3 / numpy 2 / markdownify 1):** NICHT blind — JobSpy 1.1.82 ist gegen die alten
  Major-Versionen gebaut; global pip ohne venv ⇒ ein Bruch trifft auch crewai. Erst `lib-version-checker`.
- **Status der Befunde:** PyPI-Versionen + GitHub-Commits = **getestet/web-verifiziert**.
  Kompatibilitäts-Bewertungen = **durchgedacht, nicht installiert/getestet**.

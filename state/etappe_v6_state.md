# Etappe v6 — crewai-Fix via Projekt-venv (Isolation statt Reconcile)

**Datum:** 2026-06-28 · **Hut:** Wolf (Env/Infra) · **Status:** ABGESCHLOSSEN + COMMITTED
**Typ:** Environment-/Infra-Etappe (kein Projekt-`.py`-Code geändert, nur venv + global-pip + Doku)

## Ausgangslage (HANDOFF-Premise vs. Realität)

HANDOFF nahm an: „crewai broken" durch den JobSpy-Install (Etappe 1) — der global
`regex 2026.1.15→2024.11.6` + `numpy 2.4.6→1.26.3` heruntergestuft hat.

**Real gemessen (live `pip show`/`pip check`/`import`):**
- crewai 1.14.6 **importierte sauber** trotz regex 2024.11.6 — kein Laufzeit-Bruch.
- Einziger echter Defekt = **eine** `pip check`-Zeile: `crewai has requirement regex~=2026.1.15, but you have 2024.11.6`.
- **numpy war gar kein Konflikt** — `pip check` bemängelt nur regex; 1.26.3 passt beiden.

## Kernbefund — Constraints sind DISJUNKT (nicht neu aufrollen)

| Paket | regex-Constraint |
|---|---|
| `python-jobspy` | `>=2024.4.28, <2025.0.0` |
| `crewai`        | `~=2026.1.15` (= `>=2026.1.15`) |

**Kein einziger regex-Wert erfüllt `<2025` UND `>=2026`** → „Reconcile im global-Env"
(regex hochziehen) ist **mathematisch unmöglich**, hätte JobSpys eigene Deklaration verletzt.
Scan über ALLE globalen Pakete: nur `python-jobspy` erzwingt `<2025` (crewai braucht 2026,
tiktoken nur `>=2022`). `Required-by: python-jobspy` = **leer** → nichts Globales hängt an JobSpy.

## Was global wirklich steht (nicht „verirrtes Einzelpaket")

global py311 = **stehende AI-Agenten-Toolchain**: crewai + crewai-cli + crewai-core +
crewai-tools (crewai-tools `Required-by` crewai!) + langchain-core/community/classic/protocol/
text-splitters + openai 2.41.0 + instructor. Eine `pip uninstall crewai` hätte diesen ganzen
Stack zerrissen — **destruktiver Fehlvorschlag, vom User gestoppt**. Daraus die Regel unten.

## Entscheidung — Option A: JobSpy (Eindringling) isolieren, global heilen

User-Entscheid 2026-06-28: **Ausnahme zur globalen „kein venv"-Regel für DIESES Projekt.**
Nicht der vorbestehende globale Bestand wird geopfert, sondern die jüngere kollidierende
Projekt-Dependency isoliert.

**Durchgeführt:**
1. `.venv` (py 3.11.9) im Projekt angelegt → `python-jobspy==1.1.82` + `PyYAML` darin
   (zieht eigene `pandas 2.3.3`, `numpy 1.26.3`, `regex 2024.11.6`). `.venv` ist gitignored.
2. Alle 4 Verifies mit venv-Python grün: `verify_engine/match/critic/factground` exit 0.
3. Global geheilt: `pip uninstall -y python-jobspy` (Required-by leer) → `pip install regex==2026.1.15`.
4. Global verifiziert: `pip check` = „No broken requirements found." · `import crewai` + `import crewai_tools` OK · `import jobspy` global korrekt weg.

**End-Zustand — beide Töpfe gleichzeitig gesund:** global = crewai/LangChain (regex 2026.1.15,
pip check sauber); venv = JobSpy-Pipeline (regex 2024.x, 4/4 Verifies grün).

## Bewusst NICHT gemacht

- **crewai NICHT entfernt/verschoben** (Opfer, nicht Verursacher).
- **global numpy NICHT auf 2.4.6 hochgezogen** — pip check meckert bei 1.26.3 nicht; numpy-2-ABI-Risiko
  ohne aktuellen Bedarf. Nur auf ausdrücklichen Wunsch als separater Schritt.
- **Kein Projekt-Code geändert** — Verifies/main laufen unter dem Python, das sie aufruft; Fix ist rein
  „venv-Python statt global aufrufen" + Doku.

## NEUE REGEL (übergeordnet, gilt projektübergreifend)

> **Nie ein global installiertes Paket deinstallieren/downgraden, um den Constraint-Konflikt
> eines einzelnen Projekts zu lösen. Isoliert wird das Projekt (bzw. der jüngere Eindringling),
> nie der vorbestehende globale Bestand. Globales Env = read-/append-mostly für Projektarbeit.**
> Wurzel des Fehlvorschlags: destruktive Aktion als „Recommended" gelabelt + „absence in diesem
> Repo" als „global ungenutzt" fehlinterpretiert, ohne `Required-by`/global zu prüfen.

## Run-Befehle ab jetzt (KRITISCH für nächste Session)

- Engine/Verify: `.\.venv\Scripts\python.exe <datei>.py` — **NICHT** `py -3.11` (global ohne jobspy → ModuleNotFoundError).
- `profile/`-Generatoren (gen_cv/gen_bewerbung, kein jobspy, brauchen `docx`): weiter global `py -3.11`.

## Nächste Etappe

Agenten-Roadmap **E-C** (JDParser + getrennte Writer + ATS, Marek+Wolf) — eigene frische Session.
Grundlage `state/agenten_roadmap.md` A.3/A.4 + C. Env-Smoke nun via venv-Python.

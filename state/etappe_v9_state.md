# Etappe v9 — State nach Abschluss (Agenten-Roadmap E-C, Teil 3: ATS-Linter)

**Datum:** 2026-06-28
**ZIP:** (optional, auf Freigabe; `make_backup.py` nicht zwingend gelaufen)
**Status:** ✅ funktionsfähig + offline verifiziert (27/27) + Live gegen beide echten v3-CV-Pfade (ROT/GRÜN korrekt)
**Persona:** Marek (Code-Etappe). Grundlage: `state/agenten_roadmap.md` Abschnitt C (ATS-Befund).

---

## Scope (User-Entscheid 2026-06-28)

60k-Schnitt: nach v8 (Tailoring) den **ATS-Linter** als nächsten eigenständigen Agent vorgezogen
(Teil 3 / Abschnitt C). Adressiert den lange offenen §3.6a-Posten deterministisch — ersetzt ihn aber
**nicht** (s. u.).

## Was wurde gemacht

- **ATS-Linter (`ats_lint.py`)** — deterministisch, **offline**, keine LLM-API. Grundsatz wie
  critic/factground/jdparser/tailoring: **flaggt, ändert nichts** (read-only Scope). Prüft ein
  CV-`.docx` strukturell über **python-docx + OOXML** auf bekannte ATS-Parsing-Risiken.
  - **API:** `pruefe(doc)` (nimmt ein python-docx `Document`), `pruefe_datei(pfad)`,
    `hat_fehler(result) -> bool` (Gate), `report(pfad, result) -> str`.
  - **CLI:** `py -3.11 ats_lint.py <cv.docx> [--json]`; exit **1 bei FEHLER** / **0 sonst**.
- **⚠️ Run-Befehl global `py -3.11`** (braucht `python-docx` 1.2.0) — NICHT venv (dort nur jobspy).
  Reiht sich bei die `profile/`-Generatoren ein. Vor Lauf: `py -3.11 -c "import docx"`.
- **Prüf-Kategorien / Schweren (Quelle: agenten_roadmap.md C):**
  - **FEHLER:** Tabellen (`doc.tables` — Taleo scrambelt/Workday merged); mehrspaltiges Seitenlayout
    (`sectPr w:cols num>1`); Textbox/Shape (XML-Scan `txbxContent`/`v:textbox`); Kontaktdaten nur in
    Kopf-/Fußzeile (ATS ignoriert); kaum extrahierbarer Text (<200 Zeichen = Scan-/Bild-CV-Verdacht).
  - **WARNUNG:** eingebettete Bilder/Grafiken (inline_shapes + `wp:anchor`); keine Standard-
    Abschnittsüberschriften (Vokabular-Match); kein Plain-Text-Kontakt im Body.
  - Headings + Text werden auch aus **Tabellen-Zellen** gelesen (sonst False-Negatives bei
    tabellen-basierten CVs).
- **`verify_ats_lint.py`** — offline Selbsttest, **27 Checks**, exit 0: baut In-Memory-`.docx`-Fixtures
  je Zweig (Tabelle, Spalten via OxmlElement, Header-Kontakt, Wenig-Text, Bild via programmatisch
  erzeugtem 1×1-PNG, fehlende Headings, Heading-in-Zelle) + Schema-Stabilität.

## Test-Status

- **Offline:** `verify_ats_lint.py` **27/27** grün, exit 0; `ats_lint.py` + `verify_ats_lint.py`
  `py_compile`-sauber (global `py -3.11`).
  - Verify fand 1 **Fixture**-Bug (ungültiges 1×1-PNG-Base64-Literal → python-docx-Parser-Crash) →
    durch programmatisch (`zlib`/`struct`) erzeugtes, garantiert gültiges PNG ersetzt. Kein `ats_lint`-Bug.
- **Live (echte CVs, §3.6a):**
  - `Lebenslauf_Adam_Wzietek_v3.docx` (klassisch) → **26 Tabellen, ROT, exit 1**.
  - `Lebenslauf_Adam_Wzietek_v3_ATS.docx` (ATS-Pfad) → **0 Tabellen, 8 Std-Überschriften, Kontakt im
    Body, GRÜN, exit 0**. Der Linter trennt die beiden Generator-Pfade exakt.
- **Env-Smoke vorab (§3.11):** `py -3.11 -c "import docx"` → python-docx 1.2.0 OK.

## Was wurde verworfen / bewusst nicht gemacht

- **Echter ATS-Parser-Durchlauf ersetzt** — NICHT: §3.6a bleibt offen. Der Linter fängt nur die
  mechanisch erkennbaren, belegten Risiken vorab; er sagt, ob der CV ATS-robust *aufgebaut* ist, nicht
  wie ein konkretes ATS ihn real parst. Ehrlich im Docstring.
- **Auto-Reparatur des .docx** — außerhalb read-only Scope (flaggt nur). Single-Column-Erzeugung ist
  Sache des Generators (`build_cv_ats`).

## Public-Repo / PII

- `ats_lint.py` + `verify_ats_lint.py` = **Code, kein PII** → committed. Tests nur In-Memory-Fixtures.
  Live-Lauf gegen echte CVs (`profile/*.docx`, gitignored) nur **gelesen**, Output nicht eingecheckt.

## Known Issues / Offene Punkte

- **Textbox-Erkennung = XML-String-Scan** (`txbxContent`/`v:textbox`) — Heuristik, kein OOXML-Parse;
  ausreichend für die belegten Fälle.
- **`MIN_TEXT_LEN=200`** und Heading-Vokabular sind erste Setzung — an realen CVs nachschärfen.
- **Aus v7 offen:** `abschluss`-Meta-Soft-Edge in jdparser (kosmetisch) — als nächster Mini-Fix geplant.
- **Aus v2–v6 unverändert:** Google-Quelle 0 (JobSpy #302).

## Nächste sinnvolle Etappe

- **Mini-Fix:** jdparser `abschluss`-Meta (nachlaufendes Trigger-Wort abschneiden).
- **Generator-Integration (eigene Session):** jdparser + tailoring + ats_lint in den lokalen
  PII-Generator einhängen (Kostentreiber = Generator lesen).
- **E-C Text-Writer (eigene ~150k-Session):** CoverLetterWriter + CVTailoring-Text (konsumieren
  `parse()` + `abgleich()`).

## Verweis-Quellen

- Planungsgrundlage: `state/agenten_roadmap.md` (Abschnitt C)
- Vorgänger-State: `state/etappe_v8_state.md` (Tailoring) + `state/etappe_v7_state.md` (JDParser)
- Relevante User-Entscheide: 2026-06-28 (60k-Schnitt = ATS-Linter vorgezogen; „go" zur Freigabe)

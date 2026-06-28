# Etappe v14 — Quellordner-Extraktor + FactGrounding-Verdrahtung (+ Workflow-Härtung)

**Datum:** 2026-06-28 · **Persona:** Marek-Muster (Code-Etappe) · **Status:** ABGESCHLOSSEN, Commit auf „go"

## Was gemacht

### A) Quellordner-Extraktor (Deliverable, Code/kein-PII)
- **`extract_quellordner.py`** — deterministischer, OFFLINE, **READ-ONLY** Text-Extraktor für den
  persönlichen Bewerbungs-Quellordner (`C:\Users\0 - Eigene Dateien\Documents\Bewerbung`).
  - Formate: `.odt` (pur-Python zip/content.xml) · `.docx` (python-docx, inkl. Tabellenzellen) ·
    `.pdf` (pdfplumber) · `.doc` (**antiword**, Subprozess, Output cp1252 empirisch verifiziert).
  - API: `extrahiere(basis)→[(rel,text,status)]`, `corpus_text(basis)`, `schreibe_corpus(basis,out)`.
    CLI: `py -3.11 extract_quellordner.py <ordner> --out=… [--json]`.
  - Status-Klassen: OK / SKIP (`<20` Worte = Scan/leer, oder antiword fehlt) / ERR (korrupt, kein Crash).
  - **READ-ONLY hart:** schreibt nie in den Quellordner; `_guard_out_pfad` verweigert Output im
    Quellordner (`ValueError`). Bild/Video/PSD werden ignoriert (kein OCR = keine neue Dependency).
- **`verify_extract_quellordner.py`** — 21 Checks, synthetische TEMP-Fixtures (kein PII-Zugriff im Test):
  Format-Extraktion, SKIP/ERR/ignoriert, Konsolidierung, **READ-ONLY-Nachweis (Hash/Size/mtime)**,
  Output-Guard, Statistik, fehlender Ordner. **21/21 grün.**

### B) Live-Verdrahtung in FactGrounding (lokal/PII, gitignored — NICHT committed)
- `profile/gen_bewerbung_guetepruefer.py`: `lade_quellordner_corpus()` + Corpus als zusätzliche
  Quelle in `sammle_fakten(...)`. **Default-safe:** Corpus fehlt → exakt altes Verhalten.
- Corpus erzeugt: `profile/quellordner_corpus.txt` (293 760 Zeichen, **58/58 Dateien OK**) — gitignored (PII).

### C) Verifikation (Getestet, real auf Win11/py-3.11)
- `verify_all.py` **11/11** grün (neue Suite via `GLOBAL_PY_VERIFIES` → py-3.11, braucht docx/pdfplumber/fitz).
- E2E-Smoke (touchte keine echten CVs): Wiring trägt, **0 Regression** (echtes Anschreiben 0F/0W→0F/0W).
  **Wert belegt:** Corpus bringt +80 Firma-Tokens / +94 Akronyme / +187 Jahre; echter Fakt „Erweka GmbH"
  wird OHNE Corpus fälschlich als FEHLER geflaggt, MIT Corpus korrekt gegroundet.

### D) Workflow-Härtung (global, ~/.claude — separater Geltungsbereich, hier nur vermerkt)
Auslöser: 17%-Früh-Stopp (4. Session). deep-search-analyst + meta-auditor → **CLAUDE.md v4.32**:
§3.11 von Verbot auf **Default-Aktion=KETTEN + geschlossene 5-Bedingungen-Stopp-Liste + harte 60%**
(`deutlich`/`~` raus); SessionStart-Hook `print_etappe_gate.sh` **real gebaut+verdrahtet** (war
Schein-Sicherheit); brief-writer/etappe-tracker von „150k" auf UI-% ≥60 gesynct; §3.6(a)/(b) Hedges
geschärft. Memory `early-stop-17pct-failure`.

## Verworfen / bewusst nicht
- **OCR (tesseract):** nicht nötig — 58/58 textführende Dateien extrahieren sauber; Scans liegen
  zusätzlich als Text-PDF vor. Keine neue Dependency.
- **GEO-Tabelle erweitern in dieser Session:** Koordinaten aus dem Gedächtnis = Raten (§3.10-Hazard) →
  abgelehnt. Nur mit authoritativer Quelle (WebSearch/Geo-Datensatz) sauber machbar.
- **validate_state_overwrite.py verdrahten:** User-Entscheid „vorerst lassen".

## Offene Punkte / nächste Posten
- GEO-Tabelle erweitern — **nur mit authoritativer Koordinaten-Quelle** (kein Memory-Raten).
- `!ETAPPE-GATE`: service.bund.de-RSS-Quelle (Wolf, eigene Session, Netz-Posten).
- §3.6(a)-Altlast: echter externer ATS-Parser-Durchlauf des CV-Outputs (User-Aktion).
- B-Corpus könnte `build_bewerber`-Stammdaten / firmenhistorie deterministisch anreichern (PII/lokal).

# Etappe v8 — State nach Abschluss (Agenten-Roadmap E-C, vorgezogener Kern von Teil 2: TailoringAgent / GapAnalysis)

**Datum:** 2026-06-28
**ZIP:** (optional, auf Freigabe; `make_backup.py` nicht zwingend gelaufen)
**Status:** ✅ funktionsfähig + offline verifiziert (30/30) + Live-CLI-Smoke (Report/exit-Gate)
**Persona:** Marek (Code-Etappe). Grundlage: `state/agenten_roadmap.md` Abschnitt A.4 (CVTailoring) — Entscheidungs-Kern.

---

## Scope-Schnitt vorab (User-Entscheid 2026-06-28)

Session-Budget für diese Etappe = **80k** (statt Default 150k). Aus den E-C-Folge-Posten den
**deterministischen Kern von CVTailoring** vorgezogen — den *Entscheidungs*-Teil (was betonen / was
fehlt), **nicht** die Text-Generierung. Die eigentlichen Text-Writer (CoverLetterWriter + CVTailoring-
Text) bleiben das volle ~150k-Folgepaket.

## Was wurde gemacht

- **TailoringAgent (`tailoring.py`)** — deterministisch, **offline**, keine LLM-API. Grundsatz wie
  critic/factground/jdparser: **flaggt, ändert nichts** (read-only Scope). Brücke JDParser ↔ CV.
  - **API:** `abgleich(jd_result, cv_result)` (nimmt zwei `jdparser.parse()`-Ergebnisse),
    `abgleich_texte(anzeige_text, cv_text)` (Bequemlichkeit), `hat_luecke(result) -> bool`
    (Pipeline-Gate), `report(jd_quelle, cv_quelle, result) -> str`.
  - **CLI:** `python tailoring.py <anzeige-datei> <cv-datei> [--json]`; exit **1 bei fehlendem
    MUSS-Keyword** (Lücke) / **0 sonst**. Kein jobspy nötig → auch global `py -3.11`.
  - **Methode:** beide Seiten mit demselben `jdparser.parse()` / `KEYWORD_KATALOG` analysieren →
    Kanon-Begriffe vergleichbar (kein Schreibweisen-Drift, Umlaut-Folding greift beidseitig). Bezug =
    immer die **Anzeige**.
- **Ausgabe (`abgleich`):** `vorhanden` (vom CV gedeckte Anzeigen-Keywords → im Brief betonen),
  `fehlend` (+ nach `kategorien` gruppiert), `muss_fehlt` (vorrangig — MUSS der Anzeige nicht im CV),
  `kann_fehlt` (optional; muss hat Vorrang, disjunkt), `stats` inkl. `abdeckung_prozent`
  (Division-by-zero-sicher).
- **`verify_tailoring.py`** — offline Selbsttest, **30 Checks**, exit 0: vorhanden/fehlend disjunkt,
  Muss/Kann-Priorität + Teilmengen-Invarianten, Abdeckung korrekt gerechnet + Bereich 0..100,
  Voll-Deckung → keine Lücke, Kategorien decken genau `fehlend`, Negativ/leer-Robustheit,
  `abgleich(parse,parse) == abgleich_texte`, Schema-Stabilität.

## Test-Status

- **Offline:** `verify_tailoring.py` **30/30** grün, exit 0; `tailoring.py` + `verify_tailoring.py`
  `py_compile`-sauber (venv-Python).
- **Live-CLI-Smoke (§3.6a):** Temp-Anzeige↔Temp-CV → 38% Abdeckung, MUSS-Lücke „Fräsen" korrekt
  geflaggt (Umlaut-Folding live: Fräsen/Schweißen/WIG sauber), exit 1.
- **Env-Smoke vorab (§3.11):** v7-Verifies grün (Vorbedingung; jdparser ist Abhängigkeit).

## Was wurde verworfen / bewusst nicht gemacht

- **Text-Generierung (Writer)** in dieser Etappe NICHT — nur der Entscheidungs-Kern. Eigene
  Folge-Etappe.
- **Synonym-/Semantik-Match außerhalb `KEYWORD_KATALOG`** bewusst NICHT — deterministisch nicht
  leistbar; ehrlich im Docstring vermerkt. Katalog erweitern statt Schein-Match.
- **Einhängen in den lokalen PII-Generator** = separater Schritt (nicht Teil dieser Etappe).

## Public-Repo / PII

- `tailoring.py` + `verify_tailoring.py` = **Code, kein PII** → committed. Tests nur gegen synthetische
  Fixtures + Temp-Dateien außerhalb des Repos. Echter CV-Abgleich = lokal (`tailoring.py <anzeige>
  profile\Lebenslauf_*.md`), nicht eingecheckt.

## Known Issues / Offene Punkte

- **Katalog-Abhängigkeit:** Match-Qualität = Qualität von `jdparser.KEYWORD_KATALOG` (gemeinsame
  Single-Source-of-Truth — Erweiterung wirkt auf beide Seiten zugleich).
- **Aus v7 offen:** `abschluss`-Meta-Soft-Edge in jdparser (kosmetisch).
- **Aus v2–v6 unverändert:** Google-Quelle 0 (JobSpy #302); echter ATS-Parser-Durchlauf offen (§3.6a).

## Nächste sinnvolle Etappe

- **E-C Teil 3 — ATS-Linter (`ats_lint.py`, Marek):** deterministische ATS-Risiko-Prüfung des
  generierten CV-`.docx` (Tabellen/Mehrspaltig/Header-Footer-Kontakt/Nicht-Standard-Überschriften) —
  adressiert §3.6a. python-docx → global `py -3.11`. Grundlage `state/agenten_roadmap.md` Abschnitt C.
- **E-C Teil 2 (Text-Writer):** CoverLetterWriter + CVTailoring-Text (konsumieren `parse()` +
  `abgleich()`), volles ~150k-Paket, eigene Session.

## Verweis-Quellen

- Planungsgrundlage: `state/agenten_roadmap.md` (Abschnitt A.4)
- Vorgänger-State: `state/etappe_v7_state.md` (JDParser — direkte Abhängigkeit)
- Relevante User-Entscheide: 2026-06-28 (80k-Schnitt = GapAnalysis-Kern vorgezogen; „go" zur Freigabe)

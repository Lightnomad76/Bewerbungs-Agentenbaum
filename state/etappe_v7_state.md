# Etappe v7 — State nach Abschluss (Agenten-Roadmap E-C, Teil 1: JDParserAgent)

**Datum:** 2026-06-28
**ZIP:** (optional, auf Freigabe; `make_backup.py` nicht zwingend gelaufen)
**Status:** ✅ funktionsfähig + offline verifiziert (38/38) + Live-CLI-Smoke (Report/JSON/exit 0)
**Persona:** Marek (Code-Etappe). Grundlage: `state/agenten_roadmap.md` Abschnitt A.3 (JDParser/KeywordExtractor).

---

## Scope-Schnitt vorab (User-Entscheid 2026-06-28)

E-C bündelt laut Roadmap drei Brocken (JDParser + getrennte Writer + ATS-Zwei-Pfad) — zu groß für
eine ~150k-Session. **Entscheidung (User):** nur **JDParserAgent** in dieser Etappe (Fundament; Writer
+ ATS hängen an seinem Output). Persona **Marek**. Getrennte Writer + ATS-Generalisierung bleiben
bewusst eigene Folge-Etappen.

## Was wurde gemacht

- **JDParserAgent (`jdparser.py`)** — deterministisch, **offline**, keine LLM-API. Grundsatz wie
  critic/factground: **extrahiert, ändert nichts** (read-only Scope). Erfindet keine Anforderung —
  findet nur, was wörtlich in der Anzeige steht.
  - **API:** `parse(text) -> {keywords, anforderungen, abschnitte, meta, stats}`;
    `keywords_flach(result) -> list` (flache, dedup-/sortierte ATS-Keyword-Liste fürs Tailoring);
    `report(quelle, result) -> str`.
  - **CLI:** `.\.venv\Scripts\python.exe jdparser.py <anzeige-datei> [--json]`; exit 0
    (kein jobspy nötig → läuft auch global `py -3.11`).
- **Extraktion (kuratiertes Domänen-Wörterbuch `KEYWORD_KATALOG`, erweiterbar):**
  - Kategorien: `fertigung` · `mess_qs` · `steuerung_it` · `normen` · `soft` · `sprachen`
    (Industriemechaniker/QS + allgemein-technisch). Output = **Kanon-Begriff**, nicht die
    Anzeigen-Schreibweise.
  - **Muss/Kann-Klassifikation** über zeilenbezogene Trigger: *zwingend/Voraussetzung/erforderlich/
    vorausgesetzt* → **Muss**; *von Vorteil/wünschenswert/idealerweise* → **Kann**; ohne Trigger =
    neutral (nicht gelistet). **Muss hat Vorrang** (disjunkt).
  - **Abschnitts-Segmentierung** nach deutschen Überschriften (Aufgaben / Profil / Angebot) →
    Bullet-Zeilen (Umlaute im Output erhalten).
  - **Meta:** `titel` (Zeile mit (m/w/d)), `ansprechpartner` (Herr/Frau Name — speist Critics
    „Anrede mit Namen"-Regel), `abschluss`, `schicht`-Flag, `reise`-Flag.
- **Robustheit:** **Umlaut-Folding** (`ä↔ae / ö↔oe / ü↔ue / ß↔ss`) auf Text **und** Inhaltsmuster
  (Anzeigen schreiben beides) — Meta-Capture (Namen) läuft bewusst auf dem Original (Umlaute bleiben);
  Wortgrenzen bei Akronymen (kein „Sappige"→SAP); Markdown-Toleranz (`_clean`); leerer/fachfreier Text
  → 0 Keywords (kein False-Positive).
- **`verify_jdparser.py`** — offline Selbsttest, **38 Checks**, exit 0: Extraktion (beide Schreibweisen),
  Kategorisierung+Sortierung, Muss/Kann inkl. neutral, Abschnitte+Bullet-Erhalt, Meta-Felder,
  Negativ/Robustheit, Schema-Stabilität, zweite QS/Normen-Fixture.

## Test-Status

- **Offline:** `verify_jdparser.py` **38/38** grün, exit 0; `jdparser.py` + `verify_jdparser.py`
  `py_compile`-sauber (venv-Python).
- **Live-CLI-Smoke (§3.6a):** Temp-Anzeige (Zerspanungsmechaniker) → Report + `--json` + exit 0;
  „Frau Dr. Müller" sauber gezogen, Muss/Kann/Abschnitte plausibel.
- **Env-Smoke vorab (§3.11):** `verify_engine.py` + `verify_match.py` + `verify_critic.py`
  + `verify_factground.py` alle exit 0 (venv-Python).

## Was wurde verworfen / bewusst nicht gemacht

- **Getrennte Writer + ATS-Generalisierung** in dieser Etappe verworfen (Budget-Schnitt; eigene
  Folge-Etappen).
- **LLM-/Semantik-Extraktion** außerhalb Scope (offline/gratis/deterministisch).
- **Erkennung katalog-fremder, frei formulierter Anforderungen** bewusst NICHT — deterministisch
  nicht leistbar; ehrlich im Docstring vermerkt statt Schein-Vollständigkeit. Wörterbuch ist der
  Erweiterungs-Hebel.
- **Einhängen in den lokalen PII-Generator** (wie bei critic/factground) = separater Schritt nach
  Bedarf, nicht Teil dieser Etappe.

## Public-Repo / PII

- `jdparser.py` + `verify_jdparser.py` = **Code, kein PII** → committed. Kein echter Anzeigentext im
  Repo (Test nur gegen synthetische Fixtures + Temp-Datei außerhalb des Repos).

## Known Issues / Offene Punkte

- **`abschluss`-Meta zieht manchmal ein nachlaufendes Wort mit** (z. B. „Zerspanungsmechaniker
  erforderlich") — kosmetisch, nicht funktional; bei Bedarf Capture nachschärfen.
- **Wörterbuch-Tuning:** `KEYWORD_KATALOG` ist erste kuratierte Setzung (Industriemechaniker/QS) —
  an realen Anzeigen erweitern; andere Branche = Kategorie/Einträge ergänzen.
- **Aus v2–v6 unverändert:** Google-Quelle 0 Treffer (JobSpy-Upstream #302); echter ATS-Parser-
  Durchlauf des CV-Outputs offen (§3.6a-Smoke, User-Aktion).

## Nächste sinnvolle Etappe (Vorschlag)

- **E-C Teil 2 (Marek/Wolf, eigene frische Session):** getrennte Writer (CoverLetterWriter +
  CVTailoring) — konsumieren `parse()`-Output (Muss/Kann + ATS-Keywords). Danach **Teil 3:**
  ATS-Zwei-Pfad fest in den ReportAgent (Single-Column generalisieren). Grundlage
  `state/agenten_roadmap.md` A.4 + C.

## Verweis-Quellen

- Planungsgrundlage: `state/agenten_roadmap.md` (Abschnitt A.3)
- Vorgänger-State: `state/etappe_v6_state.md` (crewai-Fix/venv) + `state/etappe_v5_state.md` (FactGrounding)
- Relevante User-Entscheide: 2026-06-28 (E-C-Schnitt = nur JDParser, Marek-Hut; „go" zur Freigabe)

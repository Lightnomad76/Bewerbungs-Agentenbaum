# Etappe v10 — State nach Abschluss (Agenten-Roadmap E-C Text-Writer, Sub-1: CoverLetterWriter)

**Datum:** 2026-06-28
**ZIP:** (optional, auf Freigabe; `make_backup.py` nicht zwingend gelaufen)
**Status:** ✅ funktionsfähig + offline verifiziert (28/28, inkl. critic+factground-Gate) + Live-CLI-Smoke
**Persona:** Marek (Code-Etappe). Grundlage: `state/agenten_roadmap.md` A.4 + B; Brief im HANDOFF.

---

## Gating-Entscheidung (User 2026-06-28)

Text-Writer = **deterministischer Default**, KEINE LLM-API. Der API-Pfad bleibt ein späterer,
bewusster Schalter (dann Fact-Grounding Pflicht). Damit ist diese Etappe Mareks Revier (deterministisch/
offline), nicht Wolfs (API/Backend).

## Split (User-Brief)

Text-Writer ist der größte E-C-Brocken (~150k) → gesplittet. **Diese Etappe = Sub-1: CoverLetterWriter.**
**Sub-2: CVTailoring** (CV-Bullets nach Anzeigen-Keywords umsortieren/gewichten) bleibt offen.

## Was wurde gemacht

- **CoverLetterWriterAgent (`coverletter.py`)** — deterministisch, **offline**, keine API. Ersetzt den
  früher hartkodierten Brieftext durch einen **JD-getriebenen** Writer; baut das Anschreiben aus
  Bausteinen (Kopf/Betreff/Anrede/Einstieg/Eignung/Anzeigen-Bezug/Schluss/Gruß).
  - **API:** `schreibe(bewerber, jd_result, abgleich_result, ort=, datum=) -> str` (komponierbar);
    `schreibe_fuer_anzeige(bewerber, anzeige_text) -> str` (Bequemlichkeit: parse + abgleich + schreibe).
  - **CLI:** `python coverletter.py <anzeige-datei> <bewerber.json> [--json]`. Kein jobspy → auch venv.
  - **Inputs:** `jdparser.parse()` (Titel→Betreff ohne (m/w/d), Ansprechpartner→Anrede mit Name,
    Aufgaben→konkreter Bezug) + `tailoring.abgleich()` (`vorhanden`→betonen, `muss_fehlt`→**verschweigen
    statt erfinden**).
- **Read-only Geist / Ehrlichkeit:** der Writer nennt nur die im CV **gedeckten** Anzeigen-Keywords;
  fehlende MUSS-Keywords werden NICHT behauptet. Ziel-Firmenname bewusst **nicht** genannt (vermeidet
  factground-False-Positive auf eine Firma-mit-Rechtsform, die nicht in den Bewerber-Stammdaten steht).
- **Stil (agenten_roadmap.md B):** keine Floskel-Blacklist-Treffer, 7-Sekunden-Einstieg (kein
  Aufwärmer), Anrede mit Namen wenn bekannt, DIN-5008-Pflichtfelder (Betreff/Datum/Gruß ohne Komma/
  Kontakt Plain-Text). Fett-/Layout-Pflichten bleiben Sache des docx-Generators — Writer liefert
  strukturierten Plain-Text.

## Akzeptanz-Gate (mechanisch geprüft, nicht behauptet)

Writer-Output besteht **`critic.pruefe()` = 0 FEHLER** UND **`factground.pruefe(text, fakten)` = 0
FEHLER** — beide im Verify verdrahtet. Das ist die belegte Qualitäts-Messlatte der Writer aus dem Brief.

## Test-Status

- **Offline:** `verify_coverletter.py` **28/28** grün, exit 0; `coverletter.py` + `verify_coverletter.py`
  `py_compile`-sauber (venv-Python).
- Geprüft: Pflicht-/Struktur-Felder, **critic-Gate 0 FEHLER**, **factground-Gate 0 FEHLER**, JD-Steuerung
  (Anrede mit Name, Betreff aus Titel, vorhandene Keywords + konkrete Aufgabe genannt), **Ehrlichkeit**
  (fehlendes MUSS „Fräsen" nicht erfunden), Länge 120–500, Determinismus (gleiche Inputs → identisch),
  Anrede-Fallback + Herr/Frau-Beugung.
- **Live-CLI-Smoke (§3.6a):** Temp-Anzeige + Bewerber-JSON → vollständiger, gate-konformer Brief, exit 0.

## Was wurde verworfen / bewusst nicht gemacht

- **LLM-API** (Gating-Default deterministisch). Späterer bewusster Schalter.
- **CVTailoring-Text** (= Sub-2, eigene Etappe).
- **Ziel-Firmenname im Brief** bewusst weggelassen (Grounding-Konflikt) — nachrüstbar, indem der
  factground-Check zusätzlich mit dem Anzeigentext als Wahrheitsquelle gefüttert wird.

## Public-Repo / PII

- `coverletter.py` + `verify_coverletter.py` = **Code, kein PII** → committed. Tests nur synthetische
  Fixtures + Temp-Dateien außerhalb des Repos. Echte Bewerber-Daten = lokal (`<bewerber.json>`), nie eingecheckt.

## Known Issues / Offene Punkte

- **Keyword-Wiederholung:** die gedeckten Keywords erscheinen in zwei Absätzen → wirkt etwas robotisch
  (Grenze deterministischer Baustein-Assemblierung). Qualitätskante, kein Defekt — Iteration/Variation
  oder der spätere API-Pfad adressiert das.
- **Nur erste Station** wird zur Eignungs-Bindung genutzt (`stationen[0]`).
- **Bewerber-Schema** (`name/email/telefon/ort/beruf/erfahrung/stationen[firma/zeitraum/taetigkeiten/
  skills]`) ist gesetzt; an echte Stammdaten anpassen.

## Nächste sinnvolle Etappe

- **Sub-2: CVTailoringAgent (Marek):** CV-Bullets/Stationen nach `abgleich.vorhanden` + Anzeigen-Keywords
  umsortieren/gewichten (KEINE erfundenen Inhalte). Konsumiert `parse()` + `abgleich()`; eigenes `verify_*.py`.
- **Danach: Generator-Integration** (jdparser/tailoring/ats_lint/coverletter in `gen_bewerbung_guetepruefer.py`).
- **Optional/Wolf:** natives Xing/Jobware-Scraping.

## Verweis-Quellen

- Planungsgrundlage: `state/agenten_roadmap.md` (A.4 + B) + Text-Writer-Brief im HANDOFF
- Vorgänger-State: `state/etappe_v8_state.md` (Tailoring) + `state/etappe_v7_state.md` (JDParser)
- Relevante User-Entscheide: 2026-06-28 (Gating = deterministisch; „starte Text-Writer"; „go" zur Freigabe)

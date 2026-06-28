# Etappe v11 — State nach Abschluss (Agenten-Roadmap E-C Text-Writer, Sub-2: CVTailoring)

**Datum:** 2026-06-28
**ZIP:** (optional, auf Freigabe; `make_backup.py` nicht zwingend gelaufen)
**Status:** ✅ funktionsfähig + offline verifiziert (43/43) + Live-CLI-Smoke
**Persona:** Marek (Code-Etappe). Grundlage: `state/agenten_roadmap.md` A.4 + B; Brief im HANDOFF.

---

## Gating-Entscheidung (unverändert, User 2026-06-28)

Text-Writer = **deterministischer Default**, KEINE LLM-API (wie Sub-1). API-Pfad bleibt späterer,
bewusster Schalter (dann Fact-Grounding Pflicht).

## Was wurde gemacht

- **CVTailoringAgent (`cvtailoring.py`)** — deterministisch, offline, keine API. Gegenstück zum
  CoverLetterWriter: ordnet die **bestehenden** CV-Stationen + -Bullets nach Anzeigen-Relevanz
  um/gewichtet. **Erfindet/löscht nichts** (read-only Geist).
  - **API:** `priorisiere(bewerber, jd_result, abgleich_result) -> {stationen, weggelassen,
    relevant_keywords, muss_fehlt, stats}`; `priorisiere_fuer_anzeige(bewerber, anzeige_text)`
    (parse + abgleich + priorisiere).
  - **CLI:** `python cvtailoring.py <anzeige> <bewerber.json> [--json]`, exit 0 (Sortier-Tool, kein Gate
    — die go/no-go-Lücke entscheidet `tailoring.hat_luecke`). Kein jobspy → auch global `py -3.11`.
  - **Score je Bullet** = gewichtete Treffer der Anzeigen-Keywords, die **im CV gedeckt** sind
    (`abgleich.vorhanden`): Muss=3 > Kann=2 > neutral=1. Stations-Score = Bullets + relevante Skills.
  - **Sortierung:** Stationen + Bullets nach Score desc, **Tie-Break = Original-Reihenfolge**
    (`original_index` im Output erhalten → re-chronologisierbar).
  - **`weggelassen`** = Score-0-Bullets je Station (Vorschlag wegzulassen) — **dokumentiert, nicht
    aus den Stammdaten entfernt**.
- **Bewerber-Schema** identisch zu `coverletter.py` (Single-Source; `_bewerber_als_text` importiert).

## Akzeptanz / Ehrlichkeit (mechanisch geprüft)

- **Read-only-Invariante:** Output-Bullets ≡ Input-Bullets je Station (nichts erfunden/verloren) — im
  Verify geprüft. CVTailoring erzeugt **keinen neuen Text** → kein Halluzinations-Risiko → das
  critic+factground-Gate von Sub-1 ist hier durch diese Invariante **ersetzt**, nicht weggelassen.
- **`muss_fehlt`** (z. B. `Zerspanung`) wird **durchgereicht, nicht aufgefüllt** — echte Lücke sichtbar;
  fehlendes MUSS nie als gedeckt behauptet.

## Test-Status

- **Offline:** `verify_cvtailoring.py` **43/43** grün, exit 0; `py_compile` sauber (venv).
- Geprüft: Schema, abgleich-Durchreichung, Read-only-Invariante, Scoring Muss>Kann>neutral>0,
  Bullet-/Stations-Sortierung + Tie-Break, weggelassen = exakt Score-0, skills_relevant, Stats-
  Konsistenz, Determinismus (inkl. Bequemlichkeits-Pfad), Edge-Cases (leere Anzeige/Stationen/Bullets).
- **Live-CLI-Smoke (§3.6a):** Temp-Anzeige + Bewerber-JSON → SAMSON (Score 9) vor Müller (0), CNC-Bullet
  oben, Schweißen/WIG + Büroarbeiten weggelassen, Zerspanung als MUSS-Lücke geflaggt, exit 0.
- **Env-Smoke vorab (§3.11):** alle 7 venv-Verifies exit 0.

## Was wurde verworfen / bewusst nicht gemacht

- **LLM-API** (Gating-Default). Späterer Schalter.
- **Echtes getailortes `.docx`-Rendering** — bewusst NICHT: cvtailoring liefert die Sortier-/Auswahl-
  *Entscheidung*; das Dokument-Rendering ist Sache der Generator-Integration (`build_cv`/`build_cv_ats`).
- **Synonym-/Semantik-Match außerhalb `KEYWORD_KATALOG`** — deterministisch nicht leistbar (wie tailoring).

## Public-Repo / PII

- `cvtailoring.py` + `verify_cvtailoring.py` = **Code, kein PII** → committed. Tests nur synthetische
  Fixtures + Temp-Dateien außerhalb des Repos. Echte Bewerber-Daten = lokal, nie eingecheckt.

## Known Issues / Offene Punkte

- **Chronologie-Kante:** Stationen werden nach **Relevanz** statt strikt antichronologisch sortiert.
  `original_index` ist erhalten → der Generator kann re-chronologisieren oder die Relevanz-Ordnung
  übernehmen. Bewusste Design-Entscheidung (Tailoring-Sicht), kein Defekt.
- **Skills-Score** ist additiv zur Stations-Gewichtung (kann eine skill-lastige Station hochziehen).
- **Bewerber-Schema** an echte Stammdaten anpassen (wie coverletter).

## Nächste sinnvolle Etappe

- **Generator-Integration** (in dieser Session gekettet, 2026-06-28): jdparser/tailoring/coverletter/
  cvtailoring in `profile/gen_bewerbung_guetepruefer.py` einhängen (lokal/PII).
- **Optional/Wolf:** natives Xing/Jobware-Scraping.

## Verweis-Quellen

- Planungsgrundlage: `state/agenten_roadmap.md` (A.4 + B) + Text-Writer-Brief im HANDOFF
- Vorgänger-State: `state/etappe_v10_state.md` (CoverLetter) + `etappe_v8_state.md` (Tailoring)
- Relevante User-Entscheide: 2026-06-28 (Gating deterministisch; „v11 commit + Generator-Integration
  ketten"; „150k = Ziel füllen, kleine bündeln" — Per-Session-Override + Dauerhaft-Fix beauftragt)

# Etappe v21 — Tailoring-Signal geschärft (Realtest CMBlu) + Brief/CV-Konsistenz

**Datum:** 2026-07-01 · **Persona:** Marek (Code/Scoring) · **Status:** ABGESCHLOSSEN + COMMITTED (`10f68e1`, kein PII)
**Auslöser:** End-to-End-Test an einer **echten Indeed-Anzeige** (CMBlu Industriemechaniker) — deckte drei
konkrete Schwächen auf. Alle Fixes **evidenzbasiert** (Begriffe standen wörtlich in der realen Anzeige).

## Was geändert wurde (3 Fixes)

### 1. `coverletter.py` — Belegstation = die für die Anzeige RELEVANTESTE Station
- Neu `_belegstation(bewerber, jd_result, abgleich_result, stationen)`: wählt die Belegstation fürs
  Anschreiben über **dieselbe Rangfolge wie `cvtailoring`** (`priorisiere(...).stationen[0]`), statt stur
  die jüngste `stationen[0]`.
- **Behebt den Widerspruch:** vorher zitierte der Brief die jüngste Station, die das CV-Tailoring evtl.
  gerade nach unten sortiert hatte → Brief und CV liefen auseinander.
- **Lazy import** (`from cvtailoring import priorisiere` in der Funktion) bricht den Modul-Zyklus
  (`cvtailoring` importiert `coverletter`). Jede Störung → `except` → alter, sicherer Pfad.
- **Tie-Break = Original-Reihenfolge** → ohne Relevanz-Signal fällt es auf die jüngste Station zurück
  (= altes Verhalten, **rückwärtskompatibel**).

### 2. `jdparser.py` — Katalog-Erweiterung + Recall-Bug
- **Recall-Bug behoben:** das Adjektiv „hydraulisch" traf den alten Regex `hydraulik` **nicht** (fehlendes
  `k`). Jetzt `hydraulik|hydraulisch` (analog `pneumatik|pneumatisch`).
- **Neue Terme** (alle wörtlich in der echten Anzeige, Kategorie `fertigung`): `Prototypenbau`
  (`prototyp(?:en|enbau)?`), `Sondermaschinenbau`, `Werkzeugmaschine`.
- Nutzen doppelt: „Prototyp"/„Hydraulik" matchen **zusätzlich Adams Siemens-/IAV-Stationen** → besseres
  CV↔JD-Signal, nicht nur Anzeigen-Recall.

### 3. `coverletter.py` — Einstieg führt mit Fach-Skills, Sprachen zuletzt
- Neu `_fachlich_zuerst(vorhanden, jd_result)` + `_KAT_PRIO` (fertigung/mess_qs/steuerung_it=0, normen=1,
  soft=2, **sprachen=3**): sortiert `abgleich.vorhanden` nach Kategorie-Priorität.
- **Grund:** `tailoring.abgleich` liefert `vorhanden` **alphabetisch** → der Einstieg führte mit „Deutsch,
  Englisch" (bei einer Technik-Stelle schwach). Muss/Kann-Gewicht taugt hier **nicht** — reale Anzeigen
  triggern oft nur die Sprachen als „kann", die Fach-Skills bleiben neutral.
- `sorted` ist **stabil** → innerhalb gleicher Priorität bleibt die alphabetische Eingangsreihenfolge.

## Verifikation (§3.5)
- `verify_jdparser.py` +Checks [5d] — deckt Recall-Fix + neue Terme ab.
- `verify_coverletter.py` +Checks [11][12] — deckt Belegstation-Wahl + Fach-zuerst-Reihenfolge ab.
- **`verify_all.py` 13/13 grün.** Kein PII.

## Realtest-Beleg (§3.6a — echte Operation lief)
- End-to-End gegen die echte Indeed-Anzeige **CMBlu Industriemechaniker**: die drei Symptome (falsche
  Belegstation, verpasstes Hydraulik-/Prototypen-Vokabular, Sprachen-lastiger Einstieg) waren real
  beobachtet und sind nach dem Fix behoben.

## Committed (kein PII)
`coverletter.py`, `jdparser.py`, `verify_coverletter.py`, `verify_jdparser.py` (Commit `10f68e1`).
Generator/CV/Anschreiben-Artefakte bleiben lokal/gitignored (PII).

## Offen / nächste Posten
- Autonome deterministische Roadmap weiterhin **erschöpft** (Stand v20 unverändert). Rest braucht
  User-Input oder ist groß/Netz: konkrete Anzeige tailoren (braucht User-URL) · realer externer
  ATS-Parser (§3.6a-Altlast, User-Aktion) · nativer Xing/Jobware-Scraper (Wolf — aktuell als
  undurchführbar eingestuft, SPA/Login).
- KEINE laufenden API-Kosten (Memory `no-ongoing-api-cost`).

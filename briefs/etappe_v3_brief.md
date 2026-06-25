# Kontext-Brief — Etappe 3: Lokale HTML-Web-UI (edyta)

**Für:** frischen Chat, GUI-Hut (edyta). **Ersetzt** das Durchscrollen der Etappe-1/2-Historie.
**Erstellt:** 2026-06-25 (Ende Etappe 2). Quelle: `state/etappe_v2_state.md`, `HANDOFF.md`.

---

## Ziel der Etappe

Statisches, **lokales HTML/JS** im Projektordner, das die gescorten Treffer aus
`treffer_v2.json` lädt und **sortiert + filterbar** anzeigt. Read-only, login-frei, kein Build-Tool
nötig (Doppelklick bzw. simpler Server). Kein Bewerben/keine Aktion — nur Sichten + Priorisieren.

## Datenquelle: `treffer_v2.json` (der UI-Vertrag)

Schema `{ meta, treffer[] }`, von der Engine garantiert (S1: Kernschema per `reindex` erzwungen):

- **`meta`**: `erzeugt` (ISO-UTC), `profil`, `standort`, `quellen[]`, `such_titel[]`, `anzahl`, `version` ("v2").
- **`treffer[]`** — bereits **sortiert** (vollständige zuerst, dann Score absteigend). Jeder Eintrag:
  - Kernfelder: `title`, `company`, `location`, `job_url`, `date_posted`, `min_amount`, `max_amount`,
    `description`, `such_titel` (**Liste** — welche Suchbegriffe den Treffer fanden).
  - **`match`**: `score` (int, real ~30..0, **negativ möglich**), `ko` (bool), `muss_treffer[]`,
    `muss_fehlt[]`, `kann_treffer[]`, `ausschluss_treffer[]`, `gehalt_unter_min` (bool).

**Null-Toleranz Pflicht:** `date_posted`, `min_amount`, `max_amount`, `description` können `null` sein
(NaN/NaT → null serialisiert). UI muss das sauber darstellen, nicht "null"/"NaN" zeigen.

## Erkenntnisse aus Etappe 2 (fürs UI-Design relevant — nicht neu aufrollen)

- **`kann_treffer` ist das Hauptsignal.** `skills_muss` ist bewusst **leer** (das Profil deckt zwei
  Berufsrichtungen ab — Industriemechanik UND QS —, ein UND-K.o. würde immer eine Richtung killen).
  → Folge: aktuell **alle `ko=False`**. UI muss den leeren-ko-Fall vertragen; ko-Badge nur zeigen wenn true.
- **`kann_treffer` als Chips/Tags** prominent zeigen (das macht den Score erklärbar). `ausschluss_treffer`
  und `gehalt_unter_min` als Warn-Badges.
- **Score erklärbar machen:** Nutzer soll sehen, *warum* ein Treffer oben/unten steht (Skill-Chips +
  Warn-Badges genügen; kein Formel-Dump nötig).
- **Quellen-Realität:** Google liefert aktuell 0 (JobSpy-seitig) → alle Treffer sind Indeed. `meta.quellen`
  trotzdem generisch anzeigen.
- **`such_titel` (Liste)** klein mitanzeigen (zeigt, über welche Suche der Job kam).
- Live-Stand: 35 Treffer, score 30..0, 0 False-Positive-Ausschlüsse (Ausschluss wird **nur im Titel**
  geprüft — das ist Engine-Logik, für die UI nur insofern relevant, als `ausschluss_treffer` selten/leer ist).

## Technischer Constraint — lokales Laden (WICHTIG)

Browser blockt `fetch()`/`XMLHttpRequest` von `file://` (CORS) → JSON lässt sich beim Doppelklick **nicht**
per fetch laden. Zwei Wege (edyta entscheidet):
1. **JS-Bridge (robust für Doppelklick):** Engine zusätzlich `treffer_v2.js` schreiben lassen mit
   `window.TREFFER = {…}`; HTML bindet sie per `<script src>` ein. → kein Server nötig.
   (Kleiner Engine-Zusatz in `schreibe_report` — mit Marek/in der Etappe abstimmen.)
2. **Lokaler Server:** `py -3.11 -m http.server` im Projektordner, dann `fetch('treffer_v2.json')`.
   Einfacher Code, aber Nutzer muss den Server starten (ggf. `start_ui.bat`).

## Dev-Host-Constraints (aus globaler CLAUDE.md §6)

- **Display:** 3440×1440 **Ultrawide @ 100 %** (kein DPI-Scaling) → Layout darf breit sein; nicht für
  schmale Viewports overfitten. Dunkel/hell egal, edytas Urteil.
- **Screenshot-Overlay defekt (§6.5):** **keine** Screenshots zur Diagnose anfordern — textlich lösen
  (Konsolen-Output/DOM/Konfig abfragen). Geteilte Screenshots trotz Verdeckung diagnostizieren.
- **Sprache:** Deutsch, Fachbegriffe Englisch lassen.

## Scope / Caveats (hart, nicht aufweichen)

- Read-only, login-frei. UI zeigt + filtert, mehr nicht. Link auf `job_url` öffnet die Original-Anzeige.
- **Public Repo:** `treffer_v2.json/.csv` enthalten **echte Treffer** (PII-nah) → gitignored halten,
  NIE pushen. Eine etwaige `treffer_v2.js`-Bridge ebenfalls gitignoren. Nur UI-Code (html/js/css) committen.

## Vorgeschlagene UI-Bausteine (edyta entscheidet Design)

- Kopf: `meta` (Profil/Standort/Quellen/Anzahl/erzeugt-Datum).
- Controls: Sortierung (Score/Datum), Min-Score-Slider, Toggle „Ausschluss-Treffer ausblenden",
  Quellen-/Such-Titel-Filter, Freitext-Suche.
- Treffer-Karte: Titel→`job_url`-Link, Firma · Ort, Datum, Gehalt (min–max, null→„k.A."),
  `kann_treffer`-Chips, Warn-Badges (ausschluss/gehalt/ko), Beschreibung ein-/ausklappbar.

## Workflow im Etappe-3-Chat

1. Lesen: diesen Brief + `HANDOFF.md` + `state/etappe_v2_state.md`.
2. **Environment-Smoke (§3.11):** `py -3.11 verify_engine.py` UND `py -3.11 verify_match.py` exit 0,
   bei Bedarf `py -3.11 main.py` für frische `treffer_v2.json`.
3. UI bauen (edyta-Hut). 4. Selbstcheck (§3.5) → auf „go"/„ZIP" warten → `state/etappe_v3_state.md`.
4. Falls Weg 1 (JS-Bridge) gewählt: kleinen Engine-Zusatz mit Marek abstimmen (Code-Etappe).

## Stand der Kette (Git)

`5820575` HANDOFF aktuell · `5e53391` Ausschluss-Fix · `da545d5` Etappe 2 (MatchAgent + Engine-Fixes).
`_stable`-ZIP: `Bewerbungs-Agentenbaum_v2_stable.zip` (lokal).

# Etappe v3 — State nach Abschluss

**Datum:** 2026-06-27
**ZIP:** (optional, auf Freigabe; `make_backup.py` noch nicht zwingend gelaufen)
**Status:** ✅ funktionsfähig + **live im Browser verifiziert** (Chrome, Doppelklick)

---

## Was wurde gemacht

- **Lokale HTML-Web-UI (edyta)** im Projektordner unter `ui/` — statisch, vanilla, keine
  CDNs/Dependencies, System-Fontstack, hell/nüchtern, Card-Grid fürs Ultrawide:
  - `ui/index.html` — Markup + Daten-Bridge-Einbindung.
  - `ui/style.css` — Token-getriebenes Light-Theme (CSS Custom Properties als einzige Quelle).
  - `ui/app.js` — vanilla IIFE, XSS-sicher (nur `createElement`/`textContent`).
- **Lade-Weg = JS-Bridge** (wie entschieden): `<script src="../treffer_v2.example.js">` als Default,
  echte `treffer_v2.js` per auskommentierter Zeile umschaltbar. **Kein fetch, kein Server**,
  klassisches `<script>` (file://-tauglich, nicht CORS-gesperrt). `../`-Pfad, da Bridge im Root liegt.
- **Controls:** Sortierung (Score/Datum, auf-/absteigend), Min-Score-Slider (Spanne aus Daten
  abgeleitet), Such-Titel-Filter, Freitext-Suche, Toggle „Ausschluss-Treffer ausblenden", Reset.
- **Treffer-Karte:** Titel→`job_url` (neuer Tab), Firma · Ort · Datum, Gehalt (min–max, de-DE,
  null→„k.A."), `kann_treffer`-Chips, Warn-Badges (ko / ausschluss / gehalt_unter_min),
  `muss_fehlt`-Info-Badge, ein-/ausklappbare Beschreibung (`<details>`, ohne JS).
- **Null-Toleranz** umgesetzt: `date_posted`/`min_amount`/`max_amount`/`description` = null → „k.A.",
  nie „null"/„NaN"/„undefined" im Output.
- **ko-Badge nur bei `ko=true`** (real aktuell alle `ko=False`, da `skills_muss` leer — Fall vertragen).

## Was wurde verworfen (und warum)

- **Quellen-Filter** nicht gebaut: Schema hat **kein per-Treffer Quellen-Feld** (nur `meta.quellen`
  global + per-Treffer `such_titel`). Statt totem Dropdown → funktionierender **Such-Titel-Filter**
  (Feld existiert pro Treffer). `meta.quellen` generisch im Kopf angezeigt (nicht hardcodiert).
  Echter per-Karte-Quellen-Filter bräuchte ein Engine-Feld `treffer[].quelle`/`site` → Mini-Etappe.
- **ES-Module / `type="module"`** verworfen: unterliegt auf `file://` der CORS-Sperre → klassisches
  Script.
- **`fetch()` / lokaler http.server** nicht der Pfad (CORS bzw. Server-Zwang) — JS-Bridge gewählt.

## Test-Status

- **Offline (headless, Node-DOM-Stub):** Render gegen alle 4 Fixture-Treffer = **16/16 Assertions grün**
  (Score-desc-Sortierung, ko-Badge genau 1×, null-Gehalt/-Datum → „k.A.", kein null/NaN/undefined im
  Output, Ausschluss-/Gehalt-/muss_fehlt-Badges, Gehalt `42.000–55.000 €` de-DE, Slider-Spanne −95…30
  aus Daten). `node --check app.js` = exit 0, CSS klammer-balanciert.
- **Struktur (§3.5):** alle 11 `getElementById`-Ziele aus `app.js` existieren in `index.html` —
  keine dangling reference.
- **Env-Smoke vorab:** `verify_engine.py` + `verify_match.py` beide exit 0.
- **Live (Browser):** ✅ in Chrome per Doppelklick / `file:///`-URL geöffnet, UI rendert die 4 Treffer
  korrekt („sieht super aus", User 2026-06-27). Damit ist der vormalige „nicht getestet"-Hotspot
  (cross-folder `../`-Bridge-Load über `file://`) **live bestätigt**.
- **Nicht getestet:** Edge/Firefox (nur Chrome live), Rendering gegen den **echten** `treffer_v2.js`
  (nur Fixture live geprüft — Schema identisch, daher niedriges Risiko), Druck-Stylesheet visuell.

## Bedien-Hinweis (wichtig — kein Bug)

Nackten Pfad `ui\index.html` **nicht** in die Chrome-Adressleiste tippen → landet in der Suche.
Stattdessen: Explorer-Doppelklick, oder `file:///C:/Users/adam2/.Projekte/Bewerbungs-Agentenbaum/ui/index.html`,
oder Drag & Drop ins Browserfenster.

## Public-Repo / PII

- `treffer_v2.js/json/csv` (Bridge + echte Treffer) sind `gitignored` (per `git check-ignore` bestätigt)
  → **nicht** getrackt, nicht im Commit. Nur `ui/`-Code (html/js/css) + State/HANDOFF committed.
- Fixtures `treffer_v2.example.json/.js` sind bewusst eingecheckt (anonymisiert).

## Known Issues (verbleibend)

- **Kein per-Treffer Quellen-Filter** (Schema-Lücke, s.o.) — nur falls später gebraucht.
- **Aus v2 unverändert:** Google-Quelle 0 Treffer (JobSpy-seitig), global-pip/crewai gebrochen
  (vertagt), Gehalt-Scoring best-effort (aktuell inaktiv).
- Score-Farbschwellen (`≥20` stark / `≥8` mittel / `>0` niedrig / `≤0` negativ) = edytas Setzung
  aus der ~30..0-Realspanne, bei Bedarf justierbar.

## Nächste sinnvolle Etappe (Vorschlag)

**Agenten-Roadmap (Marek, eigene frische Session)** — User-Entscheid 2026-06-24, NICHT anhängen.
Grundlage `state/agenten_roadmap.md`: Critic/FactGrounding/JDParser-Erweiterung + ATS-Zwei-Pfad-CV.
Alternativ optionale **Etappe 4** (natives Xing/Jobware-Scraping, Wolf) nur falls Google-Umweg
unzureichend.

## Verweis-Quellen

- Vorgänger-State: `state/etappe_v2_state.md`
- Brief dieser Etappe: `briefs/etappe_v3_brief.md`
- Relevante User-Entscheide: 2026-06-25 (JS-Bridge, hell/nüchtern), 2026-06-27 (Live-Abnahme UI)

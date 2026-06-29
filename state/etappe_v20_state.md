# Etappe v20 — service.bund.de-Quelle (öffentlicher Dienst) gebaut (Wolf)

**Datum:** 2026-06-29 · **Persona:** Wolf (Backend/Data-Hut) · **Status:** GEBAUT + verifiziert, COMMIT-bereit (kein PII)
**Vorlage:** `state/scope_servicebund_quelle.md` (Scope FERTIG+gemessen) + `!ETAPPE-GATE` aus HANDOFF.

## Was gebaut wurde

### `quelle_servicebund.py` — RSS-Adapter (NEU, stdlib-only)
- **Keine neue pip-Dependency:** `xml.etree` + `urllib` + `email.utils` + `html`. read-only.
- **Reine Parser (offline-testbar) vom Netz getrennt:**
  - `parse_rss(bytes)` → Treffer-Dicts im **KERN-Schema** (title/company/location/job_url/
    date_posted/min_amount/max_amount/description/such_titel) + guid/bewerbungsfrist/site/_pubdate.
    → Pipeline (match/jdparser/tailoring/coverletter/UI) greift **unverändert**.
  - `_parse_description(cdata)` → Arbeitgeber/Ort/Frist aus `<strong>…</strong>` der CDATA.
  - `parse_pubdate(s)` → RFC822 via `email.utils.parsedate_to_datetime` (**locale-unabhängig**,
    NICHT strptime %b). tz-aware, UTC-Fallback, unparsebar → None (kein Crash).
  - `filter_nach_datum(...)` → **Karteileichen-Filter** (Scope-CAVEAT: Feed enthält Anzeigen
    bis 2023/24). Default 90 Tage; unlesbares Datum bleibt (kein stiller Verlust).
  - `vorfilter(...)` → **vor dem teuren Detail-Fetch**: Titel-Keywords + Distanz (nutzt
    `match.GEO`/`_coords`/`_haversine`, keine API). Unauflösbarer Ort bleibt.
  - `html_zu_text(html)` → Detailseite → Plaintext (script/style/Kommentare raus, Block-Tags
    → Zeilenumbruch, Entities auf). **Bewusst generisch**, nicht auf GSB-div-IDs angewiesen
    (brüchig bei Relaunch); jdparser segmentiert ohnehin selbst.
- **Netz (urllib):** `_http_get_bytes` (RSS — BYTES wegen XML-encoding-Deklaration),
  `_http_get_text` (Detail), `fetch_detail_text`.
- **Orchestrator `hole_stellen(...)`:** holen → parsen → Datum → Vorfilter → **gedrosselter
  Detail-Fetch** (§3.6b: Crawl-delay 30s sequentiell, `max_detail`-Deckel, Wall-Clock-Ansage
  + START/Fortschritt/ENDE-Liveness-Logs). Ein Detail-Fehler → Treffer bleibt mit Kurzinfo.
- **CLI:** `python quelle_servicebund.py <feed_url> [--no-detail] [--max-tage N] [--max-detail N]`.

### `verify_servicebund.py` — offline Selbsttest (NEU)
- 8 Gruppen / alle grün, **kein Netz** (eingebettete Fixtures = echtes RSS-/HTML-Schema 1:1
  nach Live-Sample 2026-06-29, inkl. Umlaut-charrefs, alter Karteileiche, ferner GEO-Stadt):
  Schema-Mapping, Entity-Dekodierung (CDATA-literal vs Titel-charref), pubDate+tz, Datum-Filter,
  Vorfilter (Titel+Distanz), unauflösbarer-Ort-bleibt, HTML→Text, **Schema-Kompatibilität zu
  `match.bewerte_einen`/`bewerte_treffer`**.

### `main.py` — verdrahtet (gated, default No-Op)
- `Profil.servicebund` + `quellen_extra.servicebund` aus YAML gelesen.
- `ergaenze_servicebund(df, profil)` hängt service.bund-Treffer an die JobSpy-Roh-Treffer
  (concat) → dieselbe Dedup-/Scoring-/Report-Strecke. **Aktiv NUR wenn `feed_url` gesetzt**,
  sonst gibt es df unverändert zurück (verifiziert: No-Op-Pfad). Quelle down → `[WARN]`,
  Indeed-Lauf bleibt erhalten.

### `profile/jobprofil.example.yaml` — dokumentierter Stub
- `quellen_extra.servicebund` auskommentiert (feed_url/max_alter_tage/titel_keywords/
  detail_fetch/max_detail) inkl. Anleitung „Suchergebnis als RSS-Feed". Echte `jobprofil.yaml`
  ist PII/gitignored → User trägt seine gefilterte Feed-URL dort ein.

## Verifikation (§3.5 + §3.6a/b)
- **Offline:** `verify_servicebund.py` alle Checks grün; **`verify_all.py` 12/12** (vorher 11 +
  neue Suite). `py_compile` aller geänderten Dateien grün.
- **§3.6a Live (echte Operation lief real):**
  - RSS-Fetch+Parse gegen Live-Feed → **500 Items**, Firma/Ort/Datum/URL korrekt, Entities
    dekodiert (Münster/Küchenbuchhalterin), exit 0.
  - Voller Orchestrator-Pfad live: 500 → Vorfilter **22** → 1 Detail-Fetch → **6654 Zeichen**
    echter Aufgaben/Profil-Volltext (enthält „Berufsausbildung"/„ZÄHLT"). Detail-Fetch +
    `html_zu_text` real durchlaufen.
- **§3.6b:** Detail-Fetch ist der Laufzeit-Posten; durch Titel-Vorfilter + `max_detail`-Deckel
  + Wall-Clock-Ansage + Liveness-Logs gehärtet. Bei N Treffern = (N-1)×30s.

## Scope-Offenpunkte — Stand
1. Gefilterte Such-RSS-URL: **vom User gemessen** (22 Items, scope §Volumen). Adapter liest sie
   aus YAML; ohne URL → No-Op.
2. Detailseiten-HTML: **inspiziert** (GSB7.0, `<strong>`-Headings + `<ul><li>`); generischer
   Strip gewählt.
3. Volumen: **gemessen** (22, davon ~2–3 Indeed-unsichtbar relevant — scope).
4. ÖD-Keyword-Katalog: **ERLEDIGT v18** (jdparser), in dieser Session NICHT erneut.

## Bekannte Grenze (dokumentiert, nicht blockierend)
- `html_zu_text` ist generisch → etwas Nav/Header-Boilerplate bleibt im Volltext (Live-Sample
  zeigte „SERVICE.BUND.DE - Stellenangebote…" vorab). Für jdparser/match (keyword/substring)
  tolerabel; Block-Tag-Liste/Marker zentral justierbar, falls Rauschen stört. Bewusst KEIN
  Fitting auf GSB-div-IDs (Relaunch-brüchig, §3.10).

## Gekettet (§3.11, 22% UI): `tailor_treffer.py` promoten — ERLEDIGT
- **`tailor_treffer.py` (NEU, committbar, kein PII)** — per-Treffer read-only Tailoring-Report
  über die Live-Treffer-JSON: lädt `treffer_v*.json` (Indeed + service.bund), rechnet je Treffer
  `tailoring.abgleich_texte(anzeige, cv_text)` → Abdeckung% + `muss_fehlt`/`kann_fehlt`, mit
  durchgereichtem match-Score/Distanz/site. Zeigt auf einen Blick, welche echten Treffer am
  besten passen + wo echte Lücken sind, ohne jede Beschreibung einzeln in die CLI zu kopieren.
  **read-only/deterministisch/offline**, komponiert nur bestehende Module, erfindet nichts.
  **CV-Text = PII → Runtime-Arg, nie eingecheckt.** CLI `<cv.txt> [treffer.json] [--top N] [--json]`.
- **`verify_tailor_treffer.py` (NEU)** — 5 Gruppen offline grün (Lade-Robustheit beide JSON-Formate,
  anzeige_text Liste/Skalar-such_titel, Abdeckung/muss_fehlt-Logik mit echtem jdparser-Katalog
  [Schweißen/WIG als Muss-Lücke], read-only-Invariante + Reihenfolge-Erhalt + top, Report-leer).
  Lernpunkt im Fixture: jdparser ist **katalog-basiert** + klassifiziert nur mit Anforderungs-
  Trigger als `muss` → Fixture braucht echten Trigger ("zwingend erforderlich").
- **`verify_all.py` 12→13/13 grün.**

## Nachtrag (gleicher Tag, nach Live-Lauf mit echter User-Feed-URL)
- **Realitäts-Check:** Scope-Schätzung „22 Items / 2–3 relevant" war durch alte Anzeigen aufgebläht.
  Real+aktuell: enger Suchbegriff `handwerk` = **1** Treffer; **leerer `templateQueryString` +
  `resultsPerPage=100`** + client-seitige `titel_keywords` = **~3–6 technisch relevant** (Mess-/
  Regeltechniker FFM 13km, 2× Techniker Elektrotechnik Darmstadt 27km). Verdict: dünnes Segment,
  **Gratis-Hintergrundfang, kein Volumen** — echte Indeed-Blindflecke. Memory + Scope korrigiert.
- **`detail_fetch` Default True → FALSE** (quelle_servicebund.hole_stellen + main.ergaenze_servicebund
  + CLI `--detail` statt `--no-detail` + example-yaml). Grund: der Crawl-delay-30s-pro-Stelle-Fetch
  blockiert lange (hängte den Shell wiederholt beim Live-Probing); Titel+Ort+Datum+Scoring reichen
  zum Sichten. `true` nur bei Volltext-Bedarf, dann via `max_detail` gedeckelt. Offline-Verify grün
  (verify_servicebund testet die Parser, nicht den Default → unverändert grün).
- example-yaml-Stub trägt jetzt die **gemessene beste Config** (leerer Suchbegriff, resultsPerPage=100,
  erweiterte titel_keywords, detail_fetch: false).

## Offen / nächste Posten
- **COMMIT** (auf User-go), alles **kein PII**: `quelle_servicebund.py`, `verify_servicebund.py`,
  `tailor_treffer.py`, `verify_tailor_treffer.py`, `main.py`, `profile/jobprofil.example.yaml`,
  `state/etappe_v20_state.md`, `HANDOFF.md`.
- Autonome deterministische Roadmap damit erschöpft. Rest braucht User-Input oder ist groß/Netz:
  Glassdoor/LinkedIn-Toggle-Test (Netz/rate-limited, besser mit echtem Profil) · passende Anzeige
  tailoren (braucht User-URL/Anzeige) · nativer Xing/Jobware-Scraper (Wolf, eigene Session, §3.6b).

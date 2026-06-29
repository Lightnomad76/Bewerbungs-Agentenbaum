# Scope: service.bund.de als zusätzliche Quelle (öffentlicher Dienst)

**Erstellt:** 2026-06-29 · **Status:** SCOPE (kein Code gebaut) · **Bau = Wolf, eigene Session (§3.6b Laufzeit-Posten)**
**Motivation:** Indeed deckt öffentlichen Dienst schlecht ab (Beamte/TVöD, Kommunen, Unikliniken,
Theater/Bühnentechnik, Stiftungen, Forschung). Diese Arbeitgeber posten auf Behörden-Portalen, nicht
auf Indeed. Für Industriemechaniker/Instandhalter/Haustechnik real relevant (stabile TVöD-Stellen).

## Befunde (live verifiziert 2026-06-29, §3.10)

### 1. RSS-Feed existiert + ist tauglich — EMPFOHLENE QUELLE
- Generischer Stellen-Feed (RSS 2.0, live, 200+ Items):
  `https://www.service.bund.de/Content/Globals/Functions/RSSFeed/RSSGenerator_Stellen.xml`
- **Gefilterter Such-RSS möglich** (Server-seitig!): nach einer Suche (Region/Beruf/Stichwort) gibt es
  „Suchergebnis als RSS-Feed" → narrowed Feed statt 200 bundesweite Items. **Das ist der saubere Weg.**
  → BENÖTIGT vom User EINMAL: im Browser eine Suche bauen (z. B. Beruf „Industriemechaniker"/
  „Mechatroniker"/„Instandhalter"/„Haustechnik", Umkreis Offenbach) und die generierte
  „Suchergebnis als RSS"-URL liefern. (Such-SEITEN sind robots-disallowed, die RSS-Funktions-URL nicht.)
- **service.bund.de aggregiert interamt bereits** (Detail-URLs sind `…/IMPORTE/Stellenangebote/interamt/…`)
  → eine Quelle deckt service.bund + interamt ab; **keine separate interamt-Integration nötig**.

### 2. Schema des RSS-Items
- `<title>` — Stellenbezeichnung inkl. (m/w/d) → jdparser-Titel greift sauber
- `<link>` — Detail-URL (fetchbar, s. u.)
- `<description>` (CDATA) — Behörde + **Ort/PLZ** + Bewerbungsfrist → **Ort reicht fürs Distanz-Scoring**
- `<pubDate>`, `<guid>` (eindeutige ID, Dedup)
- **Kein Volltext im Feed** → Aufgaben/Profil per Detailseiten-Fetch (für jdparser/tailoring nötig).

### 3. Legal / robots.txt (verifiziert)
```
User-agent: *
Disallow: /Content/DE/Behoerden/Suche/
Disallow: /Content/DE/Stellen/Suche/
Disallow: /Content/DE/Ausschreibungen/Suche/
Disallow: /SiteGlobals/   (mit Allow-Ausnahmen)
Crawl-delay: 30
```
- **RSS-Feeds NICHT gesperrt** (offiziell zum Abonnieren/Automatisieren angeboten) → sanktioniert.
- **Detail-Seiten (`/IMPORTE/Stellenangebote/…`) NICHT gesperrt.**
- **`Crawl-delay: 30`** = harte Politeness-Vorgabe: 30 s zwischen Requests. Bei N Detail-Fetches ist das
  ein **block-gepufferter Laufzeit-Posten** (N×30 s) → §3.6b: messen, Liveness-Marker, sequentiell.
  → Genau deshalb: gefilterter Feed (kleines N) + Vorfilter (Ort/Distanz + Titel-Keywords) VOR dem
  Detail-Fetch, damit nur wenige Seiten gezogen werden.

## Architektur-Skizze (Bau-Posten, Wolf)
1. Gefilterte Such-RSS-URL (vom User) lesen → Items (stdlib `xml.etree`, KEINE neue Dependency).
2. Map RSS-Item → bestehendes Treffer-Schema (title, company=Behörde, location=Ort, url, date, guid).
3. **Vorfilter client-seitig**: Ort/Distanz (vorhandene GEO + 30 km) + Titel-Keywords → Überlebende.
4. Nur für Überlebende: Detailseite fetchen (Crawl-delay 30 s einhalten, sequentiell, echo-Liveness),
   Aufgaben/Profil-Volltext extrahieren → ins `description`-Feld.
5. **Bestehende Pipeline gilt unverändert**: match-Scoring, Distanz, jdparser, tailoring, cvtailoring,
   coverletter, UI. (Single-Source-Schema → null Pipeline-Änderung.)
- Neue Dateien: `quelle_servicebund.py` (Adapter) + `verify_servicebund.py` (RSS-Parse + Schema-Map
  gegen Fixture, OFFLINE — kein Netz im Verify). Keine neue pip-Dependency (xml.etree + urllib/requests).

## Alternativen (bewertet, verworfen/nachrangig)
- **interamt-API** (`gate.interamt.de/interamtApi`, OpenAPI 3.0): ist **Arbeitgeber-Seite** (Stellen
  anlegen/ändern/löschen), NICHT Bewerber-Suche. `INTERAMT.data` = **kostenpflichtiges** Bulk-Produkt.
  → für unseren Lese-/Suchzweck ungeeignet; service.bund-RSS deckt interamt ohnehin ab.
- **arbeitsagentur Jobsuche-API** (`rest.arbeitsagentur.de/jobboerse/jobsuche-service`, community
  `bundesAPI/jobsuche-api`, `X-API-Key: jobboerse-jobsuche`): JSON, **öffentlich + privat**, riesig,
  server-seitig nach Ort/Beruf filterbar — STÄRKER bei Abdeckung, ABER **inoffiziell** (kein offizielles
  API-Angebot) → Legal grauer als service.bund. Überlappt privat mit Indeed. **Option B**, falls
  service.bund-Abdeckung zu dünn; dann Legal/ToS gesondert prüfen (lib-version-checker/deep-search).
- **meinestadt.de**: kommerzieller Aggregator (AGB-Grauzone, Bruchrisiko), zieht selbst aus o. g.
  Quellen → service.bund direkt ist sauberer.

## Offene Punkte VOR dem Bau
1. **Gefilterte Such-RSS-URL vom User** (Browser-Suche → „Suchergebnis als RSS"). Sonst generischer
   Feed + härterer Client-Vorfilter (mehr Detail-Fetches = mehr Crawl-delay-Zeit).
2. **Detailseiten-HTML-Struktur** für Volltext-Extraktion an 1 Beispiel inspizieren (Aufgaben/Profil-
   Markup; die Hauswirtschaftsleitung-Seite zeigte strukturierten Text → extrahierbar).
3. **Volumen messen**: wie viele near+technische Treffer liefert der gefilterte Feed real für Obertshausen?
   (entscheidet, ob der Aufwand lohnt — erst messen, dann voll bauen, §3.6b „messen statt raten").
4. ~~Public-Sektor-Keyword-Katalog ergänzen~~ **ERLEDIGT (Prep v18, 2026-06-29)** — jdparser
   KEYWORD_KATALOG +6: Anlagenmechaniker, Gebäudetechnik (Haustechnik/GLT), MSR-Technik
   (= Samson-Regeltechnik-Brücke), Versorgungstechnik, Bühnentechnik, Hausmeister.
   verify_jdparser +8 Checks grün. In der Wolf-Session NICHT erneut.

## Volumen-Messung (2026-06-29, gefilterter Feed vom User)
Query: `templateQueryString=handwerker` + `ambit_distance=30` + `city_zipcode=Obertshausen` + `jobsrss=true`
→ **gültiger RSS 2.0, 22 Items.** Orte real nah (Raunheim/Friedberg/Rodgau/Hanau/Mörfelden-Walldorf/
Heusenstamm/Darmstadt/Frankfurt — viele im GEO-Belt). Schema wie erwartet (title/link/description/pubDate/guid).
- **Relevant für Profil ~2–3** (Indeed-unsichtbar): Mechatroniker/Elektriker Fahrzeuginstandhaltung
  (Stadtwerke VGF Frankfurt), Mess-/Regeltechniker:in (Stadt Frankfurt = Regeltechnik-Schwerpunkt),
  evtl. Hausmeister/in (Wetteraukreis). Rest Rauschen (Gärtner/pädagogisch/Sachbearbeiter) → der
  vorhandene Match-Scorer sortiert es weg (wie bei Indeed-Büro-Jobs) → **breite Query ist ok**.
- **VALIDIERT:** ÖD-Technik-Stellen im Umkreis existieren, die Indeed nicht zeigt → Aufwand lohnt für das Segment.
- **CAVEAT entdeckt:** Feed enthält **alte Anzeigen** (pubDate bis 2023/2024) → **`pubDate`-Filter
  Pflicht** (z.B. letzte 30–90 Tage), sonst Karteileichen. Zusätzlicher Bau-Punkt.
- **Crawl-delay-Kosten klein**: nach Score-Vorfilter nur ~Handvoll Detail-Fetches → ~Minuten, ok.

## Empfehlung
service.bund.de-RSS = **niedrigstes Legal-Risiko (sanktioniert), keine neue Dependency, deckt
interamt mit**. Bau als eigener Wolf-Posten (Laufzeit wegen Crawl-delay 30 s = §3.6b). Erst die
gefilterte Feed-URL + Volumen-Messung, dann Adapter + Verify, dann in Pipeline einhängen.

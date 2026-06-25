# Etappe v2 — State nach Abschluss

**Datum:** 2026-06-25
**ZIP:** (ausstehend — auf Freigabe; `make_backup.py` noch nicht gelaufen)
**Status:** ⚠️ funktionsfähig + live-verifiziert, mit benannten Restpunkten

---

## Was wurde gemacht

- **MatchAgent (`match.py`)** — offline, deterministisches Keyword-Scoring:
  - `skills_muss` = K.o.-Flag (UND-verknüpft) + starker Malus, `skills_kann` = Bonus,
    `ausschluss_keywords` = Malus, `gehalt_min_eur_jahr` = sanftes Flag (best-effort).
  - Substring-Match, case-/whitespace-normalisiert; jeder Treffer trägt sein `match`-Detail
    (score, ko, muss_treffer/fehlt, kann_treffer, ausschluss_treffer, gehalt_unter_min).
  - Sortierung: vollständige (ko=False) zuerst, dann Score absteigend.
  - **Design-Entscheidung:** fehlendes Muss → `ko=True` + Nach-unten-Sortieren, **kein** hartes
    Löschen (Keyword-Match auf Stellentexte ist spröde; read-only Tool soll nichts verstecken).
- **Marek-Review-Fixes aus Etappe 1 angewandt:**
  - **K1 (`dedupliziere`):** URL-Zeilen nur per `job_url` dedupliziert; `(title,company,location)`-
    Fallback nur auf Zeilen **ohne** `job_url`. Verschiedene Anzeigen derselben Firma/Titel
    (versch. URL) überleben jetzt.
  - **K2:** `such_titel` wird je Dedup-Schlüssel zu sortierter Liste aggregiert (kein Verlust mehr
    bei `keep="first"`). Schema-Folge: `such_titel` ist ab v2 eine **Liste**, nicht mehr String.
  - **S1:** `df.reindex(columns=KERN)` erzwingt stabiles JSON-Kernschema (UI-Bridge-Vertrag);
    fremde Spalten raus, fehlende als `null`.
  - **S2:** war bereits korrekt — `try/except` umschließt nur `scrape_jobs()`. Kein Change.
- **`verify_engine.py` erweitert:** N1 (K1: versch. URL bleibt 2), K2-Aggregation, S1-Schema-Stabilität.
- **`verify_match.py` neu:** Muss-K.o., Kann-Bonus, Ausschluss-Malus, Gehalt-Flag, Sortierung.
- **Output umbenannt:** `treffer_v2.json` (+ `treffer_v2.csv`, Review-CSV mit score/ko/muss_fehlt vorn),
  `meta.version = "v2"`.
- **Profil (`jobprofil.yaml`) Matching-Keywords umgestellt** (User-Entscheid 2026-06-25, datengestützt).

## Was wurde verworfen (und warum)

- **Mehrere berufsspezifische Muss-Keywords als UND-K.o.** verworfen. Live-Befund (35 Treffer):
  `AND[Qualitätssicherung, Industriemechaniker, Montage] = 1/35` → flaches Ranking, nur umgekehrt.
- **Einzelner Muss `"Qualität"` (29/35)** verworfen: wirft 5 **echte** Industriemechaniker-Stellen
  raus (sie nennen „Qualität" nicht). Dieses Profil deckt zwei Berufsrichtungen ab (Mechanik UND QS);
  kein berufsspezifischer Begriff steht in beiden → **kein** sinnvoller UND-K.o.-Term existiert.
  → `skills_muss: []` (leer, kein hartes K.o.), Berufs-Keywords als `skills_kann`-Bonus.
- **Matching tokenisieren** und **K.o. zu reinem Bonus** (Optionen B/C) nicht gewählt; Profil-Umstellung
  (Option A) reichte, Logik bleibt deterministisch/einfach.

## Nachgezogen nach Etappe-2-Abschluss (2026-06-25)

- **JS-Bridge für Etappe-3-UI (Vorbereitung):** `main.py` schreibt zusätzlich `treffer_v2.js`
  (`window.TREFFER = {…}`) → lokale UI per `file://`-Doppelklick ohne Server (CORS umgangen).
  `OUT_JS`-Konstante; `verify_engine.py` prüft die Bridge mit. `.gitignore`: `treffer_*.js` ignoriert,
  `!treffer_*.example.*` committbar. Anonymisierte Fixtures `treffer_v2.example.json/.js` eingecheckt.
  Lade-Weg + Design (hell/nüchtern) sind User-Entscheide; Detail im `briefs/etappe_v3_brief.md`.
- **Ausschluss-False-Positives (war Known Issue):** Ausschluss-Keywords wurden im ganzen Anzeigentext
  gesucht → „abgeschlossene Ausbildung" / „Praktikumsbescheinigungen" (Anforderungen) verbannten echte
  Stellen. Fix: `match.py` prüft Ausschluss jetzt **nur in Titel + such_titel** (`AUSSCHLUSS_FELDER`),
  Keywords auf Stellen-Typ-/Azubi-Titel-Muster präzisiert (kein bloßes „Ausbildung"). Regressionstest in
  `verify_match.py`. Live-Effekt: 0 False-Positive-Ausschlüsse, „INDUSTRIEMECHANIKER (M/W/D)" von #35 → #17.

## Known Issues (verbleibend in v2)

- **Google-Quelle weiter 0 Treffer** („initial cursor not found") — JobSpy-seitig (S3, vor eigenem Debugging
  via `lib-version-checker` gegen offene Issues prüfen). Indeed trägt allein.
- **Global-pip/crewai** weiter gebrochen (aus v1, bewusst vertagt) — JobSpy-Install hatte numpy/regex
  heruntergestuft. Unverändert.
- **Gehalt-Scoring best-effort:** Intervall (hourly/yearly) nach `reindex(KERN)` nicht mehr im Datensatz →
  Vergleich gegen `gehalt_min_eur_jahr` ist grob; aktuell ohnehin `null` (inaktiv).

## Test-Status

- **Offline:** `verify_engine.py` (20 Checks) + `verify_match.py` (14 Checks) grün, exit 0; alle Dateien
  `py_compile`-sauber.
- **Live (Netz):** `py -3.11 main.py` = 2.78s, 35 deduplizierte reale DE-Treffer (alle Indeed). Ranking nach
  Profil-Umstellung inhaltlich plausibel: Industriemechaniker oben (score 22/13/13/10), Junk (Pflege/
  studentisch) Mitte, Ausschluss unten. ko=0, Spanne 22..−10.
- **Nicht getestet:** LinkedIn-Pfad (inaktiv), echter 429 (nur durchdacht), Gehalt-Filter mit gesetztem Min.

## Nächste sinnvolle Etappe (Vorschlag)

v3 = **Lokale HTML-Web-UI (edyta)** — statisches HTML/JS im Projektordner, lädt `treffer_v2.json`, zeigt
sortiert/filterbar (Score/ko/Skill-Treffer sichtbar machen). `brief-writer` für v3-Brief. Eigene GUI-Etappe,
frischer Chat.

## Verweis-Quellen

- Vorgänger-State: `state/etappe_v1_state.md`
- Vorgänger-Brief: `briefs/etappe_v1_brief.md`
- Relevante User-Entscheide: 2026-06-25 (Matching-Fix = „Profil-Keywords umstellen"; „alles vorab mitnehmen")

# Etappe v5 — State nach Abschluss (Agenten-Roadmap E-B: FactGroundingAgent)

**Datum:** 2026-06-27
**ZIP:** (optional, auf Freigabe; `make_backup.py` nicht zwingend gelaufen)
**Status:** ✅ funktionsfähig + live gegen echten Brief verifiziert (0 False-Positives) + in Pipeline eingehängt
**Persona:** Marek (Code-Etappe). Grundlage: `state/agenten_roadmap.md` Abschnitt A.2 (FactGroundingAgent).

---

## Scope-Korrektur vorab (User-Entscheid 2026-06-27)

Die Roadmap A.2 nennt `jobprofil.yaml` als „einzige Wahrheitsquelle". **Das stimmt für
Fact-Grounding nicht:** `jobprofil.yaml` ist das *Such*-Profil (Titel/Skill-Keywords/Standort)
und enthält **keine** biografischen Fakten. Die erfindungsanfälligen Aussagen (Firmen, Zeiträume,
Zertifikate, Sprachniveau) leben als Stammdaten in `gen_cv.py` + den Generator-Overrides.

**Entscheidung (User):** Wahrheitsquelle = die **CV-Stammdaten selbst**, in den Agent
**reingefüttert** (nicht aus einer Datei gelesen). „Gegroundet" = „rückführbar auf die Daten, aus
denen das Dokument gebaut wird" → kein zweites Daten-Duplikat, kein Drift. API spiegelt critic:
`pruefe(text, fakten)` statt `pruefe(text)`.

## Was wurde gemacht

- **FactGroundingAgent (`factground.py`)** — deterministisch, **offline**, keine LLM-API.
  Grundsatz wie critic: **flaggt, ändert nichts** (read-only Scope).
  - **API:** `sammle_fakten(*quellen) -> fakten` (zieht Vokabular aus beliebig verschachtelten
    str/list/tuple-Stammdaten), `pruefe(text, fakten) -> {findings, stats}`,
    `hat_fehler(result) -> bool` (Pipeline-Gate), `report(quelle, result) -> str`.
  - **CLI:** `py -3.11 factground.py <text-datei> <wahrheitsquelle...> [--json]`;
    exit **1 bei FEHLER** / **0 sauber**.
  - **Methode „Known-Facts-Whitelist":** aus der Wahrheit ein Fakten-Vokabular ziehen
    (Firmen-Tokens, Zahlen/Jahre, Akronyme); generierten Text auf fakten-artige Tokens scannen;
    jedes nicht rückführbare flaggen.
- **Prüf-Kategorien / Schweren (ehrlich gelabelt):**
  - **FEHLER** (starkes Erfindungs-Signal): Firma mit Rechtsform (AG/GmbH/Aktiengesellschaft/…),
    deren Name-Token nicht in der Historie steht; Erfahrungs-**Dauer** („N Jahre"), deren Zahl nicht
    in den Stammdaten vorkommt.
  - **WARNUNG** (schwächeres Signal): Akronym (2–5 Großbuchst.) ohne Beleg; Jahreszahl (19xx/20xx)
    nicht in den Stammdaten.
- **Robustheit:** Markdown-Toleranz (`_clean`); Rechtsform-Varianten inkl. „AKTIENGESELLSCHAFT";
  generische Firmen-Wortbestandteile (Service/Personal/Technik …) grounden eine erfundene Firma
  NICHT (Stopword-Liste); Allowlist generischer Akronyme (DIN/ISO/EU/PC …); Zeilen-Mapping +
  Dedup pro Fund.
- **`verify_factground.py`** — offline Selbsttest, **31 Checks**, exit 0: Extraktion korrekt, guter
  Text 0/0 (kein False-Positive), schlechter Text triggert jede Kategorie, Markdown/Rechtsform,
  Stopword-/Allowlist-Robustheit, Schema-Stabilität, Gate `hat_fehler`.

## In die Bewerbungs-Pipeline eingehängt

- **`profile/gen_bewerbung_guetepruefer.py`** (lokal, PII, **gitignored**): nach `build_anschreiben()`
  läuft — zusätzlich zu Critic — `fg_pruefe(text, fakten)` + `fg_report()`; bei FEHLER ein
  Versand-Hinweis. **Read-only:** Dokument wird nie geändert, nur geflaggt.
  - `fakten = sammle_fakten(EXPERIENCE, ALPHA_HEADER, ALPHA_SUB, EXPERIENCE_TAIL, WEITERE,
    SAMSON, COPERION, KURZPROFIL, STAMMDATEN_EXTRA, CV_DATE_LINE)`.
  - **`STAMMDATEN_EXTRA`** neu im Generator: die nur in `build_*` hartkodierten Fakten
    (Weiterbildung EUP/EFKffT/SMBG, EDV SAP/Citrix/SuccessFactors, CNC/BASIC, Sprachen,
    Mannesmann Demag/Mittlere Reife) — sonst würden sie fälschlich als „nicht belegt" geflaggt.
  - `CV_DATE_LINE` mitgefüttert, damit das Briefkopf-Datum (2026) nicht als Pseudo-Fakt warnt.

## Test-Status

- **Offline:** `verify_factground.py` **31/31** grün, exit 0; `factground.py` + `verify_factground.py`
  `py_compile`-sauber (`py -3.11`).
- **Live (echter Brief, §3.6a):** `factground.py profile/Anschreiben_Guetepruefer_v2.md
  profile/Lebenslauf_Adam_Wzietek_v3.md` → 0 Fehler / 0 Warnungen (kein False-Positive auf real
  **gutem** Brief).
- **Negativ-Kontrolle gegen echte Wahrheitsquelle:** erfundene „Thyssenkrupp AG" + „40 Jahre" →
  FEHLER, „WIG" → WARNUNG, exit 1 (Vokabular winkt nicht alles durch).
- **End-to-end:** Generator `py -3.11`, 4 Dokumente gebaut; Critic 0/0; FactGrounding **0/0**.
- **Env-Smoke vorab (§3.11):** `verify_engine.py` + `verify_match.py` beide exit 0.

## Was wurde verworfen / bewusst nicht gemacht

- **`jobprofil.yaml` als Wahrheitsquelle** verworfen (enthält keine biografischen Fakten — s. o.).
- **LLM-/Semantik-Grounding** außerhalb Scope (offline/gratis, deterministisch).
- **Erkennung frei erfundener Prosa-Tätigkeiten** (ohne Eigennamen/Zahl) bewusst NICHT — ist
  deterministisch nicht erkennbar; ehrlich nicht behauptet statt Schein-Strenge.
- **Eigene `fakten.yaml`** verworfen (zweite Kopie = Drift-Risiko); Stammdaten direkt reinfüttern.

## Public-Repo / PII

- `factground.py` + `verify_factground.py` = **Code, kein PII** → committed.
- Generator-Integration (`profile/gen_bewerbung_guetepruefer.py`) + Briefe/CVs = **gitignored**
  (PII, per `git check-ignore` bestätigt). Echte Briefe/CVs nur **gelesen** (Live-Test), nicht eingecheckt.

## Known Issues / Offene Punkte

- **Heuristik-Tuning:** Firmen-Stopword-Liste + Akronym-Allowlist sind erste Setzung; an realen
  Texten nachschärfen. CEFR-Sprachlevel (C1) wird beim Grounding nicht geprüft (nur als
  Stammdaten-Token gelernt) — bewusst, niedriges Erfindungsrisiko.
- **Aus v2/v3/v4 unverändert:** Google-Quelle 0 Treffer (JobSpy-seitig); global-pip/crewai
  gebrochen (vertagt); echter ATS-Parser-Durchlauf des CV-Outputs offen (§3.6a-Smoke).

## Nächste sinnvolle Etappe (Vorschlag)

- **E-C (Marek/Wolf, eigene frische Session):** JDParserAgent / KeywordExtractor + getrennte Writer
  (CoverLetterWriter + CVTailoring) + ATS-Zwei-Pfad fest in den ReportAgent. Grundlage
  `state/agenten_roadmap.md` Abschnitt A.3/A.4 + C.

## Verweis-Quellen

- Planungsgrundlage: `state/agenten_roadmap.md` (Abschnitt A.2)
- Vorgänger-State: `state/etappe_v4_state.md`
- Relevante User-Entscheide: 2026-06-27 (Wahrheitsquelle = CV-Stammdaten reinfüttern; „go" zur Freigabe)

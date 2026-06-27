# Etappe v4 — State nach Abschluss (Agenten-Roadmap E-A, Teil: CriticAgent)

**Datum:** 2026-06-27
**ZIP:** (optional, auf Freigabe; `make_backup.py` noch nicht zwingend gelaufen)
**Status:** ✅ funktionsfähig + live gegen echten Brief verifiziert (0 False-Positives)
**Persona:** Marek (Code-Etappe). Grundlage: `state/agenten_roadmap.md` Abschnitt A (CriticAgent = höchster Nutzen) + Abschnitt B (Stil-Checkliste).

---

## Was wurde gemacht

- **CriticAgent (`critic.py`)** — deterministische, **offline** Stil-/Pflichtfeld-Prüfung für
  Anschreiben. KEINE LLM-API (passt zum offline/gratis-Scope). Grundsatz: **flaggt, ändert nichts**
  (read-only Projekt-Scope).
  - **API:** `pruefe(text) -> {"findings": [...], "stats": {...}}` + `hat_fehler(result) -> bool`
    (Pipeline-Gate). Jeder Befund: `{kategorie, schwere, nachricht, zeile, fundstelle}`.
  - **CLI:** `py -3.11 critic.py <pfad>` → Report, exit **1 bei FEHLER** / **0 sauber**;
    `--json` für maschinenlesbare Ausgabe (UI-/Pipeline-Bridge-tauglich).
  - **Pipeline-Rolle (Roadmap E-A):** schaltet zwischen Writer und ReportAgent — exit-Code/`hat_fehler`
    als Gate.
- **Prüf-Kategorien** (Quelle: `agenten_roadmap.md` Abschnitt B):
  - **FEHLER:** Floskel-Blacklist (Hiermit bewerbe ich mich / Mit großem Interesse … gelesen / neue
    Herausforderung / Über eine Einladung … freuen); fehlende Pflichtfelder Anrede, Grußformel,
    Kontakt (E-Mail|Telefon), Datum.
  - **WARNUNG (Heuristik):** unbelegte Selbst-Adjektive (teamfähig/zielstrebig/… → an Station/Zahl
    binden), Länge (>500 / <120 Wörter), Aufwärm-Erstsatz (7-Sek-Regel), Anrede ohne Namen,
    kein erkennbarer Betreff, weiche Floskel-Varianten.
- **`verify_critic.py`** — offline Selbsttest, **24 Checks**, exit 0: guter Brief fällt NICHT durch
  (kein False-Positive), schlechter Brief triggert jede Kategorie, Markdown-Toleranz, Schema-Stabilität.

## Was wurde verworfen / bewusst nicht gemacht

- **Adjektiv-„Beleg" als FEHLER** verworfen: ob ein Selbst-Adjektiv an eine konkrete Station/Zahl
  gebunden ist, lässt sich **deterministisch nicht** verifizieren → bewusst **WARNUNG** (prüfen),
  nicht Fehler. Ehrlich gelabelt statt Schein-Strenge.
- **Critic-Einhängung in `gen_bewerbung_guetepruefer.py`** bewusst NICHT in dieser Etappe — Critic
  läuft **standalone** (CLI + importierbare API). Das Einhängen zwischen Writer/ReportAgent ist eine
  eigene Mini-Etappe (Schnittstelle steht über `pruefe`/`hat_fehler` bereit).
- **DIN-5008-Layout-Prüfung** (Betreff fett, Datum rechtsbündig, Abstände) nicht umgesetzt: betrifft
  `.docx`-Geometrie, nicht den Text → gehört in den Generator/ReportAgent, nicht in den Text-Critic.
- **LLM-/Semantik-Bewertung** außerhalb Scope (offline/gratis, deterministisch).

## Test-Status

- **Offline:** `verify_critic.py` 24/24 grün, exit 0; `critic.py` + `verify_critic.py`
  `py_compile`-sauber (`py -3.11`).
- **Live (echter Brief):** `py -3.11 critic.py profile/Anschreiben_Guetepruefer_v2.md` → 346 Wörter,
  **0 Fehler / 0 Warnungen** → bestätigt: kein False-Positive auf einem real **gut** geschriebenen
  Brief. Exit-Codes 0/1 korrekt; `--json` valide (per `ConvertFrom-Json` geparst).
- **Env-Smoke vorab (§3.11):** `verify_engine.py` + `verify_match.py` beide exit 0.
- **Nicht getestet:** kein echter **Negativ**-Realbrief geprüft (nur synthetischer); Integration in
  die Bewerbungs-Pipeline (Critic noch nicht eingehängt); Heuristik-Schwellen (Wortgrenzen 500/120,
  Adjektiv-Liste) sind erste Setzung, an realen Briefen justierbar.

## Public-Repo / PII

- `critic.py` + `verify_critic.py` = **Code, kein PII** → committed.
- Der echte Brief `profile/Anschreiben_Guetepruefer_v2.md` wurde nur **gelesen** (Live-Test), **nicht**
  eingecheckt (PII, gitignored bzw. nur lokal).

## Nachgezogen 2026-06-27 — Critic in die Bewerbungs-Pipeline eingehängt

- **`profile/gen_bewerbung_guetepruefer.py`** (lokal, PII, **gitignored**): Anschreiben-Textbausteine
  in Variablen gehoistet → **eine Quelle** für docx **und** Critic (kein Drift). Nach `build_anschreiben()`
  (gibt jetzt `(pfad, text)` zurück) läuft `pruefe()` auf dem assemblierten Volltext; `report()` druckt
  den Befund, bei FEHLER ein Versand-Hinweis. **Read-only:** das Dokument wird nie geändert, nur geflaggt.
  Import via Repo-Root-`sys.path`-Insert (Generator läuft aus `profile/`).
- **`critic.py`:** `_report` → öffentliches `report()` (sauberer Fremd-Import). `verify_critic.py` danach
  weiter 24/24 grün.
- **Live:** Generator end-to-end (`py -3.11`), 4 Dokumente gebaut, Critic auf Anschreiben → 329 Wörter,
  0 Fehler/0 Warnungen.
- **PII-Grenze:** nur `critic.py` ist committed; die Generator-Integration bleibt lokal (gitignored).

## Known Issues / Offene Punkte

- **Critic nicht in Pipeline eingehängt** (Standalone) — Mini-Etappe, Schnittstelle steht.
- **Heuristik-Tuning** (Adjektiv-Liste, Wortgrenzen, Betreff-Erkennung bei Plain-Text fuzzy) an realen
  Briefen nachschärfen, sobald mehr Beispiele vorliegen.
- **Aus v2/v3 unverändert:** Google-Quelle 0 Treffer (JobSpy-seitig), global-pip/crewai gebrochen (vertagt).

## Nächste sinnvolle Etappe (Vorschlag)

- **E-B FactGroundingAgent (Marek, eigene frische Session):** jede generierte Aussage muss auf ein Feld
  in `jobprofil.yaml` (einzige Wahrheitsquelle) rückführbar sein; nicht-rückführbare Sätze werden
  **geflaggt, nicht ausgeliefert** (mechanischer §3.3-Schutz gegen erfundene CV-Fakten). Eigenbau —
  Grundlage `state/agenten_roadmap.md` Abschnitt A.2.
- **Optional davor:** Critic-Einhängung in `gen_bewerbung_guetepruefer.py` als kleine Etappe.

## Verweis-Quellen

- Planungsgrundlage: `state/agenten_roadmap.md` (Abschnitt A + B)
- Vorgänger-State: `state/etappe_v3_state.md`
- Relevante User-Entscheide: 2026-06-27 (Scope = CriticAgent bauen; „go" zur Freigabe)

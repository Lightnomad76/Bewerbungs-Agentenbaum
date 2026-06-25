# Agenten-Roadmap & Stil-Standards — Bewerbungs-Agentenbaum

**Erstellt:** 2026-06-24 · **Quelle:** deep-search-analyst (Strang 1 Architektur, Strang 2 Business-Stil/ATS),
8–10 unabhängige Quellen je Strang, verified/untested-Split. Vollzitate unten.
**Status:** Faktenlage gesichert. **Architektur-*Entscheidung* + Bau gehört zu Marek / second-opinion-architect**
(eigene Etappe) — dieses Doc ist die Planungsgrundlage, kein Implementierungs-Commit.

---

## A. Empfohlene Agenten-Erweiterungen (additiv zu ProfileAgent/SearchAgent/MatchAgent/ReportAgent)

Etablierte 2025/26-Pipeline = spezialisierte Rollen statt Mono-Writer. Priorität nach Nutzen/Aufwand:

1. **CriticAgent** (Generator-Critic / Reflexion-Pattern) — ✅ belegt halluzinations-mindernd.
   **Lokal/deterministisch baubar** (Floskel-Blacklist, Pflichtfeld-Check, Längen-Check) → KEINE LLM-API,
   passt zum offline/gratis-Scope. Schaltet zwischen Writer und ReportAgent. **Höchster Nutzen.**
2. **FactGroundingAgent** — projektkritisch (= mechanischer §3.3-Schutz gegen erfundene CV-Fakten).
   Regel: jede generierte Aussage muss auf ein Feld in `jobprofil.yaml` (einzige Wahrheitsquelle)
   rückführbar sein; nicht-rückführbare Sätze werden **geflaggt, nicht ausgeliefert**.
   ⚠️ **Eigenbau** — keine Quelle liefert ein fertiges Muster (ResumeFlow *misst* Halluzination nur,
   *verhindert* sie nicht). Reversibel/risikoarm, weil rein additiv.
3. **JDParserAgent / KeywordExtractor** — zieht Anzeigen-Vokabular strukturiert → speist Tailoring +
   ATS-Keywords. Belegt etabliert.
4. **Writer getrennt**: CoverLetterWriterAgent + CVTailoringAgent (nicht ein Mono-Writer) — entspricht
   der belegten Pipeline-Aufteilung.

**Referenzen:** ResumeFlow (arXiv 2402.06221, akad. 3-Stufen-Pipeline) · Reflexion (arXiv 2405.06682) ·
Repos: drukpa1455/crewai-job, touhi99/genai-job-agents, Paramchoudhary/ResumeSkills.
**Framework-Hinweis:** CrewAI = schneller Prototyp; LangGraph = Produktion/State. (Unser Scope ist
aber deterministisch/offline — die Quellen setzen durchweg GPT-4/Gemini voraus; Critic/Grounding lokal
ohne API ist NICHT durch eine Quelle vorgemacht = untested, aber machbar.)

---

## B. Business-Stil-Checkliste (direkt als Writer-System-Prompt / CriticAgent-Regeln)

**Verbotene Floskeln (Tabu, mehrfach belegt):**
- „Hiermit bewerbe ich mich…"
- „Mit großem Interesse habe ich Ihre Stellenanzeige gelesen"
- „… auf der Suche nach einer neuen Herausforderung"
- „Über eine Einladung würde ich mich sehr freuen" (inkl. Varianten „… freue ich mich sehr")

**Weitere Regeln:**
- Keine Selbst-Adjektive ohne Beleg (teamfähig/zielstrebig/kreativ/souverän/selbstständig/strukturiert/
  gewissenhaft) → an konkrete Station/Tätigkeit/Zahl binden („belegen statt behaupten").
- Erster Satz muss in **7 Sekunden** tragen — kein Aufwärm-Satz.
- Anrede mit Namen, wenn vorhanden; gendergerecht.
- Bezug auf konkrete Tätigkeit/Werte aus der Anzeige (zwingt JDParser-Output in den Brief).

**DIN 5008 (Fassung 03/2020) — Layout-Pflichten:**
- Betreff **fett**; Datum **rechtsbündig**; „Mit freundlichen Grüßen" **ohne Komma**, danach 3–4
  Leerzeilen, dann maschinenschriftlicher Name.
- Anschriftfeld Form B (Praxis-Standard Bewerbung): 8,5 × 4,5 cm, Start 4,5 cm vom oberen Rand.
- Lebenslauf: tabellarisch + **antichronologisch** (neu→alt), Datumsformat MM/JJJJ.
- ⚠️ DIN-Primärnorm paywalled (Beuth) → Maße aus konsistenten Sekundär-Referaten, nicht primär verifiziert.

---

## C. ATS-Befund (⚔️ disputed, aber für uns gelöst)

- **Randlose 2-Spalten-Tabellen (unsere `python-docx`-Methode) sind ein belegtes ATS-Parsing-Risiko** —
  Taleo scrambelt Zellen, Workday merged Zeilen-Zellen zu einem String, iCIMS überspringt Tabellen teils.
  **„Randlos" schützt NICHT** — Fix ist Single-Column, nicht unsichtbare Tabelle.
- **Header/Footer + Textboxen werden oft ignoriert** → Kontaktdaten als Plain-Text-Absatz oben.
- **Disputed:** deutsche Tradition erwartet 2-Spalten-Optik (Mensch liest schön) vs. ATS will einspaltig.
  Kontext-Auflösung: Mensch-gelesen (Mittelstand/Direkt) → Tradition; ATS davor (Konzern/Plattform,
  z. B. **SAP SuccessFactors** = ATS!) → Single-Column.
- **untested:** welcher Anteil Industriemechaniker-Stellen real durch ein ATS läuft — keine Zahl gefunden.
  python-docx-Output wurde von keiner Quelle parser-getestet.

**→ Umgesetzt 2026-06-24:** ReportAgent-Zwei-Pfad-Prinzip vorgezogen für eine konkrete Bewerbung —
`Lebenslauf_v3.docx` (klassisch 2-spaltig, Mensch) **+** `..._v3_ATS.docx`
(einspaltig, 0 Tabellen, Kontakt Plain-Text — für SuccessFactors). Beide aus denselben Daten in
`gen_bewerbung_guetepruefer.py` (`build_cv` / `build_cv_ats`).
**Offen (§3.6a-Smoke-Test):** echter Parser-Durchlauf des Outputs (z. B. profiling-institut CV-Parsing-Check)
— keine Recherche ersetzt das.

---

## Geplante Etappen (Vorschlag, je eigene frische Session — §3.11)

- **E-A (Marek):** Architektur-Entscheid welche Agenten + Default-CV-Pfad (second-opinion-architect für
  Pre-Mortem). Dann CriticAgent (lokal, Floskel-/Pflichtfeld-Regeln aus Abschnitt B) bauen.
- **E-B (Marek):** FactGroundingAgent gegen `jobprofil.yaml` (Eigenbau-Grounding).
- **E-C (Marek/Wolf):** JDParserAgent + getrennte Writer; ATS-Zwei-Pfad fest in ReportAgent.

## Quellen (Auszug)
arXiv 2402.06221 · arXiv 2405.06682 · arXiv 2510.06265 · jobscan.co/blog/resume-tables-columns-ats ·
resumemate.io (borderless tables) · wbstraining.de · profiling-institut.de/cv-parsing-check ·
din-5008-richtlinien.de · karrierebibel.de/floskeln-bewerbung · stepstone.de / indeed.de (antichronologisch).
Vollliste im Session-Transcript (deep-search-analyst, 2026-06-24).

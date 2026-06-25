# Konzept-State — Jobsuche-Agent (vor Etappe 1)

**Datum:** 2026-06-22
**ZIP:** noch keins (Pre-Code)
**Status:** 🧭 Konzeption abgeschlossen — kein stabiles Code-ZIP

> Hinweis: Dies ist **kein** `etappe_v<N>_state.md` nach etappe-tracker-Regel 1
> ("nur nach stabilem ZIP"). Es dokumentiert die Konzeptions-Phase vor der ersten
> Code-Etappe, damit eine CLI-Session ohne Chat-Scrolling startklar ist.

---

## Was wurde gemacht

- Anforderung geklärt: Bewerbungshilfe, die Jobbörsen nach dem Profil durchsucht + Vorschläge macht.
- Tool-Recherche: `speedyapply/JobSpy` als primäres Scraping-Tool identifiziert (v1.1.82, aktiv 2026).
- Plattform-Faktenlage geprüft (LinkedIn / Xing / Jobware) — siehe „Verworfen".
- Agentenstruktur entworfen: ProfileAgent / SearchAgents / MatchAgent / ReportAgent.
- 3-Etappen-Plan aufgestellt (siehe unten).

## Was wurde verworfen (und warum)

- **Profil-„Steuerung" / Auto-Bewerben** — AGB-Verstoß + Account-Sperrgefahr (LinkedIn/Xing/Jobware).
  Scope auf read-only Suchen+Vorschlagen reduziert.
- **Natives Xing-API** — öffentliches API eingestellt (New Work SE). Nur bezahlte
  Drittanbieter-Scraper oder Login-Scraping (riskant). Default = Google-Jobs-Umweg.
- **Jobware-Direkt-API** — kein bekanntes öffentliches Such-API → Eigen-Scraper (Etappe 3) oder Google-Umweg.

## Offene Punkte (Stand 2026-06-23)

- ✅ Frage 1 Scope: read-only bestätigt.
- ✅ Frage 2 Matching: Keyword offline (Semantik später optional).
- ✅ Frage 3 Xing/Jobware: Google-Umweg.
- ✅ Frage 5 Interface: lokale HTML-Web-UI projektordner-bezogen → Output als JSON; UI = eigene GUI-Etappe (edyta).
- ⏳ Frage 4 Jobprofil: User füllt `jobprofil.yaml` (v.a. `suche.jobtitel`, Etappe-2: `skills_muss/kann`) — **letzter Blocker vor Etappe-1-Build**.
- ⏳ JobSpy-cp314-Wheel: in Etappe 1 via lib-version-checker prüfen (Fallback `py -3.11`).

## Test-Status

- Nichts getestet — es existiert kein Code.
- JobSpy-Verfügbarkeit/Funktionsumfang = Recherche (geprüft), nicht selbst ausgeführt.

## Nächste sinnvolle Etappe (Vorschlag)

**Etappe 1:** Gerüst + ProfileAgent + JobSpy-SearchAgent (LinkedIn/Indeed/Google) → Roh-Treffer als CSV.
Voraussetzung: 5 offene Fragen beantwortet. Brief liegt vor (`briefs/etappe_v1_brief.md`).

## Verweis-Quellen

- HANDOFF.md (dieses Paket)
- Konzept-Chat 2026-06-22 (Architektur, Etappenplan)
- Recherche 2026-06-22: JobSpy (PyPI/GitHub), XING-API-Status

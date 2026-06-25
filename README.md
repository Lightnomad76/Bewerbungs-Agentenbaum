# Jobsuche-Agent — Handoff-Paket v0

Übergabe der Konzeptions-Phase an eine Claude-Code-CLI-Session. **Noch kein Code.**

## Inhalt

| Datei | Zweck |
|---|---|
| `HANDOFF.md` | **Hier starten.** Einstieg, Entscheidungen, 5 offene Fragen, Caveats. |
| `state/konzept_state.md` | Was gemacht/verworfen/offen ist (etappe-tracker-Stil). |
| `briefs/etappe_v1_brief.md` | Etappe 1 fertig gebrieft (brief-writer-Stil). |
| `profile/jobprofil.example.yaml` | Vom User auszufüllen → `jobprofil.yaml`. |

## Ablauf in der CLI-Session

1. `HANDOFF.md` lesen.
2. Die **5 offenen Fragen** dem User stellen (gebündelt), Antworten abwarten.
3. User füllt `jobprofil.yaml`.
4. Etappe 1 nach `briefs/etappe_v1_brief.md` bauen.
5. Selbstcheck → Zusammenfassung → auf "ZIP" warten (User-Workflow §7).

## Wichtig

- Read-only. Kein Login, kein Auto-Bewerben (AGB/Account-Sperre).
- JobSpy-Wheel auf Python 3.14.4 vor Einbau prüfen (lib-version-checker).

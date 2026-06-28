# Etappe v13 — Produktiv-Test an echten Anzeigen + deterministische Katalog-/Parser-Tuning-Posten

**Datum:** 2026-06-28 · **Persona:** Marek (Code) · **Gating:** deterministisch/offline, keine API (Memory `no-ongoing-api-cost`)

## Was gemacht (gekettet in einer Session, §3.11)

1. **Produktiv-Test der JD-Pipeline an zwei echten Anzeigen** (read-only Treiber im scratchpad,
   `ANZEIGE_DATEI`-Env, **keine echten CVs gebaut/angefasst**):
   - KTO Kabeltechnik „Industriemechaniker" (Rodgau) — Warm-up/Mismatch-nah.
   - SAMSON intern „Güteprüfer Fertigung Stufe 2" (Offenbach) — echter Profil-Match.
   - Anzeigen-Texte sind PII/intern → nur lokal im scratchpad, **nicht** committed/gepusht.

2. **`jdparser.py` KEYWORD_KATALOG erweitert** (zwei gemessene Katalog-Lücken geschlossen):
   - `fertigung`: +Mechatronik, Antriebstechnik, Betriebstechnik, Feinwerktechnik,
     Arbeitsvorbereitung, Maschineneinrichtung, Maschinenführung, Justieren.
   - `mess_qs`: +Abnahmeprüfzeugnis (EN 10204), Chargenverfolgung, Nacharbeit, Nichtkonformität.
   - Effekt am Samson-Test: Keywords 8→12, MUSS 1→3; Tool flaggt jetzt korrekt
     MUSS-Lücken (Abnahmeprüfzeugnis/Nacharbeit) statt sie zu übersehen.

3. **`ABSCHLUSS_RE` robuster:** erkennt „Berufsausbildung **in einem/einer** … Beruf" und
   optionales „abgeschlossene"-Präfix → Abschluss am Samson-Test „nicht erkannt" → „Metallberuf".

4. **Deliverable (lokal/PII):** zugeschnittenes internes Anschreiben „Güteprüfer Fertigung Stufe 2"
   + CV-Reihenfolge-Empfehlung. Ehrlich (factground-Prinzip): nur belegte Skills (Maßprüfung,
   Messmittel, Chargen DIN EN 10204, Abnahmen-Assistenz Großventil-Montage, SAP/MS-Office, C1);
   nicht belegte Anforderungen (3.2-Umstempelung, Nacharbeit, TÜV/EWM) als „arbeite ich mich ein",
   nicht als vorhanden. Repetition (v10-Issue) vermieden.

## Selbstcheck (§3.5)
- Syntax `jdparser.py` OK; **verify_all 10/10 grün** (insb. jdparser/tailoring/cvtailoring 54/54,
  kein Fixture-Bruch trotz Katalog-Erweiterung).
- Real-Beleg an echten Anzeigen, read-only.

## Nachgezogen (gekettet, gleiche Session)
- **Getailorte CV-PDFs (Deliverable, lokal):** klassisch + ATS-clean für die Güteprüfer-Stelle
  in TEMP gebaut, als PDF auf Desktop exportiert (Word/win32com). ATS-Lint 0 FEHLER. Echte
  `profile/`-CVs mtime-identisch = unberührt (Folgeschäden-Check bestanden).
- **„Deutsch"-False-Gap BEHOBEN:** `coverletter._bewerber_als_text` serialisiert jetzt `sprachen`
  (committed); `build_bewerber` liefert reale CV-Sprachen (Deutsch C1 / Polnisch / Englisch, lokal/PII).
  Effekt Samson-Test: Abdeckung 42%→50%, „Deutsch" korrekt gedeckt. verify_all 10/10.

## Bewusst NICHT gemacht (Folgeschäden-Ausschluss, User-Vorgabe)
- **Ansprechpartner „HR BP: <Name>" (ohne Herr/Frau):** würde in `coverletter._anrede` zu falscher
  Anrede führen („Sehr geehrte <Vorname Nachname>") → Folgeschaden. Aktuelles Verhalten
  (None + neutraler Fallback) ist das sichere; nur mit Geschlechts-Erkennung gefahrlos lösbar.

## Offene Punkte / nächste kleine Posten
- **Auto-Writer-Kosmetik:** deterministischer coverletter listet „Deutsch" als „Schwerpunkt"
  (Sprache ≠ Schwerpunkt) — Sprachen-Keywords in der Schwerpunkt-Zeile ausklammern.
- **Inhaltliche CV-Ergänzung (User-Aktion):** Bullet „Chargen nach DIN EN 10204" bei Samson aufnehmen
  (belegt, deckt eine MUSS-Anforderung; read-only Tool ergänzt bewusst keine Inhalte).
- Altlasten unverändert: echter externer ATS-Parser-Durchlauf (§3.6a, User-Aktion);
  natives Xing/Jobware-Scraping (Wolf, optional).

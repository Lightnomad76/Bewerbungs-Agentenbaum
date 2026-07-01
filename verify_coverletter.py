# -*- coding: utf-8 -*-
"""verify_coverletter.py — offline Mechanik-Selbsttest fuer den CoverLetterWriter.

Baut gegen synthetische Bewerber/Anzeige-Fixtures (keine PII, kein Netz, kein jobspy)
einen Brief und prueft: Pflicht-/Struktur-Felder, das **Akzeptanz-Gate** (critic 0
FEHLER + factground 0 FEHLER), JD-Steuerung (Anrede mit Name, Betreff aus Titel,
vorhandene Keywords genannt), Ehrlichkeit (fehlende MUSS-Keywords NICHT behauptet),
Laenge, Determinismus, Anrede-Fallback. exit 0 = alles gruen.

Lauf: .\\.venv\\Scripts\\python.exe verify_coverletter.py
      (kein jobspy noetig -> auch: py -3.11 verify_coverletter.py)
"""
from __future__ import annotations

import sys

from coverletter import schreibe, schreibe_fuer_anzeige, _bewerber_als_text
from jdparser import parse
from tailoring import abgleich
from critic import pruefe as c_pruefe, hat_fehler as c_hat_fehler
from factground import sammle_fakten, pruefe as fg_pruefe, hat_fehler as fg_hat_fehler

_fehler = 0


def ok(bedingung, text, ist=None):
    global _fehler
    marke = "[OK  ]" if bedingung else "[FAIL]"
    extra = "" if bedingung else ("  (ist: " + repr(ist) + ")")
    print("  " + marke + "   " + text + extra)
    if not bedingung:
        _fehler += 1


BEWERBER = {
    "name": "Max Mustermann",
    "email": "max.mustermann@example.com",
    "telefon": "0151 23456789",
    "ort": "Musterstadt",
    "beruf": "Industriemechaniker",
    "erfahrung": "langjähriger Erfahrung",
    "stationen": [
        {"firma": "Mustermann Technik GmbH", "zeitraum": "2018-2024",
         "taetigkeiten": ["Wartung und Instandhaltung von CNC-Anlagen",
                          "Montage von Baugruppen"],
         "skills": ["Drehen", "CNC", "Wartung", "Instandhaltung", "Montage"]},
    ],
}

ANZEIGE = """Industriemechaniker (m/w/d) Instandhaltung

Ihre Aufgaben:
- Wartung und Instandhaltung unserer CNC-Anlagen
- Montage von Baugruppen

Ihr Profil:
- Drehen und Fraesen zwingend erforderlich
- CNC-Kenntnisse
- SPS-Kenntnisse von Vorteil

Fuer Rueckfragen wenden Sie sich an Frau Schmidt.
"""

DATUM = "28.06.2026"  # fix fuer Determinismus


def main():
    brief = schreibe_fuer_anzeige(BEWERBER, ANZEIGE, datum=DATUM)

    print("[1] Pflicht-/Struktur-Felder (DIN 5008)")
    ok("Bewerbung als Industriemechaniker" in brief, "Betreff aus Titel (ohne m/w/d)")
    ok("Sehr geehrte Frau Schmidt," in brief, "Anrede mit Namen aus Anzeige")
    ok("Mit freundlichen Grüßen" in brief, "Grussformel (ohne Komma)")
    ok("max.mustermann@example.com" in brief, "Kontakt (E-Mail) im Body")
    ok(DATUM in brief, "Datum vorhanden")
    ok(brief.count("Max Mustermann") >= 2, "Name in Kopf + Signatur")

    print("[1b] Autoritativer Titel ueberschreibt jdparser-Heuristik (Indeed-Fix)")
    marketing = ("Unsere Mission: die Welt mit Energiespeichern veraendern, weltweit.\n"
                 "Wir suchen Verstaerkung fuer unser Team in der Fertigung.")
    bm = schreibe_fuer_anzeige(BEWERBER, marketing, datum=DATUM,
                               titel="Industriemechaniker (all genders)")
    betreff_line = [l for l in bm.splitlines() if l.startswith("Bewerbung als")][0]
    ok(betreff_line == "Bewerbung als Industriemechaniker",
       "Betreff = autoritativer Titel, Marketing-Vorspann verworfen + (all genders) bereinigt",
       betreff_line)

    print("[2] AKZEPTANZ-GATE: critic 0 FEHLER")
    cres = c_pruefe(brief)
    ok(c_hat_fehler(cres) is False, "critic: keine FEHLER", cres["stats"])
    ok(cres["stats"]["fehler"] == 0, "critic fehler == 0", cres["stats"]["fehler"])
    floskeln = [f for f in cres["findings"] if f["kategorie"] == "floskel" and f["schwere"] == "fehler"]
    ok(not floskeln, "keine verbotene Floskel", floskeln)

    print("[3] AKZEPTANZ-GATE: factground 0 FEHLER")
    fakten = sammle_fakten(_bewerber_als_text(BEWERBER), ANZEIGE)
    fres = fg_pruefe(brief, fakten)
    ok(fg_hat_fehler(fres) is False, "factground: keine FEHLER (nichts erfunden)", fres["stats"])
    ok(fres["stats"]["fehler"] == 0, "factground fehler == 0", fres["stats"]["fehler"])

    print("[4] JD-Steuerung: vorhandene Keywords genannt")
    jd = parse(ANZEIGE)
    abg = abgleich(jd, parse(_bewerber_als_text(BEWERBER)))
    ok("Drehen" in abg["vorhanden"], "Setup: Drehen ist vorhanden", abg["vorhanden"])
    ok(any(kw in brief for kw in abg["vorhanden"]), "mind. ein vorhandenes Keyword im Brief")
    ok("Wartung und Instandhaltung unserer CNC-Anlagen" in brief, "konkrete Anzeigen-Aufgabe referenziert")

    print("[5] Ehrlichkeit: fehlende MUSS-Keywords NICHT behauptet")
    ok("Fräsen" in abg["muss_fehlt"], "Setup: Fraesen ist muss_fehlt", abg["muss_fehlt"])
    ok("Fräsen" not in brief and "Fraesen" not in brief,
       "fehlendes MUSS (Fraesen) wird NICHT erfunden")

    print("[6] Laenge im Anschreiben-Rahmen")
    n = cres["stats"]["woerter"]
    ok(120 <= n <= 500, "120..500 Woerter", n)

    print("[7] Erstsatz kein Aufwaermer")
    erstsatz_warn = [f for f in cres["findings"] if f["kategorie"] == "erstsatz"]
    ok(not erstsatz_warn, "kein Aufwaerm-Erstsatz geflaggt", erstsatz_warn)
    ok(not brief.lower().lstrip().startswith("hiermit"), "startet nicht mit 'Hiermit'")

    print("[8] Determinismus")
    b2 = schreibe_fuer_anzeige(BEWERBER, ANZEIGE, datum=DATUM)
    ok(brief == b2, "gleiche Inputs -> identischer Text")
    ok(isinstance(brief, str) and len(brief) > 0, "Rueckgabe ist nicht-leerer String")

    print("[9] Anrede-Fallback ohne Ansprechpartner")
    anzeige_ohne = ANZEIGE.replace("Fuer Rueckfragen wenden Sie sich an Frau Schmidt.", "")
    b3 = schreibe_fuer_anzeige(BEWERBER, anzeige_ohne, datum=DATUM)
    ok("Sehr geehrte Damen und Herren," in b3, "neutraler Fallback")
    ok(c_hat_fehler(c_pruefe(b3)) is False, "Fallback besteht critic-Gate weiter")

    print("[10] Herr-Anrede korrekt gebeugt")
    jd_h = parse(ANZEIGE)
    jd_h["meta"]["ansprechpartner"] = "Herr Müller"
    bh = schreibe(BEWERBER, jd_h, abg, datum=DATUM)
    ok("Sehr geehrter Herr Müller," in bh, "Herr-Anrede gebeugt + nicht doppelt",
       [l for l in bh.splitlines() if "geehrt" in l])

    print("[11] Belegstation = relevanteste Station, NICHT stur die juengste")
    # Fix: coverletter zitierte frueher stationen[0] (juengste), auch wenn cvtailoring die
    # gerade nach unten sortierte. Jetzt waehlt es die fuer die Anzeige relevanteste Station
    # (gleiche Rangfolge wie cvtailoring) -> Brief + CV-Tailoring laufen nicht auseinander.
    bewerber_multi = {
        "name": "Max Mustermann", "ort": "Musterstadt",
        "beruf": "Industriemechaniker", "erfahrung": "langjähriger Erfahrung",
        "stationen": [
            # juengste Station: fuer eine Montage/Hydraulik-Anzeige IRRELEVANT (Score 0)
            {"firma": "Pruefdienst GmbH", "zeitraum": "2020-2024",
             "taetigkeiten": ["Dokumentation von Ergebnissen", "Terminplanung"],
             "skills": ["Terminplanung"]},
            # aeltere Station: montage-/hydraulik-relevant (Score > 0)
            {"firma": "Montagebau AG", "zeitraum": "2010-2020",
             "taetigkeiten": ["Montage von hydraulischen Baugruppen nach Zeichnung"],
             "skills": ["Montage", "Hydraulik"]},
        ],
    }
    anz_mont = ("Industriemechaniker (m/w/d)\n\nIhre Aufgaben:\n"
                "- Montage von hydraulischen Baugruppen\n")
    b_multi = schreibe_fuer_anzeige(bewerber_multi, anz_mont, datum=DATUM)
    ok("Montagebau AG" in b_multi, "Beleg zitiert die relevante (aeltere) Station", b_multi)
    beleg_zeile = [l for l in b_multi.splitlines() if l.startswith("In meiner Tätigkeit")]
    ok(beleg_zeile and "Pruefdienst GmbH" not in beleg_zeile[0],
       "Beleg zitiert NICHT die irrelevante juengste Station", beleg_zeile)
    # Rueckwaertskompatibel: ohne Relevanz-Signal (Single-Station) bleibt es bei stationen[0]
    b_single = schreibe_fuer_anzeige(BEWERBER, ANZEIGE, datum=DATUM)
    ok("Mustermann Technik GmbH" in b_single, "Single-Station-Fallback = juengste Station")

    print("[12] Einstieg fuehrt mit Fach-Skills, Sprachen zuletzt")
    # Fix: vorhanden kommt aus tailoring.abgleich alphabetisch -> 'Deutsch, Englisch'
    # standen vor Fach-Skills. Der Einstieg soll fachlich fuehren.
    bewerber_fach = {
        "name": "Max Mustermann", "ort": "Musterstadt", "beruf": "Industriemechaniker",
        "stationen": [{"firma": "Technik GmbH", "zeitraum": "2015-2024",
                       "taetigkeiten": ["Montage hydraulischer Baugruppen"],
                       "skills": ["Montage", "Hydraulik"]}],
        "sprachen": ["Deutsch", "Englisch"],
    }
    anz_fach = ("Industriemechaniker (m/w/d)\n\nIhre Aufgaben:\n"
                "- Montage von hydraulischen Baugruppen\n\nIhr Profil:\n"
                "- Sehr gute Deutschkenntnisse, gute Englischkenntnisse\n")
    b_fach = schreibe_fuer_anzeige(bewerber_fach, anz_fach, datum=DATUM)
    einstieg = [l for l in b_fach.splitlines() if l.startswith("Als ")][0]
    # sowohl ein Fach-Skill als auch eine Sprache im Einstieg, Fach VOR Sprache
    pos_fach = min((einstieg.find(k) for k in ("Montage", "Hydraulik") if k in einstieg),
                   default=-1)
    pos_spr = min((einstieg.find(k) for k in ("Deutsch", "Englisch") if k in einstieg),
                  default=10**9)
    ok(pos_fach != -1, "Fach-Skill (Montage/Hydraulik) im Einstieg", einstieg)
    ok(pos_fach < pos_spr, "Fach-Skill steht VOR der Sprache im Einstieg", einstieg)

    print("")
    if _fehler == 0:
        print("GRUEN: alle CoverLetter-Checks bestanden")
        return 0
    print("ROT: " + str(_fehler) + " Check(s) fehlgeschlagen")
    return 1


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    sys.exit(main())

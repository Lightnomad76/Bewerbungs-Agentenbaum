# -*- coding: utf-8 -*-
"""verify_jdparser.py — offline Mechanik-Selbsttest fuer den JDParserAgent.

Prueft gegen synthetische Anzeigen-Fixtures (keine PII, kein Netz, kein jobspy),
dass parse() das Vokabular korrekt extrahiert, Muss/Kann richtig klassifiziert,
Abschnitte segmentiert und Meta-Felder zieht. exit 0 = alles gruen.

Lauf: .\\.venv\\Scripts\\python.exe verify_jdparser.py
      (kein jobspy noetig -> auch: py -3.11 verify_jdparser.py)
"""
from __future__ import annotations

import sys

from jdparser import parse, keywords_flach

_fehler = 0


def ok(bedingung, text, ist=None):
    global _fehler
    marke = "[OK  ]" if bedingung else "[FAIL]"
    extra = "" if bedingung else ("  (ist: " + repr(ist) + ")")
    print("  " + marke + "   " + text + extra)
    if not bedingung:
        _fehler += 1


# Realistische, aber synthetische Anzeige (Industriemechaniker / QS).
ANZEIGE = """Industriemechaniker (m/w/d) Instandhaltung

Die Beispiel Maschinenbau GmbH sucht zum naechstmoeglichen Zeitpunkt.

Ihre Aufgaben:
- Wartung und Instandhaltung unserer CNC-Anlagen
- Montage von Baugruppen nach technischer Zeichnung
- Fehlersuche an Hydraulik- und Pneumatik-Systemen

Ihr Profil:
- Abgeschlossene Ausbildung als Industriemechaniker oder vergleichbar
- Erfahrung im Drehen und Fraesen zwingend erforderlich
- Kenntnisse in SPS (Siemens S7) sind von Vorteil
- WIG-Schweissen wuenschenswert
- Schichtbereitschaft wird vorausgesetzt
- Zuverlaessigkeit und Teamfaehigkeit

Wir bieten:
- Unbefristeter Vertrag
- 30 Tage Urlaub

Fuer Rueckfragen wenden Sie sich an Frau Schmidt.
"""


def main():
    res = parse(ANZEIGE)

    print("[1] Keyword-Extraktion: Katalog-Begriffe gefunden")
    flach = keywords_flach(res)
    ok("CNC" in flach, "CNC erkannt", flach)
    ok("Instandhaltung" in flach, "Instandhaltung erkannt")
    ok("Wartung" in flach, "Wartung erkannt")
    ok("Montage" in flach, "Montage erkannt")
    ok("Hydraulik" in flach and "Pneumatik" in flach, "Hydraulik + Pneumatik erkannt")
    ok("Drehen" in flach and "Fräsen" in flach, "Drehen + Fraesen erkannt")
    ok("SPS" in flach, "SPS erkannt")
    ok("Siemens S7" in flach, "Siemens S7 erkannt")
    ok("WIG" in flach, "WIG erkannt")
    ok("Schweißen" in flach, "Schweissen (Kanon) erkannt")
    ok("Teamfähigkeit" in flach, "Teamfaehigkeit erkannt")
    ok("Zuverlässigkeit" in flach, "Zuverlaessigkeit erkannt")
    ok("Schichtbereitschaft" in flach, "Schichtbereitschaft erkannt")
    ok("Technisches Zeichnen" in flach, "Technisches Zeichnen erkannt")

    print("[2] Keyword-Kategorisierung")
    ok("CNC" in res["keywords"]["steuerung_it"] or "CNC" in res["keywords"]["fertigung"],
       "CNC in plausibler Kategorie", res["keywords"])
    ok("Drehen" in res["keywords"]["fertigung"], "Drehen in fertigung")
    ok("Teamfähigkeit" in res["keywords"]["soft"], "Teamfaehigkeit in soft")
    ok(all(liste == sorted(liste) for liste in res["keywords"].values()),
       "jede Kategorie sortiert")

    print("[3] Muss/Kann-Klassifikation (zeilenbezogene Trigger)")
    muss = res["anforderungen"]["muss"]
    kann = res["anforderungen"]["kann"]
    ok("Drehen" in muss and "Fräsen" in muss, "'zwingend erforderlich' -> Drehen/Fraesen MUSS", muss)
    ok("Schichtbereitschaft" in muss, "'vorausgesetzt' -> Schichtbereitschaft MUSS", muss)
    ok("SPS" in kann or "Siemens S7" in kann, "'von Vorteil' -> SPS/S7 KANN", kann)
    ok("WIG" in kann, "'wuenschenswert' -> WIG KANN", kann)
    ok(not (set(muss) & set(kann)), "muss und kann disjunkt (muss hat Vorrang)")
    ok("Wartung" not in muss and "Wartung" not in kann,
       "Aufgaben-Keyword ohne Trigger ist neutral (nicht in muss/kann)")

    print("[4] Abschnitts-Segmentierung")
    ab = res["abschnitte"]
    ok("aufgaben" in ab, "Aufgaben-Abschnitt erkannt", list(ab))
    ok("profil" in ab, "Profil-Abschnitt erkannt", list(ab))
    ok("angebot" in ab, "Angebot-Abschnitt erkannt", list(ab))
    ok(len(ab["aufgaben"]) == 3, "Aufgaben hat 3 Bullets", ab.get("aufgaben"))
    ok(any("Wartung" in b for b in ab["aufgaben"]), "Bullet-Text erhalten")

    print("[5] Meta-Felder")
    m = res["meta"]
    ok(m["titel"] is not None and "(m/w/d)" in m["titel"], "Titel mit (m/w/d)", m["titel"])
    ok(m["ansprechpartner"] == "Frau Schmidt", "Ansprechpartner = Frau Schmidt", m["ansprechpartner"])
    ok(m["abschluss"] == "Industriemechaniker",
       "Abschluss erkannt + nachlaufendes 'oder vergleichbar' abgeschnitten", m["abschluss"])
    ok(m["schicht"] is True, "Schichtbereitschaft-Flag", m["schicht"])
    ok(m["reise"] is False, "Reise-Flag korrekt False (nicht im Text)", m["reise"])

    print("[5b] Titel-Heuristik gehaertet (Indeed-Marketing-Vorspann)")
    # (all genders) statt (m/w/d) muss als Titel erkannt werden (breiter GENDER_RE).
    ag = parse("Industriemechaniker (all genders)\nWir montieren Stellventile.")
    ok(ag["meta"]["titel"] == "Industriemechaniker (all genders)",
       "Geschlechtszusatz '(all genders)' -> Titel erkannt", ag["meta"]["titel"])
    # Marketing-Satz als erste Zeile darf NICHT als Titel gekapert werden -> Fallback Beruf.
    mk = parse("Unsere Mission: Energiespeicherung nach dem Vorbild der Natur ermoeglichen, "
               "weltweit fuer alle.\nAbgeschlossene Ausbildung als Industriemechaniker.")
    ok(mk["meta"]["titel"] == "Industriemechaniker",
       "Marketing-Vorspann verworfen -> Fallback auf erkannten Beruf", mk["meta"]["titel"])
    # Frage-/Label-Ueberschrift ist kein Titel.
    fr = parse("Was sind SolidFlow-Batterien?\nAbgeschlossene Ausbildung als Mechatroniker.")
    ok(fr["meta"]["titel"] == "Mechatroniker",
       "Frage-Ueberschrift verworfen -> Fallback auf Beruf", fr["meta"]["titel"])

    print("[6] Negativ-/Robustheit")
    leer = parse("")
    ok(leer["stats"]["keywords_gesamt"] == 0, "leerer Text -> 0 Keywords")
    ok(leer["anforderungen"]["muss"] == [] and leer["anforderungen"]["kann"] == [],
       "leerer Text -> keine Anforderungen")
    ok(leer["meta"]["titel"] is None, "leerer Text -> kein Titel")
    plain = parse("Wir suchen jemanden fuer allgemeine Buerotaetigkeiten ohne Fachbegriffe.")
    ok(plain["stats"]["keywords_gesamt"] == 0,
       "Text ohne Katalog-Begriff -> 0 Keywords (kein False-Positive)",
       plain["keywords"])
    # SAP darf nicht in beliebigem Wort matchen
    ok("SAP" not in keywords_flach(parse("Die Sappige Wiese war gruen.")),
       "'Sappige' triggert SAP nicht (Wortgrenze)")

    print("[7] Schema-Stabilitaet")
    ok(set(res.keys()) == {"keywords", "anforderungen", "abschnitte", "meta", "stats"},
       "Top-Level-Keys stabil", set(res.keys()))
    ok(set(res["meta"].keys()) == {"titel", "ansprechpartner", "abschluss", "schicht", "reise"},
       "meta-Keys stabil", set(res["meta"].keys()))
    ok(set(res["stats"].keys()) == {"keywords_gesamt", "muss", "kann", "abschnitte"},
       "stats-Keys stabil", set(res["stats"].keys()))
    ok(set(res["keywords"].keys()) == set(["fertigung", "mess_qs", "steuerung_it",
                                           "normen", "soft", "sprachen"]),
       "keyword-Kategorien stabil")

    print("[8] Mess/QS + Normen (zweite Fixture)")
    qs = parse(
        "Qualitaetssicherung\n"
        "Ihr Profil:\n"
        "- Erfahrung mit FMEA, SPC und 8D-Report\n"
        "- Bedienung der Koordinatenmessmaschine (CMM)\n"
        "- Kenntnis ISO 9001 und IATF 16949 erforderlich\n"
        "- Umgang mit Messschieber und Mikrometer\n"
        "- Bauteilmontage und Prüfung nach Prüfvorschrift mit Messuhr\n"
        "- Prüfmittelüberwachung\n"
    )
    qsf = keywords_flach(qs)
    ok("FMEA" in qsf and "SPC" in qsf and "8D-Report" in qsf, "FMEA/SPC/8D erkannt", qsf)
    ok("Koordinatenmessmaschine" in qsf, "CMM -> Koordinatenmessmaschine")
    ok("ISO 9001" in qsf and "IATF 16949" in qsf, "Normen erkannt", qsf)
    ok("Messschieber" in qsf and "Mikrometer" in qsf, "Messmittel erkannt")
    # v14: belegt durch echte Arbeitszeugnisse (IAV/Amicus) — neue mess_qs-Begriffe.
    ok("Messuhr" in qsf, "Messuhr erkannt (Zeugnis-belegt)", qsf)
    ok("Prüfvorschrift" in qsf, "Prüfvorschrift erkannt (Zeugnis-belegt)", qsf)
    ok("Prüfmittel" in qsf, "Prüfmittel(überwachung) erkannt", qsf)
    ok("ISO 9001" in qs["anforderungen"]["muss"], "ISO-Zeile mit 'erforderlich' -> MUSS",
       qs["anforderungen"]["muss"])

    print("")
    if _fehler == 0:
        print("GRUEN: alle JDParser-Checks bestanden")
        return 0
    print("ROT: " + str(_fehler) + " Check(s) fehlgeschlagen")
    return 1


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    sys.exit(main())

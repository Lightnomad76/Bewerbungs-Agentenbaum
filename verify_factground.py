# -*- coding: utf-8 -*-
"""Offline-Selbsttest fuer den FactGroundingAgent (factground.py).

Keine Netz-/API-/Datei-Abhaengigkeit: synthetische Stammdaten (mirror der echten
gen_cv-Struktur) + ein bewusst guter und ein bewusst schlechter Text. Prueft:
- sammle_fakten extrahiert Firmen-Tokens / Akronyme / Zahlen korrekt,
- guter Text faellt NICHT durch (kein False-Positive),
- schlechter Text triggert jede Kategorie (Firma/Dauer = FEHLER, Akronym/Jahr = WARNUNG),
- Markdown-Toleranz, Rechtsform-Varianten, Schema-Stabilitaet, Gate hat_fehler.

Lauf:  py -3.11 verify_factground.py    (exit 0 = alle Checks gruen)
"""
from __future__ import annotations

import sys
from factground import sammle_fakten, pruefe, hat_fehler

# --- synthetische Wahrheitsquelle (Struktur wie gen_cv: (datum, firma, [bullets], summary)) ---
TRUTH = [
    ("11/2017 – dato", "Samson AG, Frankfurt – Guetepruefung",
     ["Hydrostatische Festigkeitspruefung"], "Festigkeits- und Leckagepruefung"),
    ("11/2008 – 08/2010", "Coperion GmbH, Waldhof",
     ["Wareneingang und Kontrolle"], "Montage von Vakuumgeblaesen"),
    ("02/1997 – 02/2005", "Siemens Dematic AG, Waldhof", ["Foerdertechnik"], "Montage"),
    "Industriemechaniker mit ueber 8 Jahre Guetepruefung, ergaenzend ueber 25 Jahre "
    "Industriepraxis. SAP-Anwender, MS-Office, CNC, Deutsch C1.",
]

GOOD = """Sehr geehrte Frau Keienburg,

derzeit bin ich bei der Samson AG taetig. Ueber 8 Jahre pruefe ich Bauteile.
Bereits bei der Coperion GmbH habe ich Reparaturberichte erstellt.
SAP und MS-Office wende ich sicher an. Im Jahr 2017 begann meine Taetigkeit.

Mit freundlichen Gruessen
Adam Wzietek"""

BAD = """Sehr geehrte Damen und Herren,

ich war 30 Jahre bei der Bosch GmbH und zuvor bei der Continental AG.
Ich besitze ein ABC-Zertifikat und SPS-Kenntnisse.
Im Jahr 1985 startete meine Karriere.

Mit freundlichen Gruessen"""

_checks = 0
_fails = 0


def ok(bedingung, label):
    global _checks, _fails
    _checks += 1
    if bedingung:
        print("  [OK]   " + label)
    else:
        _fails += 1
        print("  [FAIL] " + label)


def hat(result, kategorie=None, schwere=None):
    return [f for f in result["findings"]
            if (kategorie is None or f["kategorie"] == kategorie)
            and (schwere is None or f["schwere"] == schwere)]


def main():
    fakten = sammle_fakten(*TRUTH)

    print("[1] sammle_fakten: Vokabular aus Stammdaten")
    ok("samson" in fakten["firma_tokens"], "Firma-Token 'samson' erkannt")
    ok("coperion" in fakten["firma_tokens"], "Firma-Token 'coperion' erkannt")
    ok("siemens" in fakten["firma_tokens"], "Firma-Token 'siemens' erkannt")
    ok("waldhof" not in fakten["firma_tokens"], "Ort nach Rechtsform NICHT als Firma-Token")
    ok("SAP" in fakten["akronyme"] and "CNC" in fakten["akronyme"], "Akronyme SAP/CNC erkannt")
    ok("AG" not in fakten["akronyme"], "Rechtsform 'AG' nicht als Akronym")
    ok(8 in fakten["zahlen"] and 25 in fakten["zahlen"], "Dauer-Zahlen 8/25 im Vorrat")
    ok(2017 in fakten["zahlen"], "Jahr 2017 im Vorrat")

    print("[2] Guter Text faellt NICHT durch (kein False-Positive)")
    rg = pruefe(GOOD, fakten)
    ok(rg["stats"]["fehler"] == 0, "guter Text: 0 FEHLER")
    ok(rg["stats"]["warnungen"] == 0, "guter Text: 0 WARNUNG")
    ok(not hat_fehler(rg), "hat_fehler(gut) == False")
    ok(rg["stats"]["geprueft"]["firmen"] >= 2, "guter Text: Firmen wurden ueberhaupt geprueft")

    print("[3] Firma ohne Beleg = FEHLER")
    rb = pruefe(BAD, fakten)
    firma_fehler = hat(rb, "firma", "fehler")
    ok(any("Bosch" in f["fundstelle"] for f in firma_fehler), "erfundene 'Bosch GmbH' geflaggt")
    ok(any("Continental" in f["fundstelle"] for f in firma_fehler), "erfundene 'Continental AG' geflaggt")
    ok(len(firma_fehler) == 2, "genau 2 Firmen-FEHLER (keine Doppelung)")

    print("[4] Erfahrungs-Dauer ohne Deckung = FEHLER")
    dauer_fehler = hat(rb, "dauer", "fehler")
    ok(len(dauer_fehler) == 1 and "30" in dauer_fehler[0]["fundstelle"], "'30 Jahre' als FEHLER")
    rd = pruefe("Ueber 8 Jahre im Einsatz.", fakten)
    ok(len(hat(rd, "dauer", "fehler")) == 0, "gedeckte '8 Jahre' kein FEHLER")

    print("[5] Akronym ohne Beleg = WARNUNG")
    akr_warn = hat(rb, "akronym", "warnung")
    funde = {f["fundstelle"] for f in akr_warn}
    ok("ABC" in funde, "'ABC' als WARNUNG")
    ok("SPS" in funde, "'SPS' als WARNUNG")
    ok(all(f["schwere"] == "warnung" for f in akr_warn), "Akronyme nie FEHLER")

    print("[6] Jahreszahl ohne Beleg = WARNUNG")
    jahr_warn = hat(rb, "jahr", "warnung")
    ok(any("1985" in f["fundstelle"] for f in jahr_warn), "'1985' als WARNUNG")
    ok(hat_fehler(rb), "hat_fehler(schlecht) == True")

    print("[7] Markdown-Toleranz + Rechtsform-Varianten")
    rmd = pruefe("Ich bin bei der **Samson AG** taetig.", fakten)
    ok(len(hat(rmd, "firma", "fehler")) == 0, "**Samson AG** (Markdown) wird gegroundet")
    rak = pruefe("Bewerbung bei der SAMSON AKTIENGESELLSCHAFT.", fakten)
    ok(len(hat(rak, "firma", "fehler")) == 0, "'SAMSON AKTIENGESELLSCHAFT' gegroundet (Rechtsform-Variante)")

    print("[8] Robustheit: Stopword-Firma + Allowlist + generisches Wort")
    rst = pruefe("Wir sind eine GmbH mit Profil.", fakten)
    ok(len(hat(rst, "firma")) == 0, "'eine GmbH' (nur Stopword) wird nicht geflaggt")
    rdin = pruefe("Pruefung nach DIN und ISO.", fakten)
    ok(len(hat(rdin, "akronym")) == 0, "DIN/ISO (Allowlist) nicht geflaggt")
    rgen = pruefe("Frueher bei der Mueller Service GmbH.", fakten)
    ok(len(hat(rgen, "firma", "fehler")) == 1, "generisches 'Service' groundet erfundene Firma NICHT")

    print("[9] Schema-Stabilitaet")
    ok(set(rb["stats"]) == {"fehler", "warnungen", "geprueft"}, "stats-Schluessel stabil")
    ok(set(rb["stats"]["geprueft"]) == {"firmen", "akronyme", "jahre", "dauern"},
       "geprueft-Schluessel stabil")
    feld_ok = all(set(f) == {"kategorie", "schwere", "nachricht", "zeile", "fundstelle"}
                  for f in rb["findings"])
    ok(feld_ok, "jedes finding hat das volle Schema")
    ok(all(f["zeile"] is None or f["zeile"] >= 1 for f in rb["findings"]), "Zeilen 1-basiert/None")

    print("---")
    if _fails == 0:
        print("GRUEN: alle " + str(_checks) + " FactGrounding-Checks bestanden")
        return 0
    print("ROT: " + str(_fails) + " von " + str(_checks) + " Checks fehlgeschlagen")
    return 1


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    sys.exit(main())

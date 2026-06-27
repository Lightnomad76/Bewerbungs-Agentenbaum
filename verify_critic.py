# -*- coding: utf-8 -*-
"""verify_critic.py — offline Selbsttest für den CriticAgent (critic.py).

Kein Netz, keine API. Prüft an synthetischen Anschreiben, dass jede Regel
greift (schlechter Brief) und NICHT überreagiert (guter Brief = 0 Fehler).
exit 0 = grün.   Lauf:  py -3.11 verify_critic.py
"""
import sys

from critic import (
    pruefe, hat_fehler,
    FLOSKELN, SELBST_ADJEKTIVE, WORT_MAX, WORT_MIN,
)

_fails = []


def check(bedingung, label):
    status = "OK  " if bedingung else "FAIL"
    print(f"  [{status}] {label}")
    if not bedingung:
        _fails.append(label)


def kat(result, kategorie=None, schwere=None):
    """Findings zählen, optional nach Kategorie/Schwere gefiltert."""
    return [f for f in result["findings"]
            if (kategorie is None or f["kategorie"] == kategorie)
            and (schwere is None or f["schwere"] == schwere)]


# --- Vollständiger, sauberer Brief (echtes Muster, kein Floskel) -------------
GUT = """\
Adam Wzietek
Egerländer Platz 19 · 63179 Obertshausen
Tel. 0176-47149475 · adam@example.de

SAMSON AG
Frau Keienburg
Frankfurt am Main

Obertshausen, den 24.06.2026

Bewerbung als Güteprüfer Fertigung Stufe 2 (w/m/d)

Sehr geehrte Frau Keienburg,

derzeit bin ich bei der Samson AG in der Güteprüfung tätig und möchte mich intern auf die
ausgeschriebene Position bewerben. In meiner heutigen Tätigkeit prüfe ich sicherheitsrelevante
Bauteile auf Richtigkeit und Vollständigkeit, führe hydrostatische Festigkeits- und
Leckageprüfungen durch und dokumentiere die Ergebnisse lückenlos. Bei Coperion habe ich
Reparaturberichte und Ersatzteillisten erstellt sowie Vakuumgebläse nach Zeichnung montiert.
Der sichere Umgang mit Zeichnungen, Toleranzen und Prüfvorgaben gehört für mich zum täglichen
Handwerk. SAP wende ich seit Jahren sicher an, MS-Office ebenso, Deutsch C1.

Gerne überzeuge ich Sie in einem persönlichen Gespräch von meiner Eignung.

Mit freundlichen Grüßen

Adam Wzietek
"""

# --- Schlechter Brief: triggert jede Kategorie -------------------------------
SCHLECHT = """\
Müllerstraße 1, Musterstadt

Hiermit bewerbe ich mich auf Ihre Stellenanzeige. Mit großem Interesse habe ich Ihre
Stellenanzeige gelesen und bin auf der Suche nach einer neuen Herausforderung. Ich bin
teamfähig, zielstrebig, kreativ und absolut belastbar. Über eine Einladung würde ich mich
sehr freuen.
"""

print("=== verify_critic.py (offline CriticAgent-Selbsttest) ===")

# --- [1] Guter Brief: keine Fehler -------------------------------------------
print("[1] Sauberer Brief darf NICHT durchfallen")
r_gut = pruefe(GUT)
check(not hat_fehler(r_gut), f"guter Brief: 0 Fehler (ist {r_gut['stats']['fehler']})")
check(len(kat(r_gut, "floskel")) == 0, "guter Brief: keine Floskel erkannt")
check(len(kat(r_gut, "pflichtfeld", "fehler")) == 0, "guter Brief: alle Pflichtfelder vorhanden")
check(len(kat(r_gut, "adjektiv")) == 0, "guter Brief: kein unbelegtes Selbst-Adjektiv")

# --- [2] Schlechter Brief: Floskeln greifen ----------------------------------
print("[2] Floskel-Blacklist greift")
r_bad = pruefe(SCHLECHT)
floskeln_fehler = kat(r_bad, "floskel", "fehler")
check(len(floskeln_fehler) >= 4, f"mind. 4 Floskel-Fehler (ist {len(floskeln_fehler)})")
labels = " | ".join(f["nachricht"] for f in floskeln_fehler)
check("Hiermit bewerbe ich mich" in labels, "‚Hiermit bewerbe ich mich' erkannt")
check("Herausforderung" in labels, "‚neue Herausforderung' erkannt")
check("Einladung" in labels, "‚Über eine Einladung' erkannt")

# --- [3] Selbst-Adjektive = Warnung ------------------------------------------
print("[3] Unbelegte Selbst-Adjektive werden geflaggt (Warnung)")
adj = kat(r_bad, "adjektiv")
check(len(adj) >= 4, f"mind. 4 Adjektiv-Warnungen (ist {len(adj)})")
check(all(f["schwere"] == "warnung" for f in adj), "Adjektive sind Warnung, nicht Fehler")

# --- [4] Pflichtfelder fehlen -> Fehler --------------------------------------
print("[4] Fehlende Pflichtfelder werden als Fehler gemeldet")
pf = kat(r_bad, "pflichtfeld", "fehler")
nachr = " | ".join(f["nachricht"] for f in pf)
check("Anrede" in nachr, "fehlende Anrede erkannt")
check("Grussformel" in nachr, "fehlende Grussformel erkannt")
check("Datum" in nachr, "fehlendes Datum erkannt")
check(hat_fehler(r_bad), "schlechter Brief: hat_fehler() == True (Gate rot)")

# --- [5] Erstsatz-Aufwärmer ---------------------------------------------------
print("[5] Aufwärm-Erstsatz nach Anrede wird erkannt")
ERSTSATZ = (
    "Sehr geehrte Frau Keienburg,\n\n"
    "Hiermit bewerbe ich mich auf die Stelle als Prüfer.\n\n"
    "Mit freundlichen Grüßen\nA. W.\n"
    "Tel. 0170-1234567, den 01.01.2026, Bewerbung als Prüfer"
)
r_erst = pruefe(ERSTSATZ)
check(len(kat(r_erst, "erstsatz")) >= 1, "Aufwärm-Erstsatz als Warnung erkannt")

# --- [6] Längen-Check ---------------------------------------------------------
print("[6] Längen-Schwellen greifen")
kurz = ("Sehr geehrte Frau Meier, ich bewerbe mich. Mit freundlichen Grüßen, "
        "A. W. Tel. 0170-1, den 01.01.2026, Bewerbung als Prüfer")
r_kurz = pruefe(kurz)
check(any("kurz" in f["nachricht"].lower() for f in kat(r_kurz, "laenge")),
      f"sehr kurzer Brief -> Längen-Warnung (Schwelle {WORT_MIN})")
lang_body = ("Sehr geehrte Frau Meier, " + ("Prüfung Qualität Montage Wartung " * 200) +
             " Mit freundlichen Grüßen A. W. Tel. 0170-1, den 01.01.2026, Bewerbung als Prüfer")
r_lang = pruefe(lang_body)
check(any("lang" in f["nachricht"].lower() for f in kat(r_lang, "laenge")),
      f"sehr langer Brief -> Längen-Warnung (Schwelle {WORT_MAX})")

# --- [7] Markdown-Toleranz ----------------------------------------------------
print("[7] Markdown-Marker stören die Erkennung nicht")
md = "## Betreff\n\n**Hiermit bewerbe ich mich** auf die Stelle."
r_md = pruefe(md)
check(len(kat(r_md, "floskel", "fehler")) >= 1, "Floskel trotz ** und ## erkannt")

# --- [8] Schema-Stabilität ----------------------------------------------------
print("[8] Rückgabe-Schema stabil")
check(set(r_gut.keys()) == {"findings", "stats"}, "Top-Level-Keys == {findings, stats}")
check(set(r_gut["stats"].keys()) == {"woerter", "fehler", "warnungen"}, "stats-Keys stabil")
if r_bad["findings"]:
    f0 = r_bad["findings"][0]
    check(set(f0.keys()) == {"kategorie", "schwere", "nachricht", "zeile", "fundstelle"},
          "finding-Keys stabil")

print("---")
if _fails:
    print(f"ROT: {len(_fails)} Check(s) fehlgeschlagen:")
    for f in _fails:
        print("   -", f)
    sys.exit(1)
print("GRÜN: alle CriticAgent-Checks bestanden")
sys.exit(0)

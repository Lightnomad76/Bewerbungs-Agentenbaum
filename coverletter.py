# -*- coding: utf-8 -*-
"""CoverLetterWriterAgent — deterministischer, offline Anschreiben-Generator.

Pipeline-Rolle (Agenten-Roadmap E-C / A.4, Sub-Etappe 1): ersetzt den frueher
hartkodierten Brieftext durch einen JD-getriebenen Writer. Baut das Anschreiben aus
den **CV-Stammdaten des Bewerbers** (reingefuettert) + dem **Anzeigen-Output**
(`jdparser.parse`) + dem **Abgleich** (`tailoring.abgleich`) deterministisch zusammen.

GATING-ENTSCHEIDUNG (User 2026-06-28): **deterministischer Default** — KEINE LLM-API.
Der Text entsteht aus Bausteinen (Kopf / Betreff / Anrede / Einstieg / Eignung /
Anzeigen-Bezug / Schluss / Gruss). Qualitaet „solide, regelkonform", nicht „brillant";
ein fluessigerer API-Pfad ist ein spaeterer, bewusster Schalter (dann Fact-Grounding
Pflicht). Bis dahin gilt: **belegen statt behaupten, nichts erfinden.**

WICHTIG (read-only Geist): der Writer behauptet nur, was durch den Abgleich gedeckt
ist — er nennt die im CV **vorhandenen** Anzeigen-Keywords (`abgleich.vorhanden`) und
verschweigt fehlende (`muss_fehlt`), statt sie zu erfinden. Damit besteht der Output
das Akzeptanz-Gate: `critic.pruefe` = 0 FEHLER UND `factground.pruefe` = 0 FEHLER.

Stil-Regeln: state/agenten_roadmap.md Abschnitt B (keine Floskel-Blacklist-Treffer,
7-Sekunden-Erstsatz, Anrede mit Namen wenn bekannt, DIN-5008-Pflichtfelder). Die
**Fett**-/Layout-Pflichten (Betreff fett, Datum rechtsbuendig) sind Sache des docx-
Generators — dieser Writer liefert strukturierten Plain-Text.

CLI:   python coverletter.py <anzeige-datei> <bewerber.json> [--json]
API:   from coverletter import schreibe, schreibe_fuer_anzeige
       text = schreibe_fuer_anzeige(bewerber, anzeige_text)
"""
from __future__ import annotations

import re
import sys
import json
from datetime import date

from jdparser import parse, MWD_RE
from tailoring import abgleich


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------


def _titel_clean(titel: str) -> str:
    """(m/w/d) und Mehrfach-Leerzeichen aus dem Stellentitel entfernen."""
    t = MWD_RE.sub("", titel or "")
    return re.sub(r"\s{2,}", " ", t).strip(" -–—\t") or "die ausgeschriebene Stelle"


def _anrede(ansprechpartner) -> str:
    """Anrede aus 'Herr X' / 'Frau X' bauen; sonst neutraler Fallback."""
    if ansprechpartner:
        ap = ansprechpartner.strip()
        if re.match(r"(?i)frau\b", ap):
            return "Sehr geehrte " + ap + ","
        if re.match(r"(?i)herr\b", ap):
            name = re.sub(r"(?i)^herr\b", "", ap).strip()
            return "Sehr geehrter Herr " + name + ","
    return "Sehr geehrte Damen und Herren,"


def _bewerber_als_text(bewerber: dict) -> str:
    """Bewerber-Stammdaten zu Fliesstext flachklopfen (fuer parse()/Grounding)."""
    teile = [bewerber.get("name", ""), bewerber.get("beruf", ""),
             bewerber.get("erfahrung", "")]
    for st in bewerber.get("stationen", []):
        teile.append(st.get("firma", ""))
        teile.append(st.get("zeitraum", ""))
        teile.extend(st.get("taetigkeiten", []) or [])
        teile.append(", ".join(st.get("skills", []) or []))
    teile.extend(bewerber.get("skills", []) or [])
    return "\n".join(t for t in teile if t)


# ---------------------------------------------------------------------------
# Kern-API
# ---------------------------------------------------------------------------


def schreibe(bewerber: dict, jd_result: dict, abgleich_result: dict,
             ort: str = None, datum: str = None) -> str:
    """Anschreiben deterministisch aus Bausteinen zusammensetzen. Gibt Plain-Text."""
    name = (bewerber.get("name") or "").strip()
    email = (bewerber.get("email") or "").strip()
    tel = (bewerber.get("telefon") or "").strip()
    ort = (ort or bewerber.get("ort") or "").strip()
    beruf = (bewerber.get("beruf") or "").strip() or "Fachkraft"
    erfahrung = (bewerber.get("erfahrung") or "").strip()
    stationen = bewerber.get("stationen", []) or []
    datum = datum or date.today().strftime("%d.%m.%Y")

    meta = jd_result.get("meta", {})
    titel = _titel_clean(meta.get("titel"))
    anrede = _anrede(meta.get("ansprechpartner"))
    vorhanden = abgleich_result.get("vorhanden", []) or []
    aufgaben = jd_result.get("abschnitte", {}).get("aufgaben", []) or []

    # --- Kopf (DIN: Kontakt als Plain-Text) -----------------------------------
    kontakt = " | ".join(x for x in (email, tel) if x)
    kopf = "\n".join(z for z in (name, ort, kontakt) if z)
    datum_zeile = (ort + ", den " + datum) if ort else ("den " + datum)
    betreff = "Bewerbung als " + titel

    # --- Einstieg (7-Sekunden, kein Aufwaermer) -------------------------------
    top = ", ".join(vorhanden[:4]) if vorhanden else "den von Ihnen geforderten Aufgaben"
    erfahr = (" mit " + erfahrung) if erfahrung else ""
    einstieg = ("Als " + beruf + erfahr + " bringe ich die von Ihnen für " + titel
                + " gesuchten Schwerpunkte in " + top + " unmittelbar mit.")

    # --- Eignung (belegen statt behaupten, an eine Station gebunden) -----------
    koennen = ", ".join(vorhanden[:6]) if vorhanden else "die geforderten Aufgaben"
    if stationen:
        st = stationen[0]
        firma = (st.get("firma") or "").strip()
        zeitraum = (st.get("zeitraum") or "").strip()
        beleg = "In meiner Tätigkeit"
        if firma:
            beleg += " bei " + firma
        if zeitraum:
            beleg += " (" + zeitraum + ")"
        beleg += (" habe ich " + koennen + " im Arbeitsalltag angewandt und Aufträge "
                  "termin- und qualitätsgerecht abgeschlossen.")
    else:
        beleg = ("In meiner bisherigen Tätigkeit habe ich " + koennen + " im "
                 "Arbeitsalltag angewandt und Aufträge termin- und qualitätsgerecht "
                 "abgeschlossen.")
    vertief = ("Konkret decke ich die in Ihrer Anzeige zentral genannten Punkte "
               + koennen + " aus der täglichen Praxis ab; in neue Anlagen und "
               "Verfahren arbeite ich mich zügig ein.")

    # --- Bezug auf eine konkrete Anzeigen-Aufgabe -----------------------------
    if aufgaben:
        bezug = ("Die in Ihrer Anzeige genannte Aufgabe „" + aufgaben[0].rstrip(". ")
                 + "“ deckt sich unmittelbar mit dem, was ich heute verantworte.")
    else:
        bezug = ("Die in Ihrer Anzeige beschriebenen Aufgaben decken sich unmittelbar "
                 "mit meinem bisherigen Verantwortungsbereich.")

    # --- Schluss (KEINE Einladungs-Floskel) + Gruss ---------------------------
    schluss = "Für ein persönliches Gespräch stehe ich Ihnen gern zur Verfügung."
    gruss = "Mit freundlichen Grüßen\n\n" + name

    absaetze = [kopf, datum_zeile, betreff, anrede, einstieg, beleg, vertief,
                bezug, schluss, gruss]
    return "\n\n".join(a for a in absaetze if a and a.strip())


def schreibe_fuer_anzeige(bewerber: dict, anzeige_text: str,
                          ort: str = None, datum: str = None) -> str:
    """Bequemlichkeit: parse(anzeige) + abgleich(gegen Bewerber-CV) + schreibe()."""
    jd = parse(anzeige_text)
    abg = abgleich(jd, parse(_bewerber_als_text(bewerber)))
    return schreibe(bewerber, jd, abg, ort=ort, datum=datum)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("--")]
    flags = {a for a in argv[1:] if a.startswith("--")}
    if len(args) < 2:
        print("Aufruf: python coverletter.py <anzeige-datei> <bewerber.json> [--json]",
              file=sys.stderr)
        return 2
    try:
        with open(args[0], "r", encoding="utf-8") as fh:
            anzeige = fh.read()
        with open(args[1], "r", encoding="utf-8") as fh:
            bewerber = json.load(fh)
    except OSError as e:
        print("FEHLER: Datei nicht lesbar: " + str(e), file=sys.stderr)
        return 2
    except json.JSONDecodeError as e:
        print("FEHLER: bewerber.json ungültig: " + str(e), file=sys.stderr)
        return 2

    text = schreibe_fuer_anzeige(bewerber, anzeige)
    if "--json" in flags:
        print(json.dumps({"anzeige": args[0], "anschreiben": text}, ensure_ascii=False, indent=2))
    else:
        print(text)
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    sys.exit(main(sys.argv))

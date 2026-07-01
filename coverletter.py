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

from jdparser import parse, MWD_RE, GENDER_RE
from tailoring import abgleich


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------


def _titel_clean(titel: str) -> str:
    """Geschlechtszusatz ((m/w/d), (all genders) …) und Mehrfach-Leerzeichen entfernen."""
    t = GENDER_RE.sub("", MWD_RE.sub("", titel or ""))
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
    teile.extend(bewerber.get("sprachen", []) or [])
    return "\n".join(t for t in teile if t)


# ---------------------------------------------------------------------------
# Kern-API
# ---------------------------------------------------------------------------


def _belegstation(bewerber: dict, jd_result: dict, abgleich_result: dict,
                  stationen: list) -> tuple:
    """Belegstation fuers Anschreiben waehlen: die fuer DIESE Anzeige relevanteste
    Station — dieselbe Rangfolge wie cvtailoring, damit Brief und CV-Tailoring NICHT
    auseinanderlaufen (frueher zitierte der Brief stur die juengste Station
    `stationen[0]`, die das CV-Tailoring evtl. gerade nach unten sortiert hatte).
    Tie-Break bleibt die Original-Reihenfolge -> ohne Relevanz-Signal faellt es auf
    die juengste Station zurueck (= altes Verhalten, ruecwaertskompatibel).
    Lazy import bricht den Modul-Zyklus (cvtailoring importiert coverletter)."""
    try:
        from cvtailoring import priorisiere
        sortiert = priorisiere(bewerber, jd_result, abgleich_result).get("stationen") or []
        if sortiert:
            top = sortiert[0]
            return (top.get("firma") or "").strip(), (top.get("zeitraum") or "").strip()
    except Exception:
        pass  # jede Stoerung -> alter, sicherer Pfad
    st = stationen[0]
    return (st.get("firma") or "").strip(), (st.get("zeitraum") or "").strip()


# Kategorie-Prioritaet fuer die Einstiegs-Reihenfolge: Fachliches zuerst, Sprachen zuletzt.
_KAT_PRIO = {"fertigung": 0, "mess_qs": 0, "steuerung_it": 0, "normen": 1,
             "soft": 2, "sprachen": 3}


def _fachlich_zuerst(vorhanden: list, jd_result: dict) -> list:
    """Reihenfolge fuers Anschreiben: fachliche Keywords (Fertigung/Mess-QS/Steuerung)
    zuerst, Sprachen zuletzt. Sonst fuehrt der Einstieg mit 'Deutsch, Englisch'
    (tailoring.abgleich liefert vorhanden alphabetisch) — bei einer Technik-Stelle
    schwach. Muss/Kann-Gewicht taugt hier NICHT: reale Anzeigen triggern oft nur die
    Sprachen als 'kann', die Fach-Skills bleiben neutral. Innerhalb gleicher Prioritaet
    stabil (sorted ist stabil) -> die alphabetische Eingangsreihenfolge bleibt."""
    kat_von = {}
    for kat, kws in (jd_result.get("keywords") or {}).items():
        for kw in kws:
            kat_von[kw] = kat
    return sorted(vorhanden, key=lambda kw: _KAT_PRIO.get(kat_von.get(kw, ""), 1))


def schreibe(bewerber: dict, jd_result: dict, abgleich_result: dict,
             ort: str = None, datum: str = None, titel: str = None) -> str:
    """Anschreiben deterministisch aus Bausteinen zusammensetzen. Gibt Plain-Text.
    titel: autoritativer Stellentitel (z. B. JobSpy job['title']) — ueberschreibt die
    jdparser-Titel-Heuristik (die bei Indeed-Marketing-Vorspann danebengreifen kann)."""
    name = (bewerber.get("name") or "").strip()
    email = (bewerber.get("email") or "").strip()
    tel = (bewerber.get("telefon") or "").strip()
    ort = (ort or bewerber.get("ort") or "").strip()
    beruf = (bewerber.get("beruf") or "").strip() or "Fachkraft"
    erfahrung = (bewerber.get("erfahrung") or "").strip()
    stationen = bewerber.get("stationen", []) or []
    datum = datum or date.today().strftime("%d.%m.%Y")

    meta = jd_result.get("meta", {})
    titel = _titel_clean(titel if titel is not None else meta.get("titel"))
    anrede = _anrede(meta.get("ansprechpartner"))
    vorhanden = _fachlich_zuerst(abgleich_result.get("vorhanden", []) or [], jd_result)
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
    # Dedup gegen das Dreifach-Listing: die Schwerpunkte stehen im Einstieg; der Beleg
    # referenziert sie kollektiv ("diese Schwerpunkte"), der Vertief-Absatz nennt nur
    # NOCH NICHT genannte gedeckte Keywords (vorhanden[4:]).
    bezeichner = "diese Schwerpunkte" if vorhanden else "die geforderten Aufgaben"
    if stationen:
        firma, zeitraum = _belegstation(bewerber, jd_result, abgleich_result, stationen)
        beleg = "In meiner Tätigkeit"
        if firma:
            beleg += " bei " + firma
        if zeitraum:
            beleg += " (" + zeitraum + ")"
        beleg += (" habe ich " + bezeichner + " im Arbeitsalltag angewandt und Aufträge "
                  "termin- und qualitätsgerecht abgeschlossen.")
    else:
        beleg = ("In meiner bisherigen Tätigkeit habe ich " + bezeichner + " im "
                 "Arbeitsalltag angewandt und Aufträge termin- und qualitätsgerecht "
                 "abgeschlossen.")
    rest = vorhanden[4:8]
    if rest:
        vertief = ("Darüber hinaus bringe ich " + ", ".join(rest) + " aus der täglichen "
                   "Praxis mit; in neue Anlagen und Verfahren arbeite ich mich zügig ein.")
    else:
        vertief = ("Diese Punkte decke ich aus der täglichen Praxis ab; in neue Anlagen "
                   "und Verfahren arbeite ich mich zügig ein.")

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
                          ort: str = None, datum: str = None, titel: str = None) -> str:
    """Bequemlichkeit: parse(anzeige) + abgleich(gegen Bewerber-CV) + schreibe().
    titel: optionaler autoritativer Stellentitel (sonst jdparser-Heuristik)."""
    jd = parse(anzeige_text)
    abg = abgleich(jd, parse(_bewerber_als_text(bewerber)))
    return schreibe(bewerber, jd, abg, ort=ort, datum=datum, titel=titel)


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

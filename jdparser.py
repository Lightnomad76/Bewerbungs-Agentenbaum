# -*- coding: utf-8 -*-
"""JDParserAgent / KeywordExtractor — deterministisches, offline Parsen einer
Stellenanzeige in strukturiertes Vokabular.

Pipeline-Rolle (Agenten-Roadmap E-C, Abschnitt A.3): zieht aus einer Anzeige das
Anforderungs-Vokabular strukturiert heraus und speist damit (a) das spaetere
CV-/Anschreiben-Tailoring und (b) die ATS-Keyword-Liste. KEINE LLM-API, rein
regelbasiert gegen ein kuratiertes Domaenen-Woerterbuch (Industriemechaniker / QS +
allgemein-technisch).

Grundsatz wie CriticAgent/FactGroundingAgent: der Agent EXTRAHIERT, aendert nichts
(read-only Scope des Projekts). Er erfindet keine Anforderung — er findet nur, was
woertlich in der Anzeige steht.

Ausgabe von parse(text):
  keywords      kategorisiertes Vokabular {fertigung, mess_qs, steuerung_it,
                normen, soft, sprachen} -> sortierte Kanon-Begriffe (dedup)
  anforderungen {muss, kann} -> Kanon-Begriffe, klassifiziert nach Trigger-Woertern
                in ihrer Zeile (zwingend/Voraussetzung = muss; von Vorteil/
                wuenschenswert = kann; ohne Trigger = neutral, nicht hier gelistet)
  abschnitte    erkannte Anzeigen-Abschnitte (Aufgaben / Profil / Wir bieten) ->
                Bullet-Zeilen
  meta          {titel, ansprechpartner, abschluss, schicht, reise}
  stats         Zaehler

EHRLICHE GRENZE (deterministisch, keine LLM): erkannt wird nur, was im Woerterbuch
steht bzw. einem Muster entspricht. Eine ungewoehnlich formulierte Anforderung ohne
Katalog-Begriff faengt der Parser bewusst NICHT — das wird ehrlich nicht behauptet.
Das Woerterbuch ist erweiterbar (KEYWORD_KATALOG).

CLI:   .\\.venv\\Scripts\\python.exe jdparser.py <anzeige-datei> [--json]
       (kein jobspy noetig -> laeuft auch global: py -3.11 jdparser.py ...)
API:   from jdparser import parse, keywords_flach, report
       res = parse(anzeige_text); ats = keywords_flach(res)
"""
from __future__ import annotations

import re
import sys
import json

# Umlaut-Folding: Anzeigen schreiben Umlaute mal als ä/ö/ü/ß, mal als ae/oe/ue/ss.
# Inhalts-Matches (Keywords, Trigger, Ueberschriften) laufen gegen die gefoldete
# Form -> beide Schreibweisen treffen. Muster werden mit derselben Funktion gefoldet
# (literale Umlaute im Muster -> ae/.. ; Regex-Metazeichen bleiben ASCII = unberuehrt).
_UML = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss",
                      "Ä": "Ae", "Ö": "Oe", "Ü": "Ue"})


def _fold(s: str) -> str:
    return s.translate(_UML)


# ---------------------------------------------------------------------------
# Domaenen-Woerterbuch: kategorie -> [(kanon, regex-variante), ...]
# Reihenfolge egal; Output ist der Kanon-Begriff (nicht die Anzeigen-Schreibweise).
# Erweiterbar — neue Branche = Kategorie/Eintraege ergaenzen.
# ---------------------------------------------------------------------------

KEYWORD_KATALOG = {
    "fertigung": [
        ("Drehen", r"dreh(?:en|teil|maschine|er)"),
        ("Fräsen", r"fräs(?:en|teil|maschine|er)"),
        ("Bohren", r"bohr(?:en|ung|maschine)"),
        ("Schleifen", r"schleif(?:en|maschine)"),
        ("CNC", r"cnc"),
        ("Zerspanung", r"zerspan(?:ung|en)"),
        ("Schweißen", r"schwei(?:ß|ss)(?:en|er|naht)"),
        ("WIG", r"wig\b"),
        ("MAG", r"mag-schwei|\bmag\b"),
        ("MIG", r"\bmig\b"),
        ("Löten", r"löt(?:en|stelle)"),
        ("Montage", r"montage|montier(?:en|t)"),
        ("Instandhaltung", r"instandhalt(?:ung|en)"),
        ("Wartung", r"wartung|warten"),
        ("Reparatur", r"reparat(?:ur|ieren)"),
        ("Hydraulik", r"hydraulik|hydraulisch"),
        ("Pneumatik", r"pneumatik|pneumatisch"),
        ("Technisches Zeichnen", r"technische[nr]?\s+zeichn|zeichnung(?:en)?\s+les"),
        # Kern-Industriemechaniker-Vokabular (v13: realer Anzeigen-Test KTO/Rodgau
        # deckte diese Luecken auf — Anzeige nennt sie unter "Erweiterte Kenntnisse").
        ("Mechatronik", r"mechatronik"),
        ("Antriebstechnik", r"antriebstechnik"),
        ("Betriebstechnik", r"betriebstechnik"),
        ("Feinwerktechnik", r"feinwerktechnik"),
        ("Arbeitsvorbereitung", r"arbeitsvorbereitung"),
        ("Maschineneinrichtung", r"maschineneinrichtung|anlageneinrichtung"),
        ("Maschinenführung", r"maschinenführung|anlagenführung|maschinenbedienung|anlagenbedienung"),
        ("Justieren", r"justier(?:en|ung)"),
        # v21 (2026-07-01): realer Indeed-Test (CMBlu Industriemechaniker) deckte auf, dass
        # gaengiges Prototypen-/Sondermaschinenbau-Vokabular fehlte. Evidenzbasiert: alle
        # Begriffe standen wortwoertlich in der echten Anzeige; "Prototyp" matcht zusaetzlich
        # Adams Siemens-Station ("Prototypen"). ("hydraulisch"-Adjektiv-Recall oben mitgefixt.)
        ("Prototypenbau", r"prototyp(?:en|enbau)?"),
        ("Sondermaschinenbau", r"sondermaschinenbau"),
        ("Werkzeugmaschine", r"werkzeugmaschine"),
        # v18: öffentlicher-Dienst-Technik (service.bund-Quelle, Scope 2026-06-29) — Rollen,
        # die im gemessenen ÖD-Feed real vorkamen + zum Profil passen (Stadtwerke/Kommune/Theater).
        ("Anlagenmechaniker", r"anlagenmechaniker"),
        ("Gebäudetechnik", r"gebäudetechnik|haustechnik|gebäudeleittechnik|\bglt\b"),
        ("Versorgungstechnik", r"versorgungstechnik"),
        ("Bühnentechnik", r"bühnentechnik|veranstaltungstechnik"),
        ("Hausmeister", r"hausmeister|hauswart"),
    ],
    "mess_qs": [
        ("Qualitätssicherung", r"qualitätssicherung|qualitäts-?kontrolle|qualitätsprüfung"),
        ("Messtechnik", r"messtechnik"),
        ("Messmittel", r"messmittel"),
        ("Messschieber", r"messschieber|schieblehre"),
        ("Mikrometer", r"mikrometer|bügelmessschraube"),
        ("Koordinatenmessmaschine", r"koordinatenmessmaschine|\bkmg\b|\bcmm\b"),
        ("Erstmusterprüfung", r"erstmuster(?:prüf|bericht)|\bempb\b"),
        ("FMEA", r"\bfmea\b"),
        ("SPC", r"\bspc\b|statistische\s+prozess"),
        ("8D-Report", r"\b8d\b|8d-report"),
        ("Reklamation", r"reklamation"),
        ("Wareneingangsprüfung", r"wareneingangsprüfung|wareneingangskontrolle"),
        ("Endkontrolle", r"endkontrolle|endprüfung"),
        ("Prüfprotokoll", r"prüfprotokoll|prüfbericht"),
        # Güteprüfung / Prüftechnik (v12: KEYWORD_KATALOG fuer den realen Gueteprueferei-CV)
        ("Maßprüfung", r"maß-?prüfung|maß-?kontrolle|maßhaltigkeit"),
        ("Festigkeitsprüfung", r"festigkeitsprüfung"),
        ("Druckprüfung", r"druckprüfung|hydrostatische\s+prüfung"),
        ("Leckageprüfung", r"leckageprüfung|leckage"),
        ("Dichtheitsprüfung", r"dichtheitsprüfung|dichtheitstest"),
        ("Sichtprüfung", r"sichtprüfung|sichtkontrolle"),
        ("Toleranz", r"toleranz"),
        ("Abnahmeprüfung", r"abnahmeprüfung|kundenabnahme|warenabnahme"),
        # Güteprüfer-Fertigung-Vokabular (v13: realer interner Samson-Anzeigen-Test
        # deckte diese QS-Kernbegriffe als Katalog-Luecke auf).
        ("Abnahmeprüfzeugnis", r"abnahmeprüfzeugnis|prüfzeugnis|werkszeugnis|en\s?10204"),
        ("Chargenverfolgung", r"chargen?\b|chargennummer|chargenrückverf"),
        ("Nacharbeit", r"nacharbeit"),
        ("Nichtkonformität", r"nicht-?konformität|nonkonformität|abweichungsbericht"),
        # v14: belegt durch die echten Arbeitszeugnisse (extract_quellordner-Corpus) —
        # Messuhr (Amicus/Karl Mayer "Wirkhebel mittels Messuhren"), Prüfvorschrift
        # (IAV "Prüfung nach Prüfvorschrift"), Prüfmittel(-überwachung) = Standard-QS-Lücken.
        ("Messuhr", r"messuhr(?:en)?"),
        ("Prüfvorschrift", r"prüfvorschrift|prüfanweisung"),
        ("Prüfmittel", r"prüfmittel(?:überwachung)?"),
    ],
    "steuerung_it": [
        ("SPS", r"\bsps\b|speicherprogrammierbar"),
        ("Siemens S7", r"\bs7\b|simatic"),
        ("TIA-Portal", r"tia[- ]portal|\btia\b"),
        ("SAP", r"\bsap\b"),
        ("CAD", r"\bcad\b"),
        ("CATIA", r"catia"),
        ("SolidWorks", r"solidworks"),
        ("AutoCAD", r"autocad"),
        ("ERP", r"\berp\b"),
        ("MS Office", r"ms[- ]office|microsoft\s+office|\bexcel\b"),
        # v18: MSR/Regeltechnik = Samson-Schwerpunkt (Stellventile/Regeltechnik) UND häufig
        # in ÖD-Technik-Stellen (Stadt/Stadtwerke) — matcht Anzeige UND CV (Tailoring-Boost).
        ("MSR-Technik", r"msr-?technik|mess-?\s*und\s*regeltechnik|regel(?:ungs)?technik"),
    ],
    "normen": [
        ("DIN", r"\bdin\s?\d|\bdin\s?en"),
        ("EN-Norm", r"\ben\s?\d"),
        ("ISO 9001", r"iso\s?9001"),
        ("IATF 16949", r"iatf\s?16949"),
        ("ISO 14001", r"iso\s?14001"),
        ("GD&T", r"gd&t|form-?\s*und\s+lagetoleranz"),
    ],
    "soft": [
        ("Teamfähigkeit", r"teamfähig|teamfä|teamplay|im\s+team"),
        ("Zuverlässigkeit", r"zuverlässig"),
        ("Selbstständigkeit", r"selbst(?:st)?ändig"),
        ("Sorgfalt", r"sorgfält|gewissenhaft|genau(?:igkeit|es\s+arbeiten)"),
        ("Belastbarkeit", r"belastbar"),
        ("Flexibilität", r"flexib"),
        ("Kommunikationsfähigkeit", r"kommunikationsfähig|kommunikationsstark"),
        ("Schichtbereitschaft", r"schichtbereit|schichtarbeit|\d-schicht|drei-?schicht"),
        ("Reisebereitschaft", r"reisebereit|dienstreise"),
    ],
    "sprachen": [
        ("Deutsch", r"deutsch(?:kenntnisse)?"),
        ("Englisch", r"englisch(?:kenntnisse)?"),
    ],
}

# ---------------------------------------------------------------------------
# Trigger fuer Muss-/Kann-Klassifikation (zeilenbezogen)
# ---------------------------------------------------------------------------

MUSS_TRIGGER = re.compile(_fold(
    r"zwingend|voraussetz|vorausgesetzt|erforderlich|unerlässlich|unabdingbar|"
    r"setzen\s+wir\s+voraus|notwendig|zwingend\s+erforderlich|verpflichtend"),
    re.IGNORECASE,
)
KANN_TRIGGER = re.compile(_fold(
    r"von\s+vorteil|wünschenswert|idealerweise|von\s+nutzen|bevorzugt|"
    r"nice[- ]to[- ]have|wäre\s+(?:ein\s+)?(?:plus|vorteil|schön)|vorteilhaft|"
    r"gerne\s+gesehen|gerne\s+auch"),
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Abschnitts-Erkennung (deutsche Anzeigen-Ueberschriften)
# ---------------------------------------------------------------------------

ABSCHNITT_HEADINGS = [
    ("aufgaben", re.compile(_fold(
        r"^\s*(ihre\s+aufgaben|ihr\s+aufgabengebiet|aufgaben(?:bereich|gebiet)?|"
        r"das\s+erwartet\s+sie|ihre\s+tätigkeiten|tätigkeitsfeld)\s*:?\s*$"),
        re.IGNORECASE)),
    ("profil", re.compile(_fold(
        r"^\s*(ihr\s+profil|ihre\s+qualifikation(?:en)?|das\s+bringen\s+sie\s+mit|"
        r"das\s+(?:sollten|solltest)\s+sie\s+mitbringen|wir\s+erwarten|"
        r"ihre\s+kenntnisse|anforderung(?:en|sprofil)?|was\s+sie\s+mitbringen)\s*:?\s*$"),
        re.IGNORECASE)),
    ("angebot", re.compile(_fold(
        r"^\s*(wir\s+bieten|das\s+bieten\s+wir|was\s+wir\s+(?:ihnen\s+)?bieten|"
        r"unser\s+angebot|ihre\s+(?:vorteile|benefits)|benefits)\s*:?\s*$"),
        re.IGNORECASE)),
]

# Bullet-Zeilen (Anzeigen-Listen).
BULLET_RE = re.compile(r"^\s*(?:[-•*▪–·●○]|\d+[.)])\s+(.*\S)\s*$")

# Meta-Muster.
MWD_RE = re.compile(r"\(\s*[mwd](?:\s*/\s*[mwd]){1,3}\s*\)|\(\s*m/w/d\s*\)", re.IGNORECASE)
# Breiter Geschlechtszusatz fuer Titel-Erkennung + -bereinigung: deckt (m/w/d)-Varianten
# UND ausgeschriebene Formen ab — (all genders), (alle Geschlechter), (divers), (gn), (a*).
GENDER_RE = re.compile(
    r"\([^)]*?(?:[mwfdx]\s*/\s*[mwfdx]|all\s+genders?|alle\s+geschlechter|divers|\bgn\b|\ba\*)"
    r"[^)]*?\)",
    re.IGNORECASE)


def _ist_titel_zeile(s: str) -> bool:
    """Heuristik: sieht die Zeile nach einem Stellentitel aus (kurz, kein Marketing-Satz)?
    Verhindert, dass Indeed-Anzeigen mit Firmen-Prosa als erster Zeile den Titel kapern."""
    if not s or len(s) > 70 or len(s.split()) > 9:
        return False
    # Saetze, Fragen und Label-/Abschnitts-Ueberschriften sind keine Stellentitel.
    return not (s.endswith((".", "?", "!", ":")) or ". " in s)
ANREDE_NAME_RE = re.compile(
    r"(?:ansprechpartner(?:in)?|kontakt|ihre\s+fragen|für\s+(?:rück)?fragen|"
    r"wenden\s+sie\s+sich\s+an)[^\n]{0,40}?\b(Herr|Frau)\s+([A-ZÄÖÜ][\wäöüß.-]+(?:\s+[A-ZÄÖÜ][\wäöüß.-]+)?)",
    re.IGNORECASE)
ABSCHLUSS_RE = re.compile(
    r"(?:abgeschlossene[ns]?\s+)?(?:(?:Berufs)?ausbildung|studium)\s+"
    r"(?:als|zum|zur|im\s+bereich|in\s+einem|in\s+einer)\s+([^\n,.;]{3,60})",
    re.IGNORECASE)
# Nachlaufende Trigger-/Fuellwoerter aus der Abschluss-Bezeichnung schneiden
# (z. B. "Industriemechaniker oder vergleichbar" / "... erforderlich").
ABSCHLUSS_CUT_RE = re.compile(
    r"\s+(?:oder|bzw\.?|sowie|erforderlich|vorausgesetzt|wünschenswert|zwingend|"
    r"notwendig|idealerweise|von\s+vorteil)\b.*$",
    re.IGNORECASE)
SCHICHT_RE = re.compile(_fold(r"schicht(?:arbeit|bereit|betrieb|system)|\d-schicht|drei-?schicht"), re.IGNORECASE)
REISE_RE = re.compile(_fold(r"reisebereit|dienstreise|reisetätigkeit"), re.IGNORECASE)


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------


def _clean(text: str) -> str:
    """Markdown-Marker entfernen (Zeilenstruktur bleibt)."""
    return re.sub(r"[*_`#>]", "", text)


def _zeilen(text: str):
    return text.split("\n")


def _bullet_text(zeile: str):
    """Bullet-Inhalt zurueckgeben, falls die Zeile ein Listenpunkt ist, sonst None."""
    m = BULLET_RE.match(zeile)
    return m.group(1).strip() if m else None


# ---------------------------------------------------------------------------
# Kern-API
# ---------------------------------------------------------------------------


def _finde_keywords(text: str) -> dict:
    """kategorie -> {kanon: [zeilen-indizes 0-basiert, an denen er vorkommt]}."""
    lines = [_fold(ln) for ln in _zeilen(text)]
    treffer = {kat: {} for kat in KEYWORD_KATALOG}
    for kat, eintraege in KEYWORD_KATALOG.items():
        for kanon, pattern in eintraege:
            rx = re.compile(_fold(pattern), re.IGNORECASE)
            zeilen = [i for i, ln in enumerate(lines) if rx.search(ln)]
            if zeilen:
                treffer[kat][kanon] = zeilen
    return treffer


def _klassifiziere(text: str, treffer: dict) -> dict:
    """Jeden gefundenen Kanon-Begriff nach Trigger seiner Zeile(n) in muss/kann
    einsortieren. Staerkstes Signal gewinnt (muss > kann); ohne Trigger = neutral
    (nicht gelistet)."""
    lines = [_fold(ln) for ln in _zeilen(text)]
    muss, kann = set(), set()
    for kat, kw in treffer.items():
        for kanon, zeilen in kw.items():
            sig = None  # None | "kann" | "muss"
            for i in zeilen:
                ln = lines[i]
                if MUSS_TRIGGER.search(ln):
                    sig = "muss"
                    break
                if KANN_TRIGGER.search(ln):
                    sig = "kann"
            if sig == "muss":
                muss.add(kanon)
            elif sig == "kann":
                kann.add(kanon)
    # muss hat Vorrang, falls ein Begriff in beiden Kontexten auftaucht
    kann -= muss
    return {"muss": sorted(muss), "kann": sorted(kann)}


def _abschnitte(text: str) -> dict:
    """Anzeige in erkannte Abschnitte segmentieren -> {kanon: [bullets]}."""
    lines = _zeilen(text)
    # Heading-Position je Zeile bestimmen (Erkennung auf gefoldeter Zeile,
    # Bullet-Text spaeter aus der Original-Zeile -> Umlaute bleiben im Output)
    marker = []  # (zeilen-idx, kanon)
    for i, ln in enumerate(lines):
        folded = _fold(ln)
        for kanon, rx in ABSCHNITT_HEADINGS:
            if rx.match(folded):
                marker.append((i, kanon))
                break
    abschnitte = {}
    for n, (start, kanon) in enumerate(marker):
        ende = marker[n + 1][0] if n + 1 < len(marker) else len(lines)
        bullets = []
        for j in range(start + 1, ende):
            bt = _bullet_text(lines[j])
            if bt:
                bullets.append(bt)
            elif bullets and not lines[j].strip():
                # Leerzeile nach Bullets = Abschnitt vorbei
                break
        if bullets:
            abschnitte.setdefault(kanon, []).extend(bullets)
    return abschnitte


def _meta(text: str) -> dict:
    lines = [ln for ln in _zeilen(text)]
    a = ABSCHLUSS_RE.search(text)
    abschluss = ABSCHLUSS_CUT_RE.sub("", a.group(1)).strip(" .,;:") if a else None
    # Titel-Erkennung in Stufen (robust gegen Indeed-Beschreibungen mit Marketing-Vorspann):
    #  1) erste Zeile mit Geschlechtszusatz (m/w/d | all genders | ...) = sicherster Titel
    #  2) sonst erste „titel-artige" Zeile (kurz, kein Satz) — Marketing-Prosa faellt raus
    #  3) Fallback: erkannter Abschluss/Beruf (z. B. „Industriemechaniker")
    titel = None
    for ln in lines:
        if GENDER_RE.search(ln) and len(ln.strip()) <= 90:
            titel = ln.strip()
            break
    if titel is None:
        for ln in lines:
            if _ist_titel_zeile(ln.strip()):
                titel = ln.strip()
                break
    if titel is None:
        titel = abschluss
    m = ANREDE_NAME_RE.search(text)
    ansprechpartner = (m.group(1) + " " + m.group(2)).strip(" .,;:") if m else None
    folded = _fold(text)
    return {
        "titel": titel,
        "ansprechpartner": ansprechpartner,
        "abschluss": abschluss,
        "schicht": bool(SCHICHT_RE.search(folded)),
        "reise": bool(REISE_RE.search(folded)),
    }


def parse(text: str) -> dict:
    """Stellenanzeige deterministisch parsen. Gibt strukturiertes Dict zurueck."""
    clean = _clean(text)
    treffer = _finde_keywords(clean)
    keywords = {kat: sorted(kw.keys()) for kat, kw in treffer.items()}
    anforderungen = _klassifiziere(clean, treffer)
    abschnitte = _abschnitte(clean)
    meta = _meta(clean)

    n_kw = sum(len(v) for v in keywords.values())
    return {
        "keywords": keywords,
        "anforderungen": anforderungen,
        "abschnitte": abschnitte,
        "meta": meta,
        "stats": {
            "keywords_gesamt": n_kw,
            "muss": len(anforderungen["muss"]),
            "kann": len(anforderungen["kann"]),
            "abschnitte": len(abschnitte),
        },
    }


def keywords_flach(result: dict) -> list:
    """Alle Kanon-Begriffe kategorieuebergreifend, dedupliziert + sortiert
    (= ATS-Keyword-Liste fuer den Abgleich gegen den CV)."""
    flach = set()
    for liste in result["keywords"].values():
        flach |= set(liste)
    return sorted(flach)


# ---------------------------------------------------------------------------
# CLI / Report
# ---------------------------------------------------------------------------

_KAT_LABEL = {
    "fertigung": "Fertigung/Verfahren",
    "mess_qs": "Messtechnik/QS",
    "steuerung_it": "Steuerung/IT",
    "normen": "Normen",
    "soft": "Soft Skills",
    "sprachen": "Sprachen",
}


def report(quelle: str, result: dict) -> str:
    m = result["meta"]
    s = result["stats"]
    out = []
    out.append("=== JDParserAgent — Anzeigen-Vokabular ===")
    out.append("Quelle: " + quelle)
    out.append("Titel: " + (m["titel"] or "(nicht erkannt)"))
    out.append("Ansprechpartner: " + (m["ansprechpartner"] or "(nicht erkannt)"))
    out.append("Abschluss: " + (m["abschluss"] or "(nicht erkannt)"))
    out.append("Schichtbereitschaft: " + ("ja" if m["schicht"] else "nein")
               + "  |  Reisebereitschaft: " + ("ja" if m["reise"] else "nein"))
    out.append("")
    out.append("Keywords (" + str(s["keywords_gesamt"]) + "):")
    for kat, liste in result["keywords"].items():
        if liste:
            out.append("  " + _KAT_LABEL[kat] + ": " + ", ".join(liste))
    out.append("")
    out.append("MUSS (" + str(s["muss"]) + "): "
               + (", ".join(result["anforderungen"]["muss"]) or "—"))
    out.append("KANN (" + str(s["kann"]) + "): "
               + (", ".join(result["anforderungen"]["kann"]) or "—"))
    out.append("")
    if result["abschnitte"]:
        out.append("Abschnitte:")
        for kanon, bullets in result["abschnitte"].items():
            out.append("  [" + kanon + "] " + str(len(bullets)) + " Punkt(e)")
    else:
        out.append("Abschnitte: (keine Standard-Ueberschriften erkannt)")
    return "\n".join(out)


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("--")]
    flags = {a for a in argv[1:] if a.startswith("--")}
    if not args:
        print("Aufruf: python jdparser.py <anzeige-datei> [--json]", file=sys.stderr)
        return 2
    pfad = args[0]
    try:
        with open(pfad, "r", encoding="utf-8") as fh:
            text = fh.read()
    except OSError as e:
        print("FEHLER: Datei nicht lesbar: " + str(e), file=sys.stderr)
        return 2

    result = parse(text)
    if "--json" in flags:
        print(json.dumps({"datei": pfad, **result, "ats_keywords": keywords_flach(result)},
                         ensure_ascii=False, indent=2))
    else:
        print(report(pfad, result))
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    sys.exit(main(sys.argv))

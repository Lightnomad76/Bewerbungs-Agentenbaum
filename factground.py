# -*- coding: utf-8 -*-
"""FactGroundingAgent — deterministisches, offline Fact-Grounding fuer generierte
Bewerbungstexte (Anschreiben / Lebenslauf).

Pipeline-Rolle (Agenten-Roadmap E-B): mechanischer Schutz gegen erfundene CV-Fakten
(§3.3). Grundsatz wie CriticAgent: der Agent FLAGGT, aendert nichts (read-only Scope).

Wahrheitsquelle = die CV-Stammdaten selbst (die Daten, aus denen der Generator die
Dokumente baut). Sie werden REINGEFUETTERT (nicht aus jobprofil.yaml gelesen — das ist
das Such-Profil und enthaelt KEINE biografischen Fakten). Damit ist "gegroundet" exakt
definiert als "rueckfuehrbar auf die Daten, die das Dokument erzeugt haben" — kein
zweites Daten-Duplikat, kein Drift. Analog zu critic.pruefe(text): hier
pruefe(text, fakten), und der lokale Generator uebergibt seine Stammdaten.

Methode = "Known-Facts-Whitelist": aus der Wahrheitsquelle wird ein Fakten-Vokabular
gezogen (Firmen mit Rechtsform, Zahlen/Jahre, Akronyme). Der generierte Text wird auf
*fakten-artige* Tokens gescannt; jedes NICHT rueckfuehrbare wird geflaggt.

EHRLICHE GRENZE (deterministisch, keine LLM): Erfindung laesst sich nicht *beweisen*,
nur "nicht in den bekannten Fakten" feststellen. Darum:
- FEHLER  = starkes Erfindungs-Signal: Firma mit Rechtsform, die NICHT in der
            Historie steht; Erfahrungs-Dauer ("N Jahre"), deren Zahl nicht in den
            Stammdaten vorkommt.
- WARNUNG = schwaecheres Signal zum Pruefen: Akronym / Jahreszahl ohne Beleg.
Was KEIN Eigenname/keine Zahl ist (z. B. eine frei erfundene Taetigkeit in Prosa),
faengt dieser Agent bewusst NICHT — das ist deterministisch nicht erkennbar und wird
ehrlich nicht behauptet.

CLI:   py -3.11 factground.py <text-datei> <wahrheitsquelle...> [--json]
       (erste Datei = zu pruefender Text; weitere Dateien = Stammdaten/Wahrheit)
API:   from factground import sammle_fakten, pruefe, hat_fehler
       fakten = sammle_fakten(EXPERIENCE, WEITERE, SAMSON, KURZPROFIL, ...)
       res = pruefe(anschreiben_text, fakten); hat_fehler(res) -> bool
"""
from __future__ import annotations

import re
import sys
import json
import bisect

# ---------------------------------------------------------------------------
# Muster
# ---------------------------------------------------------------------------

# Rechtsformen, die eine Firmen-Nennung markieren (Reihenfolge: laengste zuerst).
RECHTSFORM = r"(?:Aktiengesellschaft|GmbH\s*&\s*Co\.?\s*KG|GmbH|mbH|gGmbH|AG|SE|KGaA|KG|GbR|UG|e\.\s*V\.|e\.\s*K\.)"

# Firma = Lauf aus Gross-Wort-Tokens (inkl. Binnen-&/-und/Bindestrich) direkt vor der
# Rechtsform. Lowercase-Woerter (bei/der/und nach Praeposition) brechen den Lauf.
FIRMA_RE = re.compile(
    r"((?:[A-ZÄÖÜ][\wäöüß.-]*)(?:[\s-]+(?:[A-ZÄÖÜ][\wäöüß.-]*|und|&))*)\s+" + RECHTSFORM + r"\b"
)

# Akronyme: kurze Vollgross-Tokens (2-5) + CEFR-Sprachlevel (A1..C2).
AKRONYM_RE = re.compile(r"\b[A-ZÄÖÜ]{2,5}\b")
CEFR_RE = re.compile(r"\b[ABC][12]\b")

# Jahreszahlen + Erfahrungs-Dauer.
JAHR_RE = re.compile(r"\b(?:19|20)\d{2}\b")
DAUER_RE = re.compile(r"\b(\d{1,2})\s*Jahre[n]?\b", re.IGNORECASE)

# Alle Ganzzahlen (fuer den Stammdaten-Zahlenvorrat).
ZAHL_RE = re.compile(r"\b\d{1,4}\b")

# Rechtsform-Tokens NICHT als Akronym flaggen.
_RECHTSFORM_TOKENS = {"ag", "se", "kg", "gbr", "ug", "mbh", "kgaa"}

# Generische Firmen-Wortbestandteile: taugen NICHT als Unterscheidungsmerkmal
# (sonst groundet eine erfundene "Mueller Service GmbH" ueber das Wort "Service").
_FIRMA_STOPWORDS = {
    "gmbh", "mbh", "ggmbh", "ag", "se", "kg", "kgaa", "gbr", "ug",
    "aktiengesellschaft", "co", "und", "der", "die", "das", "den", "dem",
    "service", "personal", "industries", "industrie", "technik", "technologie",
    "technologies", "system", "systeme", "fördersysteme", "foerdersysteme",
    "automatisations", "maschinen", "messtechnik", "metallwarenfabrik",
    "textilmaschinenfabrik", "group", "gruppe", "holding", "international",
}

# Akronyme, die generisch/legitim sind und nie geflaggt werden (keine CV-Fakten).
_AKRONYM_ALLOWLIST = {"DIN", "ISO", "EU", "DE", "PLZ", "PDF", "URL", "USB", "PC", "IT"}


# ---------------------------------------------------------------------------
# Wahrheitsquelle einsammeln
# ---------------------------------------------------------------------------


def _flatten(obj):
    """Beliebig verschachtelte str/list/tuple zu einem Text zusammenfuehren."""
    if obj is None:
        return ""
    if isinstance(obj, str):
        return obj
    if isinstance(obj, (list, tuple)):
        return "\n".join(_flatten(x) for x in obj)
    return str(obj)


def _firma_tokens(name: str) -> set:
    """Unterscheidungs-Tokens eines Firmennamens (lowercase, ohne Stopwords, len>=3)."""
    toks = re.findall(r"[A-Za-zÄÖÜäöüß]{3,}", name.lower())
    return {t for t in toks if t not in _FIRMA_STOPWORDS}


def sammle_fakten(*quellen) -> dict:
    """Aus den CV-Stammdaten (beliebig verschachtelt) das Fakten-Vokabular bauen."""
    text = "\n".join(_flatten(q) for q in quellen)

    firma_tokens = set()
    for m in FIRMA_RE.finditer(text):
        firma_tokens |= _firma_tokens(m.group(1))

    akronyme = {a for a in AKRONYM_RE.findall(text) if a.lower() not in _RECHTSFORM_TOKENS}
    akronyme |= set(CEFR_RE.findall(text))

    zahlen = {int(z) for z in ZAHL_RE.findall(text)}

    return {
        "firma_tokens": firma_tokens,
        "akronyme": akronyme,
        "zahlen": zahlen,
        "roh": text,
    }


# ---------------------------------------------------------------------------
# Hilfsfunktionen (Zeilen-Mapping wie critic)
# ---------------------------------------------------------------------------


def _clean(text: str) -> str:
    """Markdown-Marker entfernen, Zeilenstruktur erhalten (Zeilennummern bleiben gueltig)."""
    return re.sub(r"[*_`#>]", "", text)


def _line_starts(text: str):
    starts = [0]
    for m in re.finditer(r"\n", text):
        starts.append(m.end())
    return starts


def _finding(kategorie, schwere, nachricht, zeile=None, fundstelle=None):
    return {"kategorie": kategorie, "schwere": schwere, "nachricht": nachricht,
            "zeile": zeile, "fundstelle": fundstelle}


# ---------------------------------------------------------------------------
# Kern-API
# ---------------------------------------------------------------------------


def pruefe(text: str, fakten: dict) -> dict:
    """Generierten Text gegen die Fakten pruefen. Gibt {findings, stats} zurueck."""
    clean = _clean(text)
    starts = _line_starts(clean)

    def zeile_von(pos: int) -> int:
        return bisect.bisect_right(starts, pos)  # 1-basiert

    findings = []
    n_firmen = n_akr = n_jahre = n_dauer = 0

    # --- 1) Firmen mit Rechtsform -> nicht in Historie = FEHLER ---------------
    gesehen_firma = set()
    for m in FIRMA_RE.finditer(clean):
        roh_name = m.group(0).strip()
        toks = _firma_tokens(m.group(1))
        if not toks:
            continue  # nur Stopwords (z. B. "der GmbH") -> nicht beurteilbar
        n_firmen += 1
        if toks & fakten["firma_tokens"]:
            continue  # gegroundet
        key = roh_name.lower()
        if key in gesehen_firma:
            continue
        gesehen_firma.add(key)
        findings.append(_finding(
            "firma", "fehler",
            "Firma '" + roh_name + "' nicht in den CV-Stammdaten — erfunden / falsch?",
            zeile=zeile_von(m.start()), fundstelle=roh_name))

    # --- 2) Erfahrungs-Dauer ("N Jahre") -> Zahl nicht in Stammdaten = FEHLER -
    for m in DAUER_RE.finditer(clean):
        n_dauer += 1
        n = int(m.group(1))
        if n in fakten["zahlen"]:
            continue
        findings.append(_finding(
            "dauer", "fehler",
            "Dauer '" + m.group(0).strip() + "' nicht durch die Stammdaten gedeckt "
            "(keine passende Zahl) — Erfahrung erfunden / aufgerundet?",
            zeile=zeile_von(m.start()), fundstelle=m.group(0).strip()))

    # --- 3) Akronyme -> nicht belegt = WARNUNG --------------------------------
    gesehen_akr = set()
    for m in AKRONYM_RE.finditer(clean):
        akr = m.group(0)
        if akr.lower() in _RECHTSFORM_TOKENS or akr in _AKRONYM_ALLOWLIST:
            continue
        n_akr += 1
        if akr in fakten["akronyme"] or akr in gesehen_akr:
            continue
        gesehen_akr.add(akr)
        findings.append(_finding(
            "akronym", "warnung",
            "Akronym '" + akr + "' nicht in den Stammdaten belegt — pruefen "
            "(Tippfehler / nicht nachgewiesene Qualifikation?)",
            zeile=zeile_von(m.start()), fundstelle=akr))

    # --- 4) Jahreszahlen -> nicht in Stammdaten = WARNUNG ---------------------
    gesehen_jahr = set()
    for m in JAHR_RE.finditer(clean):
        n_jahre += 1
        jahr = int(m.group(0))
        if jahr in fakten["zahlen"] or jahr in gesehen_jahr:
            continue
        gesehen_jahr.add(jahr)
        findings.append(_finding(
            "jahr", "warnung",
            "Jahreszahl '" + m.group(0) + "' kommt in den Stammdaten nicht vor — pruefen",
            zeile=zeile_von(m.start()), fundstelle=m.group(0)))

    n_fehler = sum(1 for f in findings if f["schwere"] == "fehler")
    n_warn = sum(1 for f in findings if f["schwere"] == "warnung")
    return {
        "findings": findings,
        "stats": {"fehler": n_fehler, "warnungen": n_warn,
                  "geprueft": {"firmen": n_firmen, "akronyme": n_akr,
                               "jahre": n_jahre, "dauern": n_dauer}},
    }


def hat_fehler(result: dict) -> bool:
    """True, wenn mind. ein FEHLER vorliegt (Pipeline-Gate)."""
    return result["stats"]["fehler"] > 0


# ---------------------------------------------------------------------------
# CLI / Report
# ---------------------------------------------------------------------------

_SCHWERE_LABEL = {"fehler": "FEHLER", "warnung": "WARNUNG"}


def report(quelle: str, result: dict) -> str:
    s = result["stats"]
    g = s["geprueft"]
    out = []
    out.append("=== FactGroundingAgent — Fakten-Abgleich gegen CV-Stammdaten ===")
    out.append("Text: " + quelle)
    out.append("Geprueft: " + str(g["firmen"]) + " Firmennennung(en), "
               + str(g["dauern"]) + " Dauer-Angabe(n), "
               + str(g["akronyme"]) + " Akronym(e), " + str(g["jahre"]) + " Jahreszahl(en)")
    out.append("")
    for schwere in ("fehler", "warnung"):
        gruppe = [f for f in result["findings"] if f["schwere"] == schwere]
        if not gruppe:
            continue
        out.append(_SCHWERE_LABEL[schwere] + " (" + str(len(gruppe)) + "):")
        for f in gruppe:
            ort = "  (Zeile " + str(f["zeile"]) + ")" if f.get("zeile") else ""
            out.append("  [" + f["kategorie"] + "] " + f["nachricht"] + ort)
            if f.get("fundstelle"):
                out.append("        -> '" + f["fundstelle"] + "'")
        out.append("")
    if s["fehler"] == 0:
        out.append("GRUEN: keine nicht-rueckfuehrbaren Fakten (" + str(s["warnungen"])
                   + " Warnung(en) — zur Durchsicht).")
    else:
        out.append("ROT: " + str(s["fehler"]) + " nicht gedeckte Fakten, "
                   + str(s["warnungen"]) + " Warnung(en) — vor Versand pruefen.")
    return "\n".join(out)


def _read(pfad: str) -> str:
    with open(pfad, "r", encoding="utf-8") as fh:
        return fh.read()


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("--")]
    flags = {a for a in argv[1:] if a.startswith("--")}
    if len(args) < 2:
        print("Aufruf: py -3.11 factground.py <text-datei> <wahrheitsquelle...> [--json]",
              file=sys.stderr)
        return 2
    pfad = args[0]
    try:
        text = _read(pfad)
        quellen = [_read(p) for p in args[1:]]
    except OSError as e:
        print("FEHLER: Datei nicht lesbar: " + str(e), file=sys.stderr)
        return 2

    fakten = sammle_fakten(*quellen)
    result = pruefe(text, fakten)
    if "--json" in flags:
        print(json.dumps({"datei": pfad, **result}, ensure_ascii=False, indent=2))
    else:
        print(report(pfad, result))
    return 1 if hat_fehler(result) else 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    sys.exit(main(sys.argv))

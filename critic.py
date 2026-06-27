# -*- coding: utf-8 -*-
"""CriticAgent — deterministische, offline Stil-/Pflichtfeld-Pruefung fuer Anschreiben.

Pipeline-Rolle (Agenten-Roadmap E-A): schaltet zwischen Writer und ReportAgent.
Prueft einen generierten Anschreiben-Text gegen die Business-Stil-Checkliste
(state/agenten_roadmap.md, Abschnitt B) — KEINE LLM-API, rein regelbasiert.

Grundsatz: der Critic flaggt, aendert nichts (read-only Scope des Projekts).
- FEHLER  = harte Stil-/Pflichtfeld-Verstoesse (Floskel-Blacklist, fehlende Pflichtfelder)
- WARNUNG = heuristische Hinweise (Selbst-Adjektive ohne Beleg, Laenge, Aufwaerm-Erstsatz)

Eine Heuristik kann 'Beleg' nicht deterministisch verifizieren -> solche Punkte sind
bewusst WARNUNG (pruefen), nicht FEHLER. Ehrlich gelabelt.

CLI:   py -3.11 critic.py <pfad-zum-anschreiben>     (Report + exit 1 bei FEHLER)
       py -3.11 critic.py <pfad> --json              (maschinenlesbar)
API:   from critic import pruefe, hat_fehler
       res = pruefe(text); hat_fehler(res) -> bool
"""
from __future__ import annotations

import re
import sys
import json
import bisect

# ---------------------------------------------------------------------------
# Regel-Tabellen (Quelle: agenten_roadmap.md Abschnitt B)
# ---------------------------------------------------------------------------

# Verbotene Floskeln. (regex, schwere, klartext) — \s+ matcht auch Zeilenumbrueche.
FLOSKELN = [
    (r"hiermit\s+bewerbe\s+ich\s+mich",
     "fehler", "Hiermit bewerbe ich mich ..."),
    (r"mit\s+gro(?:ß|ss)em\s+interesse\s+habe\s+ich\s+ihre\s+(?:stellen)?anzeige\s+gelesen",
     "fehler", "Mit grossem Interesse habe ich Ihre (Stellen-)Anzeige gelesen"),
    (r"auf\s+der\s+suche\s+nach\s+einer\s+neuen\s+herausforderung",
     "fehler", "... auf der Suche nach einer neuen Herausforderung"),
    (r"über\s+eine\s+einladung\s+würde\s+ich\s+mich\s+(?:sehr\s+)?freuen",
     "fehler", "Ueber eine Einladung wuerde ich mich (sehr) freuen"),
    # weiche Varianten / haeufige Aufwaerm-Floskeln -> Warnung (Kontext-abhaengig legitim)
    (r"mit\s+gro(?:ß|ss)em\s+interesse",
     "warnung", "Aufwaerm-Floskel 'mit grossem Interesse'"),
    (r"(?:würde\s+ich\s+mich|freue\s+ich\s+mich)\s+(?:sehr\s+)?(?:über|auf|freuen)",
     "warnung", "Floskel-Variante 'freue/wuerde ich mich (sehr)'"),
]

# Selbst-Adjektive, die laut Checkliste an Station/Taetigkeit/Zahl gebunden gehoeren.
# Wortstamm-Match (Flexion erlaubt: teamfaehig/teamfaehige/teamfaehiger ...).
SELBST_ADJEKTIVE = [
    "teamfähig", "zielstrebig", "kreativ", "souverän",
    "selbstständig", "selbständig", "strukturiert", "gewissenhaft",
    "engagiert", "motiviert", "belastbar", "flexibel", "zuverlässig",
]

# Aufwaerm-Muster am Satzanfang (der erste Satz muss in ~7 Sek. tragen).
ERSTSATZ_AUFWAERMER = re.compile(
    r"^\s*(hiermit\b|bezug\s*nehmend|mit\s+gro(?:ß|ss)em\s+interesse|"
    r"wie\s+(?:sie|aus)|ich\s+möchte\s+mich\s+(?:hiermit|bei\s+ihnen)\s+bewerben)",
    re.IGNORECASE,
)

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
# Telefon: Stichwort ODER eine Ziffernfolge, die nach Rufnummer aussieht.
TEL_RE = re.compile(r"(tel\.?|telefon|mobil|handy)\b", re.IGNORECASE)
TEL_NUM_RE = re.compile(r"\b0\d[\d\s/().+-]{6,}\d\b")
ANREDE_RE = re.compile(r"sehr\s+geehrte[rs]?\s+(herr|frau|damen)", re.IGNORECASE)
ANREDE_OHNE_NAME_RE = re.compile(r"sehr\s+geehrte\s+damen\s+und\s+herren", re.IGNORECASE)
GRUSS_RE = re.compile(r"mit\s+freundlichen\s+grü(?:ß|ss)en", re.IGNORECASE)
DATUM_RE = re.compile(r"\b\d{1,2}\.\s*\d{1,2}\.\s*\d{2,4}\b")
BETREFF_RE = re.compile(r"\bbewerbung\s+(?:als|um|auf)\b", re.IGNORECASE)

# Laengen-Schwellen (Anschreiben ~ 1 Seite).
WORT_MAX = 500
WORT_MIN = 120
ERSTSATZ_WORT_MAX = 45

# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------


def _clean(text: str) -> str:
    """Markdown-Marker (*, _, `, #, >) entfernen — Zeilenstruktur bleibt erhalten,
    damit Zeilennummern zum Original passen."""
    return re.sub(r"[*_`#>]", "", text)


def _line_starts(text: str):
    """Liste der Zeichen-Offsets, an denen jede Zeile beginnt (fuer pos -> Zeile)."""
    starts = [0]
    for m in re.finditer(r"\n", text):
        starts.append(m.end())
    return starts


def _woerter(text: str) -> int:
    return len(re.findall(r"\b[\wäöüß]+\b", text, re.IGNORECASE))


def _finding(kategorie, schwere, nachricht, zeile=None, fundstelle=None):
    return {"kategorie": kategorie, "schwere": schwere, "nachricht": nachricht,
            "zeile": zeile, "fundstelle": fundstelle}


def _erster_body_satz(clean: str):
    """Ersten inhaltlichen Satz NACH der Anrede zurueckgeben (fuer 7-Sek-Check)."""
    lines = clean.split("\n")
    anrede_idx = None
    for i, ln in enumerate(lines):
        if ANREDE_RE.search(ln):
            anrede_idx = i
            break
    if anrede_idx is None:
        return None, None
    # erster nicht-leerer Absatz nach der Anrede
    for j in range(anrede_idx + 1, len(lines)):
        if lines[j].strip():
            absatz = lines[j].strip()
            satz = re.split(r"(?<=[.!?])\s", absatz, maxsplit=1)[0]
            return satz, j + 1  # 1-basierte Zeile
    return None, None


# ---------------------------------------------------------------------------
# Kern-API
# ---------------------------------------------------------------------------


def pruefe(text: str) -> dict:
    """Anschreiben-Text deterministisch pruefen. Gibt {findings, stats} zurueck."""
    clean = _clean(text)
    starts = _line_starts(clean)

    def zeile_von(pos: int) -> int:
        return bisect.bisect_right(starts, pos)  # 1-basiert

    findings = []

    # --- 1) Floskel-Blacklist -------------------------------------------------
    for pattern, schwere, label in FLOSKELN:
        for m in re.finditer(pattern, clean, re.IGNORECASE):
            findings.append(_finding(
                "floskel", schwere,
                "Floskel: " + label,
                zeile=zeile_von(m.start()),
                fundstelle=m.group(0).strip()))

    # --- 2) Unbelegte Selbst-Adjektive (Heuristik -> Warnung) -----------------
    for adj in SELBST_ADJEKTIVE:
        for m in re.finditer(r"\b" + adj + r"\w*", clean, re.IGNORECASE):
            findings.append(_finding(
                "adjektiv", "warnung",
                "Selbst-Adjektiv '" + m.group(0) + "' — an Station/Taetigkeit/Zahl "
                "binden (belegen statt behaupten)",
                zeile=zeile_von(m.start()),
                fundstelle=m.group(0)))

    # --- 3) Pflichtfelder -----------------------------------------------------
    if not ANREDE_RE.search(clean):
        findings.append(_finding("pflichtfeld", "fehler",
                                 "Anrede fehlt (z. B. 'Sehr geehrte Frau ...')"))
    elif ANREDE_OHNE_NAME_RE.search(clean):
        findings.append(_finding("pflichtfeld", "warnung",
                                 "Anrede ohne Namen ('Sehr geehrte Damen und Herren') — "
                                 "Ansprechpartner:in namentlich anreden, wenn bekannt"))
    if not GRUSS_RE.search(clean):
        findings.append(_finding("pflichtfeld", "fehler",
                                 "Grussformel 'Mit freundlichen Gruessen' fehlt"))
    if not (EMAIL_RE.search(clean) or TEL_RE.search(clean) or TEL_NUM_RE.search(clean)):
        findings.append(_finding("pflichtfeld", "fehler",
                                 "Kontaktdaten fehlen (E-Mail oder Telefon)"))
    if not DATUM_RE.search(clean):
        findings.append(_finding("pflichtfeld", "fehler",
                                 "Datum fehlt (DIN 5008: rechtsbuendig, z. B. 'Ort, den TT.MM.JJJJ')"))
    if not BETREFF_RE.search(clean):
        findings.append(_finding("pflichtfeld", "warnung",
                                 "Kein erkennbarer Betreff ('Bewerbung als ...') — "
                                 "Betreff sollte fett oben stehen"))

    # --- 4) Laenge -------------------------------------------------------------
    n_woerter = _woerter(clean)
    if n_woerter > WORT_MAX:
        findings.append(_finding("laenge", "warnung",
                                 "Sehr lang (" + str(n_woerter) + " Woerter) — Anschreiben "
                                 "i. d. R. 1 Seite (~ 250-400 Woerter)"))
    elif n_woerter < WORT_MIN:
        findings.append(_finding("laenge", "warnung",
                                 "Sehr kurz (" + str(n_woerter) + " Woerter) — wirkt duenn "
                                 "(Richtwert ~ 250-400)"))

    # --- 5) Erster Satz / 7-Sekunden-Regel ------------------------------------
    satz, zeile = _erster_body_satz(clean)
    if satz:
        if ERSTSATZ_AUFWAERMER.match(satz):
            findings.append(_finding("erstsatz", "warnung",
                                     "Erster Satz ist eine Aufwaerm-Floskel — direkt mit Substanz "
                                     "(Eignung/Bezug) einsteigen", zeile=zeile,
                                     fundstelle=satz[:80]))
        elif _woerter(satz) > ERSTSATZ_WORT_MAX:
            findings.append(_finding("erstsatz", "warnung",
                                     "Erster Satz sehr lang (" + str(_woerter(satz)) + " Woerter) — "
                                     "traegt nicht in 7 Sek.; kuerzen/teilen", zeile=zeile,
                                     fundstelle=satz[:80]))

    n_fehler = sum(1 for f in findings if f["schwere"] == "fehler")
    n_warn = sum(1 for f in findings if f["schwere"] == "warnung")
    return {
        "findings": findings,
        "stats": {"woerter": n_woerter, "fehler": n_fehler, "warnungen": n_warn},
    }


def hat_fehler(result: dict) -> bool:
    """True, wenn mind. ein FEHLER vorliegt (Pipeline-Gate)."""
    return result["stats"]["fehler"] > 0


# ---------------------------------------------------------------------------
# CLI / Report
# ---------------------------------------------------------------------------

_SCHWERE_LABEL = {"fehler": "FEHLER", "warnung": "WARNUNG"}


def report(pfad: str, result: dict) -> str:
    s = result["stats"]
    out = []
    out.append("=== CriticAgent — Stil-/Pflichtfeld-Pruefung ===")
    out.append("Datei: " + pfad + "  (" + str(s["woerter"]) + " Woerter)")
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
        out.append("GRUEN: keine FEHLER (" + str(s["warnungen"]) + " Warnung(en) — zur Durchsicht).")
    else:
        out.append("ROT: " + str(s["fehler"]) + " Fehler, " + str(s["warnungen"]) + " Warnung(en).")
    return "\n".join(out)


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("--")]
    flags = {a for a in argv[1:] if a.startswith("--")}
    if not args:
        print("Aufruf: py -3.11 critic.py <pfad-zum-anschreiben> [--json]", file=sys.stderr)
        return 2
    pfad = args[0]
    try:
        with open(pfad, "r", encoding="utf-8") as fh:
            text = fh.read()
    except OSError as e:
        print("FEHLER: Datei nicht lesbar: " + str(e), file=sys.stderr)
        return 2

    result = pruefe(text)
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

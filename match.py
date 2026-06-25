"""match.py — MatchAgent (Etappe 2): offline, deterministisches Keyword-Scoring.

Bewertet die Treffer-Dicts des ReportAgent gegen `profil_fuer_matching`:
  skills_muss         -> K.o.-Kriterien (fehlt eines -> ko=True + starker Malus)
  skills_kann         -> Bonus
  ausschluss_keywords -> Malus (z.B. Praktikum/Werkstudent)
  gehalt_min_eur_jahr -> sanfter Malus, wenn die Anzeige darunter liegt (best-effort)

Design-Entscheidung K.o.: ein fehlendes Muss-Skill setzt `ko=True` und zieht den
Treffer per Malus klar nach unten — er wird aber NICHT gelöscht. Begründung:
reines Keyword-Matching auf Stellentexte ist spröde (eine passende Anzeige nennt
"Montage nach Zeichnung" selten wörtlich); hartes Wegfiltern würde echte Treffer
verstecken. Für ein read-only Vorschlags-Tool ist Flag + Nach-unten-Sortieren
sicherer. Umstellen auf hartes Filtern wäre ein Einzeiler in `bewerte_treffer`.

Reines Substring-Matching (case-/whitespace-normalisiert), kein Netz, keine API.
Deterministisch und nachvollziehbar: jeder Treffer trägt sein `match`-Detail.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# Gewichte (bewusst einfach/erklärbar; zentral justierbar)
GEWICHT_MUSS = 10
GEWICHT_KANN = 3
MALUS_AUSSCHLUSS = 8
MALUS_KO = 100          # hält ko-Treffer klar unter den vollständigen
MALUS_GEHALT = 5

# Felder, deren Text für Skill-Scoring durchsucht wird (breit = gewollt)
TEXT_FELDER = ("title", "company", "location", "description", "such_titel")
# Ausschluss nur hier prüfen: der Job-TYP (Praktikum/Azubi/Werkstudent) steht im
# Titel. Anforderungen im Fließtext ("abgeschlossene Ausbildung", einzureichende
# "Praktikumsbescheinigungen") sind sonst False-Positives, die echte Stellen verbannen.
AUSSCHLUSS_FELDER = ("title", "such_titel")


@dataclass
class MatchProfil:
    skills_muss: list[str]
    skills_kann: list[str]
    ausschluss_keywords: list[str]
    gehalt_min_eur_jahr: int | None


def _norm(s: object) -> str:
    """Lowercase + Whitespace auf ein Leerzeichen normalisieren."""
    return re.sub(r"\s+", " ", str(s)).strip().lower()


def _feld_text(t: dict, felder: tuple[str, ...]) -> str:
    """Normalisierter Text aus den angegebenen Feldern (Listen wie such_titel mit)."""
    teile: list[str] = []
    for f in felder:
        v = t.get(f)
        if v is None:
            continue
        if isinstance(v, (list, tuple)):
            teile.extend(str(x) for x in v)
        else:
            teile.append(str(v))
    return _norm(" ".join(teile))


def _treffer(text: str, skills: list[str]) -> list[str]:
    """Skills, deren normalisierte Form als Substring im Text vorkommt."""
    return [s for s in skills if s and _norm(s) in text]


def bewerte_einen(t: dict, pm: MatchProfil) -> dict:
    """Gibt eine Kopie von t mit zusätzlichem 'match'-Block (score, ko, Detail) zurück."""
    text = _feld_text(t, TEXT_FELDER)
    titel_text = _feld_text(t, AUSSCHLUSS_FELDER)
    muss_treffer = _treffer(text, pm.skills_muss)
    muss_fehlt = [s for s in pm.skills_muss if s and _norm(s) not in text]
    kann_treffer = _treffer(text, pm.skills_kann)
    aus_treffer = _treffer(titel_text, pm.ausschluss_keywords)  # nur im Titel

    score = (
        len(muss_treffer) * GEWICHT_MUSS
        + len(kann_treffer) * GEWICHT_KANN
        - len(aus_treffer) * MALUS_AUSSCHLUSS
    )

    ko = bool(muss_fehlt)
    if ko:
        score -= MALUS_KO

    gehalt_unter_min = False
    if pm.gehalt_min_eur_jahr is not None:
        betrag = t.get("max_amount")
        if betrag is None:
            betrag = t.get("min_amount")
        if betrag is not None:
            try:
                if float(betrag) < float(pm.gehalt_min_eur_jahr):
                    gehalt_unter_min = True
                    score -= MALUS_GEHALT
            except (TypeError, ValueError):
                pass  # unparsebarer Betrag -> neutral

    out = dict(t)
    out["match"] = {
        "score": score,
        "ko": ko,
        "muss_treffer": muss_treffer,
        "muss_fehlt": muss_fehlt,
        "kann_treffer": kann_treffer,
        "ausschluss_treffer": aus_treffer,
        "gehalt_unter_min": gehalt_unter_min,
    }
    return out


def bewerte_treffer(treffer: list[dict], pm: MatchProfil) -> list[dict]:
    """Bewertet alle Treffer und sortiert: vollständige (ko=False) zuerst,
    innerhalb nach Score absteigend."""
    bewertet = [bewerte_einen(t, pm) for t in treffer]
    bewertet.sort(key=lambda t: (t["match"]["ko"], -t["match"]["score"]))
    return bewertet

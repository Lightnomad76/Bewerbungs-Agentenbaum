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

import math
import re
from dataclasses import dataclass

# Gewichte (bewusst einfach/erklärbar; zentral justierbar)
GEWICHT_MUSS = 10
GEWICHT_KANN = 3
MALUS_AUSSCHLUSS = 8
MALUS_KO = 100          # hält ko-Treffer klar unter den vollständigen
MALUS_GEHALT = 5
MALUS_NICHT_QUALIFIZIERT = 50  # Job verlangt Studium ohne Ausbildungs-/Quereinsteiger-Pfad

# Kern-Beruf-Wörter (v13): ein ECHTER Job-Titel mit einem dieser Wörter = Trade/QS-Job,
# für den der Bewerber qualifiziert ist -> NIE wegen "Studium verlangt" abgewertet.
# (NICHT gegen such_titel prüfen — das ist unsere eigene Query.)
KERN_BERUF = [
    "mechaniker", "mechatronik", "schlosser", "industriemechan", "zerspan", "cnc",
    "instandhalt", "wartung", "montage", "monteur", "prüf", "güteprüf", "qualität",
    "fertigung", "produktion", "maschinen", "anlagen", "metall", "schweiß", "löt",
    "elektr", "werker", "feinwerk", "techniker", "hydraulik", "pneumatik",
]

# Qualifikations-Gate (v13, User-Modell): Büro-/Nicht-Trade-Jobs NICHT pauschal raus.
# Abwertung NUR, wenn ein Job ein Studium VERLANGT und KEINEN Ausbildungs- oder
# Quereinsteiger-Pfad bietet — denn dafür fehlt die formale Qualifikation (kein
# abgeschlossenes Studium; Journalismus-Studium nicht beendet). Quereinsteiger-Jobs
# und Jobs ohne Studienzwang bleiben (auch Büro), Trade-Jobs sowieso.
# Studium-Anforderung breit erkennen (freistehend, mit Adjektiv dazwischen, Uni/Hochschul/Grade).
STUDIUM_RE = re.compile(
    r"\bstudium\b|studiums\b|studien(?:gang|abschluss)|hochschul|universit|"
    r"\bbachelor\b|\bmaster\b|\bdiplom\b|akademische[rn]?\s+(?:grad|abschluss)|"
    r"\bm\.?\s?sc\b|\bb\.?\s?sc\b|\bmba\b",
    re.IGNORECASE)
# Alternativ-Pfad: Quereinsteiger ODER echte Ausbildungs-Alternative (NICHT bloßes
# "Weiterbildung" -> deshalb präzise, kein nacktes "ausbildung"-Substring).
ALT_PFAD_RE = re.compile(
    r"quereinsteig|kein\s+studium|auch\s+ohne\s+studium|ohne\s+(?:abgeschlossenes\s+)?studium|"
    r"berufserfahrung\s+statt\s+studium|ungelernt|"
    r"(?:berufs)?ausbildung\s+oder\s+(?:ein\s+)?studium|"
    r"studium\s+oder\s+(?:eine\s+|eine\s+vergleichbare\s+|vergleichbare\s+)?(?:berufs)?ausbildung|"
    r"abgeschlossene[rn]?\s+(?:berufs)?ausbildung",
    re.IGNORECASE)

# Distanz-Scoring (v13, deterministisch/offline — keine API/Geocoding-Calls).
# Bänder relativ zum Profil-Umkreis: nah = mehr Bonus, weit = Malus. Ein
# keyword-starker Treffer weit weg soll NICHT über einem nahen pendelbaren stehen.
DIST_BONUS_NAH = 10     # <= 0.5 * Umkreis (z.B. <=25 km)
DIST_BONUS_RAND = 4     # <= Umkreis        (z.B. <=50 km)
DIST_MALUS_FERN = -6    # <= 1.6 * Umkreis  (z.B. <=80 km)
DIST_MALUS_SEHR = -12   # <= 2.4 * Umkreis  (z.B. <=120 km)
DIST_MALUS_EXTREM = -18 # darüber

# Statische Ort->(lat, lon)-Tabelle (Rhein-Main + Umland, erweiterbar). Keys sind
# bereits normalisiert (lowercase). Unbekannte Orte -> Distanz neutral (0), nicht erraten.
GEO = {
    "obertshausen": (50.073, 8.856), "offenbach am main": (50.106, 8.766),
    "offenbach": (50.106, 8.766), "frankfurt am main": (50.110, 8.682),
    "frankfurt": (50.110, 8.682), "hanau": (50.133, 8.916),
    "rodgau": (50.020, 8.885), "dietzenbach": (50.009, 8.777),
    "mühlheim am main": (50.116, 8.834), "mühlheim": (50.116, 8.834),
    "mainhausen": (50.005, 8.997), "seligenstadt": (50.045, 8.974),
    "darmstadt": (49.872, 8.651), "aschaffenburg": (49.974, 9.149),
    "alzenau": (50.089, 9.062), "groß-gerau": (49.922, 8.480),
    "rüsselsheim": (49.992, 8.413), "mainz": (49.992, 8.247),
    "wiesbaden": (50.082, 8.240), "bad schwalbach": (50.140, 8.069),
    "gießen": (50.587, 8.678), "lich": (50.524, 8.819),
    "wetzlar": (50.554, 8.498), "weilburg": (50.486, 8.263),
    "marburg an der lahn": (50.801, 8.766), "marburg": (50.801, 8.766),
    "fulda": (50.555, 9.677), "mannheim": (49.488, 8.466),
    "ludwigshafen am rhein": (49.477, 8.445), "ludwigshafen": (49.477, 8.445),
    "heidelberg": (49.398, 8.672), "viernheim": (49.540, 8.578),
    "worms": (49.632, 8.355), "frankenthal": (49.535, 8.354),
    "ingelheim am rhein": (49.972, 8.058), "ingelheim": (49.972, 8.058),
    "laudenbach": (49.652, 8.643), "freudenberg": (49.752, 9.330),
    "kreuzwertheim": (49.762, 9.435), "wertheim": (49.759, 9.514),
    "bad homburg": (50.227, 8.618), "friedberg": (50.339, 8.756),
    "langen": (49.992, 8.659), "dreieich": (50.022, 8.700),
    # v16: Pendel-Belt im ~25-km-Umkreis Obertshausen (Koordinaten belegt via
    # de.wikipedia.org, 2026-06-28; keine geratenen Werte — §3.10).
    "heusenstamm": (50.059, 8.807), "neu-isenburg": (50.056, 8.697),
    "egelsbach": (49.969, 8.667), "rödermark": (49.977, 8.828),
    "mörfelden-walldorf": (49.989, 8.566), "maintal": (50.150, 8.833),
    "großkrotzenburg": (50.082, 8.985), "hainburg": (50.077, 8.953),
    "dieburg": (49.898, 8.838), "babenhausen": (49.962, 8.953),
    "karlstein am main": (50.049, 9.018), "karlstein": (50.049, 9.018),
    "kahl am main": (50.068, 9.007), "erlensee": (50.164, 8.981),
    "bruchköbel": (50.183, 8.917), "nidderau": (50.227, 8.875),
    "bad vilbel": (50.178, 8.735),
}

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
    standort: str | None = None   # Heimatort -> Distanz-Scoring (None = aus)
    umkreis_km: int = 50          # Profil-Radius -> Distanz-Bänder
    max_distanz_km: int | None = None  # harte Obergrenze: weiter entfernte Treffer NICHT anzeigen
    kern_beruf: list[str] | None = None  # Trade/QS-Titel -> nie wegen Studienzwang abgewertet


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


def _coords(location: object) -> tuple[float, float] | None:
    """Ort-String -> (lat, lon) aus der GEO-Tabelle. Wählt den längsten passenden
    Stadtnamen (robust gegen Suffixe wie 'Verkehrsflughafen ...' / ', HE, DE')."""
    if not location:
        return None
    loc = _norm(location)
    best_name, best_xy = "", None
    for stadt, xy in GEO.items():
        if stadt in loc and len(stadt) > len(best_name):
            best_name, best_xy = stadt, xy
    return best_xy


def _haversine(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Großkreis-Distanz in km zwischen zwei (lat, lon)-Punkten."""
    (la1, lo1), (la2, lo2) = a, b
    r = 6371.0
    p1, p2 = math.radians(la1), math.radians(la2)
    dphi, dl = math.radians(la2 - la1), math.radians(lo2 - lo1)
    h = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def _distanz_punkte(km: float, umkreis: int) -> int:
    """Distanz -> Score-Beitrag (Bänder relativ zum Profil-Umkreis)."""
    u = umkreis or 50
    if km <= 0.5 * u:
        return DIST_BONUS_NAH
    if km <= u:
        return DIST_BONUS_RAND
    if km <= 1.6 * u:
        return DIST_MALUS_FERN
    if km <= 2.4 * u:
        return DIST_MALUS_SEHR
    return DIST_MALUS_EXTREM


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

    # Qualifikations-Gate: Büro-Jobs NICHT pauschal raus — nur abwerten, wenn ein
    # Studium VERLANGT wird UND kein Trade-Titel / Ausbildungs- / Quereinsteiger-Pfad
    # da ist (dann fehlt die formale Qualifikation). Trade/QS-Titel sind immer ok.
    titel_norm = _feld_text(t, ("title",))
    trade_titel = any(_norm(k) in titel_norm for k in (pm.kern_beruf or []) if k)
    nicht_qualifiziert = False
    if not trade_titel and STUDIUM_RE.search(text) and not ALT_PFAD_RE.search(text):
        nicht_qualifiziert = True
        score -= MALUS_NICHT_QUALIFIZIERT

    # Distanz-Scoring (nur wenn Heimatort gesetzt UND beide Orte auflösbar; sonst neutral)
    distanz_km = None
    distanz_score = 0
    zu_weit = False
    heim = _coords(pm.standort)
    job_xy = _coords(t.get("location"))
    if heim and job_xy:
        distanz_km = round(_haversine(heim, job_xy))
        distanz_score = _distanz_punkte(distanz_km, pm.umkreis_km)
        score += distanz_score
        if pm.max_distanz_km is not None and distanz_km > pm.max_distanz_km:
            zu_weit = True  # harte Obergrenze -> wird in bewerte_treffer ausgeblendet

    out = dict(t)
    out["match"] = {
        "score": score,
        "ko": ko,
        "muss_treffer": muss_treffer,
        "muss_fehlt": muss_fehlt,
        "kann_treffer": kann_treffer,
        "ausschluss_treffer": aus_treffer,
        "gehalt_unter_min": gehalt_unter_min,
        "distanz_km": distanz_km,
        "distanz_score": distanz_score,
        "zu_weit": zu_weit,
        "nicht_qualifiziert": nicht_qualifiziert,
    }
    return out


def bewerte_treffer(treffer: list[dict], pm: MatchProfil) -> list[dict]:
    """Bewertet alle Treffer und sortiert: vollständige (ko=False) zuerst,
    innerhalb nach Score absteigend. Bei gesetztem max_distanz_km werden Treffer
    OBERHALB der Obergrenze HART ausgeblendet (User-Wunsch: gar nicht anzeigen) —
    Treffer mit unauflösbarem Ort bleiben (kein stiller Datenverlust)."""
    bewertet = [bewerte_einen(t, pm) for t in treffer]
    if pm.max_distanz_km is not None:
        bewertet = [t for t in bewertet if not t["match"]["zu_weit"]]
    bewertet.sort(key=lambda t: (t["match"]["ko"], -t["match"]["score"]))
    return bewertet


def zaehle_ausgeblendet(treffer: list[dict], pm: MatchProfil) -> int:
    """Wie viele Treffer würde der max_distanz_km-Filter ausblenden (für Report)."""
    if pm.max_distanz_km is None:
        return 0
    return sum(1 for t in treffer if bewerte_einen(t, pm)["match"]["zu_weit"])

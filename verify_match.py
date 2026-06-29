"""verify_match.py — Mechanik-Selbsttest des MatchAgent (OHNE Netz).

Prüft deterministisch: Muss-K.o., Kann-Bonus, Ausschluss-Malus, Gehalt-Flag,
Sortierung. Reines Offline-Scoring auf synthetischen Treffer-Dicts.

Lauf:  py -3.11 verify_match.py     (exit 0 = grün)
"""
from __future__ import annotations

import sys

import match

FEHLER: list[str] = []


def check(bedingung: bool, msg: str) -> None:
    if bedingung:
        print(f"  [OK]   {msg}")
    else:
        print(f"  [FAIL] {msg}")
        FEHLER.append(msg)


PM = match.MatchProfil(
    skills_muss=["Montage nach Zeichnung", "Qualitätsprüfung"],
    skills_kann=["Pneumatik", "SAP", "CNC"],
    ausschluss_keywords=["Praktikum", "Werkstudent"],
    gehalt_min_eur_jahr=40000,
)


def _job(**kw) -> dict:
    basis = {"title": "", "company": "", "location": "", "description": "", "such_titel": []}
    basis.update(kw)
    return basis


def test_muss_ko() -> None:
    print("[1] Muss-Skills = K.o.-Flag")
    voll = match.bewerte_einen(
        _job(description="Wir suchen Montage nach Zeichnung und Qualitätsprüfung."), PM)
    check(voll["match"]["ko"] is False, "alle Muss erfüllt -> ko=False")
    check(voll["match"]["muss_fehlt"] == [], "muss_fehlt leer")

    teil = match.bewerte_einen(_job(description="Nur Montage nach Zeichnung, sonst nichts."), PM)
    check(teil["match"]["ko"] is True, "ein Muss fehlt -> ko=True")
    check("Qualitätsprüfung" in teil["match"]["muss_fehlt"], "fehlendes Muss benannt")
    check(teil["match"]["score"] < voll["match"]["score"], "ko-Treffer hat kleineren Score")


def test_kann_bonus() -> None:
    print("[2] Kann-Skills = Bonus")
    ohne = match.bewerte_einen(
        _job(description="Montage nach Zeichnung, Qualitätsprüfung."), PM)
    mit = match.bewerte_einen(
        _job(description="Montage nach Zeichnung, Qualitätsprüfung, Pneumatik, SAP."), PM)
    check(mit["match"]["score"] > ohne["match"]["score"], "Kann-Treffer erhöht Score")
    check(set(mit["match"]["kann_treffer"]) == {"Pneumatik", "SAP"}, "Kann-Treffer benannt")


def test_ausschluss() -> None:
    print("[3] Ausschluss-Keywords = Malus")
    sauber = match.bewerte_einen(
        _job(description="Montage nach Zeichnung, Qualitätsprüfung."), PM)
    prakt = match.bewerte_einen(
        _job(title="Praktikum Montage", description="Montage nach Zeichnung, Qualitätsprüfung."), PM)
    check("Praktikum" in prakt["match"]["ausschluss_treffer"], "Ausschluss-Treffer erkannt")
    check(prakt["match"]["score"] < sauber["match"]["score"], "Ausschluss senkt Score")


def test_ausschluss_nur_titel() -> None:
    print("[3b] Ausschluss greift nur im Titel, nicht im Anforderungs-Fließtext")
    # False-Positive-Schutz: 'Praktikum'/'Ausbildung' als Anforderung im Body
    body = match.bewerte_einen(_job(
        title="Industriemechaniker (m/w/d)",
        description="Voraussetzung: abgeschlossene Ausbildung; bitte Praktikumsbescheinigungen einreichen."), PM)
    check(body["match"]["ausschluss_treffer"] == [], "Ausschluss im Body wird ignoriert")
    # echte Stelle: Typ steht im Titel
    titel = match.bewerte_einen(_job(title="Praktikum im Qualitätswesen (m/w/d)"), PM)
    check("Praktikum" in titel["match"]["ausschluss_treffer"], "Ausschluss im Titel greift")


def test_gehalt() -> None:
    print("[4] Gehalt unter Minimum = Flag + Malus")
    drunter = match.bewerte_einen(
        _job(description="Montage nach Zeichnung, Qualitätsprüfung.", max_amount=30000), PM)
    check(drunter["match"]["gehalt_unter_min"] is True, "max_amount < min -> Flag")
    fehlt = match.bewerte_einen(
        _job(description="Montage nach Zeichnung, Qualitätsprüfung."), PM)
    check(fehlt["match"]["gehalt_unter_min"] is False, "kein Gehalt -> kein Flag (neutral)")


def test_sortierung() -> None:
    print("[5] Sortierung: vollständige zuerst, dann Score absteigend")
    jobs = [
        _job(title="ko", description="Montage nach Zeichnung."),                      # ko
        _job(title="gut", description="Montage nach Zeichnung, Qualitätsprüfung, Pneumatik, SAP, CNC."),
        _job(title="ok", description="Montage nach Zeichnung, Qualitätsprüfung."),
    ]
    out = match.bewerte_treffer(jobs, PM)
    titel = [t["title"] for t in out]
    check(titel == ["gut", "ok", "ko"], f"Reihenfolge gut>ok>ko (ist {titel})")
    check(out[-1]["match"]["ko"] is True, "ko-Treffer landet hinten")


PM_GEO = match.MatchProfil(
    skills_muss=[], skills_kann=["Industriemechaniker"], ausschluss_keywords=[],
    gehalt_min_eur_jahr=None, standort="Obertshausen, Hessen, DE",
    umkreis_km=50, max_distanz_km=30,
)


def test_distanz() -> None:
    print("[6] Distanz-Scoring + harte Obergrenze (v13)")
    nah = match.bewerte_einen(_job(title="Industriemechaniker", location="Frankfurt am Main, HE, DE"), PM_GEO)
    fern = match.bewerte_einen(_job(title="Industriemechaniker", location="Mannheim, BW, DE"), PM_GEO)
    unbk = match.bewerte_einen(_job(title="Industriemechaniker", location="Kleinkleckersdorf, XY, DE"), PM_GEO)
    check(nah["match"]["distanz_km"] is not None and nah["match"]["distanz_km"] < 20,
          f"Frankfurt ~13km erkannt (ist {nah['match']['distanz_km']})")
    check(nah["match"]["distanz_score"] == match.DIST_BONUS_NAH, "naher Treffer -> Nah-Bonus")
    check(nah["match"]["zu_weit"] is False, "Frankfurt <=30km -> nicht zu_weit")
    check(fern["match"]["distanz_km"] > 60, f"Mannheim >60km (ist {fern['match']['distanz_km']})")
    check(fern["match"]["zu_weit"] is True, "Mannheim >30km -> zu_weit")
    check(fern["match"]["distanz_score"] < 0, "ferner Treffer -> Distanz-Malus")
    check(nah["match"]["distanz_score"] > fern["match"]["distanz_score"], "nah > fern im Distanz-Score")
    check(unbk["match"]["distanz_km"] is None, "unbekannter Ort -> distanz_km None")
    check(unbk["match"]["zu_weit"] is False, "unbekannter Ort wird NICHT zu_weit-geflaggt")
    # v16: neuer Pendel-Belt (Wikipedia-belegte Koordinaten) — vormals unbekannte
    # Nachbarorte werden jetzt korrekt als nah erkannt statt distanz-neutral.
    heu = match.bewerte_einen(_job(title="Industriemechaniker", location="63150 Heusenstamm, HE, DE"), PM_GEO)
    check(heu["match"]["distanz_km"] is not None and heu["match"]["distanz_km"] < 8,
          f"Heusenstamm ~4km erkannt (ist {heu['match']['distanz_km']})")
    check(heu["match"]["zu_weit"] is False, "Heusenstamm <=30km -> nicht zu_weit")
    kahl = match.bewerte_einen(_job(title="Industriemechaniker", location="Kahl am Main, BY, DE"), PM_GEO)
    check(kahl["match"]["distanz_km"] is not None and kahl["match"]["distanz_km"] < 20,
          f"Kahl am Main erkannt (ist {kahl['match']['distanz_km']})")
    # v17: Belt-Erweiterung (Wikipedia-belegt) — nahe Pendel-Orte + Rand-Orte am 30km-Filter.
    epp = match.bewerte_einen(_job(title="Industriemechaniker", location="64859 Eppertshausen, HE, DE"), PM_GEO)
    check(epp["match"]["distanz_km"] is not None and epp["match"]["distanz_km"] < 16,
          f"Eppertshausen ~14km erkannt (ist {epp['match']['distanz_km']})")
    check(epp["match"]["zu_weit"] is False, "Eppertshausen <=30km -> nicht zu_weit")
    hat = match.bewerte_einen(_job(title="Industriemechaniker", location="Hattersheim am Main, HE, DE"), PM_GEO)
    check(hat["match"]["distanz_km"] is not None and 20 < hat["match"]["distanz_km"] <= 30,
          f"Hattersheim ~26km erkannt + im 30km-Filter (ist {hat['match']['distanz_km']})")
    check(hat["match"]["zu_weit"] is False, "Hattersheim <=30km -> nicht zu_weit")
    # Münster-Kollisionsschutz: bare "Münster" (Westfalen) wurde bewusst NICHT eingetragen
    # -> bleibt distanz-neutral statt faelschlich als ~16km erkannt.
    muen = match.bewerte_einen(_job(title="Industriemechaniker", location="Münster, NRW, DE"), PM_GEO)
    check(muen["match"]["distanz_km"] is None, "Münster/Westfalen NICHT faelschlich aufgeloest (keine Kollision)")
    jobs = [
        _job(title="nah", location="Offenbach am Main, HE, DE"),
        _job(title="fern", location="Mannheim, BW, DE"),
        _job(title="unbekannt", location="Nirgendwo, XY, DE"),
    ]
    out = match.bewerte_treffer(jobs, PM_GEO)
    titel = [t["title"] for t in out]
    check("fern" not in titel, "ferner Treffer (Mannheim) hart ausgeblendet")
    check("nah" in titel, "naher Treffer (Offenbach) bleibt")
    check("unbekannt" in titel, "unbekannter Ort bleibt (kein stiller Drop)")
    check(match.zaehle_ausgeblendet(jobs, PM_GEO) == 1, "zaehle_ausgeblendet == 1")


PM_QUAL = match.MatchProfil(
    skills_muss=[], skills_kann=["SAP"], ausschluss_keywords=[],
    gehalt_min_eur_jahr=None, kern_beruf=["Industriemechaniker", "Mechatroniker", "Qualität"],
)


def test_qualifikation() -> None:
    print("[7] Qualifikations-Gate (Studium verlangt vs. Quereinsteiger/Ausbildung)")
    trade = match.bewerte_einen(_job(
        title="Industriemechaniker (m/w/d)",
        description="Abgeschlossenes Studium erforderlich."), PM_QUAL)
    check(trade["match"]["nicht_qualifiziert"] is False,
          "Trade-Titel bleibt qualifiziert, auch wenn Text 'Studium' nennt")

    buero = match.bewerte_einen(_job(
        title="Senior Consultant (m/w/d)",
        description="Abgeschlossenes Studium der Informatik erforderlich. SAP."), PM_QUAL)
    check(buero["match"]["nicht_qualifiziert"] is True, "Büro-Job mit Studienzwang -> nicht_qualifiziert")
    check(buero["match"]["score"] < trade["match"]["score"], "Studienzwang-Büro sinkt unter Trade")

    quer = match.bewerte_einen(_job(
        title="Vertriebsmitarbeiter (m/w/d)",
        description="Abgeschlossenes Studium oder Quereinsteiger willkommen. SAP."), PM_QUAL)
    check(quer["match"]["nicht_qualifiziert"] is False, "Quereinsteiger-Pfad -> bleibt qualifiziert")

    azubi = match.bewerte_einen(_job(
        title="Sachbearbeiter (m/w/d)",
        description="Studium oder abgeschlossene Ausbildung."), PM_QUAL)
    check(azubi["match"]["nicht_qualifiziert"] is False, "Ausbildungs-Alternative -> bleibt qualifiziert")

    plain = match.bewerte_einen(_job(
        title="Verkäufer (m/w/d)", description="Freundliches Auftreten, Teamgeist."), PM_QUAL)
    check(plain["match"]["nicht_qualifiziert"] is False, "Büro-Job ohne Studienzwang bleibt (Quereinsteiger möglich)")


def main() -> int:
    print("=== verify_match.py (offline MatchAgent-Selbsttest) ===")
    test_muss_ko()
    test_kann_bonus()
    test_ausschluss()
    test_ausschluss_nur_titel()
    test_gehalt()
    test_sortierung()
    test_distanz()
    test_qualifikation()
    print("---")
    if FEHLER:
        print(f"ROT: {len(FEHLER)} Fehler")
        return 1
    print("GRÜN: alle MatchAgent-Checks bestanden")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

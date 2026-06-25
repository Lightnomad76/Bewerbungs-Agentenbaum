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


def main() -> int:
    print("=== verify_match.py (offline MatchAgent-Selbsttest) ===")
    test_muss_ko()
    test_kann_bonus()
    test_ausschluss()
    test_gehalt()
    test_sortierung()
    print("---")
    if FEHLER:
        print(f"ROT: {len(FEHLER)} Fehler")
        return 1
    print("GRÜN: alle MatchAgent-Checks bestanden")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

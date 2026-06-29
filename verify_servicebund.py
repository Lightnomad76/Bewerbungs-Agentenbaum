"""verify_servicebund.py — Mechanik-Selbsttest des service.bund-Adapters (OHNE Netz).

Prüft deterministisch gegen eingebettete Fixtures (echtes RSS-/HTML-Schema, kein Netz):
RSS-Parse, description-CDATA-Extraktion, RFC822-pubDate, Datum-Filter (Karteileichen),
Vorfilter (Titel-Keywords + Distanz), HTML->Text, Schema-Kompatibilität zur Pipeline (match).

Lauf:  .\.venv\Scripts\python.exe verify_servicebund.py     (exit 0 = grün)
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone

import quelle_servicebund as q
import match

FEHLER: list[str] = []


def check(bedingung: bool, msg: str) -> None:
    if bedingung:
        print(f"  [OK]   {msg}")
    else:
        print(f"  [FAIL] {msg}")
        FEHLER.append(msg)


# Fixture: echtes service.bund-RSS-Schema (1:1 nach Live-Sample 2026-06-29).
# - Item 1: technischer Treffer NAH (Obertshausen, in GEO) + aktuell
# - Item 2: technischer Treffer FERN (Fulda, ~70 km, in GEO -> auflösbar) + aktuell
# - Item 3: nicht-technischer Titel (Küche) -> Titel-Keyword-Filter raus
# - Item 4: technischer Titel NAH, aber ALT (2023) -> Datum-Filter raus
# Umlaute als numerische Entities (M&#252;nster) wie im echten Feed (CDATA = literal).
RSS_FIXTURE = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>service.bund.de - Stellenangebote</title>
    <item>
      <title>Mechatronikerin / Mechatroniker (m/w/d)</title>
      <link>https://www.service.bund.de/IMPORTE/Stellenangebote/x/2026/06/AAA-0001-B.html#track=feed-jobs</link>
      <description><![CDATA[
Arbeitgeber: <strong>Stadtwerke Musterstadt</strong><br />
    Ort: <strong>63179 Obertshausen</strong>
 <br />
<br />Bewerbungsfrist:  <strong>24.07.2026 23:59</strong> <br />
]]></description>
      <pubDate>Mon, 29 Jun 2026 08:40:39 +0200</pubDate>
      <guid>https://www.service.bund.de/IMPORTE/Stellenangebote/x/2026/06/AAA-0001-B.html</guid>
    </item>
    <item>
      <title>Elektronikerin / Elektroniker (m/w/d)</title>
      <link>https://www.service.bund.de/IMPORTE/Stellenangebote/x/2026/06/AAA-0002-B.html#track=feed-jobs</link>
      <description><![CDATA[
Arbeitgeber: <strong>Bundeswehr-Dienstleistungszentrum M&#252;nster</strong><br />
    Ort: <strong>36037 Fulda</strong>
 <br />Bewerbungsfrist:  <strong>24.07.2026 23:59</strong> <br />
]]></description>
      <pubDate>Mon, 29 Jun 2026 08:02:05 +0200</pubDate>
      <guid>https://www.service.bund.de/IMPORTE/Stellenangebote/x/2026/06/AAA-0002-B.html</guid>
    </item>
    <item>
      <title>K&#252;chenservicekraft (m/w/d)</title>
      <link>https://www.service.bund.de/IMPORTE/Stellenangebote/x/2026/06/AAA-0003-B.html#track=feed-jobs</link>
      <description><![CDATA[
Arbeitgeber: <strong>Bundeswehr</strong><br />    Ort: <strong>63179 Obertshausen</strong> <br />
]]></description>
      <pubDate>Mon, 29 Jun 2026 07:58:57 +0200</pubDate>
      <guid>https://www.service.bund.de/IMPORTE/Stellenangebote/x/2026/06/AAA-0003-B.html</guid>
    </item>
    <item>
      <title>Anlagenmechanikerin / Anlagenmechaniker (m/w/d)</title>
      <link>https://www.service.bund.de/IMPORTE/Stellenangebote/x/2023/01/AAA-0004-B.html#track=feed-jobs</link>
      <description><![CDATA[
Arbeitgeber: <strong>Alt-Behörde</strong><br />    Ort: <strong>63179 Obertshausen</strong> <br />
]]></description>
      <pubDate>Tue, 10 Jan 2023 09:00:00 +0100</pubDate>
      <guid>https://www.service.bund.de/IMPORTE/Stellenangebote/x/2023/01/AAA-0004-B.html</guid>
    </item>
  </channel>
</rss>"""

DETAIL_HTML_FIXTURE = """<html><head><title>egal</title>
<style>.x{color:red}</style><script>var a=1;</script></head>
<body><nav>Navigation Suche Behörden</nav>
<div id="content">
<p><strong>DAS BRINGEN SIE MIT</strong></p>
<ul><li>abgeschlossene Berufsausbildung als Mechatroniker/in</li>
<li>Kenntnisse in Hydraulik &amp; Pneumatik</li></ul>
<p><strong>WAS F&#220;R SIE Z&#196;HLT</strong></p>
<ul><li>Verg&#252;tung nach TV&#246;D Entgeltgruppe 7</li></ul>
</div>
<footer>Zur Druckansicht Impressum</footer></body></html>"""

# Feste "Jetzt"-Zeit, damit der Datum-Filter deterministisch ist (sonst zeitabhängig).
JETZT = datetime(2026, 6, 29, 12, 0, 0, tzinfo=timezone.utc)


def test_parse_rss() -> None:
    print("[1] parse_rss: Schema-Mapping")
    items = q.parse_rss(RSS_FIXTURE.encode("utf-8"))
    check(len(items) == 4, "4 Items geparst")
    t0 = items[0]
    check(t0["title"] == "Mechatronikerin / Mechatroniker (m/w/d)", "title korrekt")
    check(t0["company"] == "Stadtwerke Musterstadt", "company aus Arbeitgeber-CDATA")
    check(t0["location"] == "63179 Obertshausen", "location aus Ort-CDATA")
    check(t0["job_url"].endswith("AAA-0001-B.html"), "job_url ohne #track-Fragment")
    check("#" not in t0["job_url"], "Fragment gestrippt")
    check(t0["guid"].endswith("AAA-0001-B.html"), "guid gesetzt")
    check(t0["date_posted"] == "2026-06-29", "date_posted aus pubDate (ISO)")
    check(t0["site"] == "servicebund", "site = servicebund")
    check(t0["bewerbungsfrist"] == "24.07.2026 23:59", "Bewerbungsfrist extrahiert")
    check(isinstance(t0["such_titel"], str), "such_titel skalar (dedup-kompatibel)")


def test_entity_decoding() -> None:
    print("[2] HTML-Entity-Dekodierung (CDATA literal + Titel-charref)")
    items = q.parse_rss(RSS_FIXTURE.encode("utf-8"))
    check(items[1]["company"] == "Bundeswehr-Dienstleistungszentrum Münster",
          "M&#252;nster -> Münster (CDATA via html.unescape)")
    check(items[2]["title"].startswith("Küchenservicekraft"),
          "K&#252;chenservicekraft -> Küchen… (Titel-charref via ET)")


def test_pubdate() -> None:
    print("[3] parse_pubdate: RFC822 + Zeitzone")
    dt = q.parse_pubdate("Mon, 29 Jun 2026 08:40:39 +0200")
    check(dt is not None and dt.year == 2026 and dt.month == 6 and dt.day == 29, "Datum geparst")
    check(dt.utcoffset().total_seconds() == 2 * 3600, "Zeitzone +0200 erkannt")
    check(q.parse_pubdate(None) is None, "None -> None")
    check(q.parse_pubdate("kaputt") is None, "Unparsebar -> None (kein Crash)")


def test_datum_filter() -> None:
    print("[4] filter_nach_datum: Karteileichen raus")
    items = q.parse_rss(RSS_FIXTURE.encode("utf-8"))
    gefiltert = q.filter_nach_datum(items, max_alter_tage=90, jetzt=JETZT)
    urls = [t["job_url"] for t in gefiltert]
    check(len(gefiltert) == 3, "altes 2023-Item (0004) ausgefiltert")
    check(not any("0004" in u for u in urls), "Karteileiche raus")
    check(any("0001" in u for u in urls), "aktuelles Item bleibt")
    check(len(q.filter_nach_datum(items, max_alter_tage=None, jetzt=JETZT)) == 4,
          "max_alter_tage=None -> kein Filter")


def test_vorfilter() -> None:
    print("[5] vorfilter: Titel-Keywords + Distanz")
    items = q.parse_rss(RSS_FIXTURE.encode("utf-8"))
    # Nur Titel-Keyword (kein Distanzfilter): Küche raus, 3 technische bleiben.
    nur_titel = q.vorfilter(items, titel_keywords=["mechatronik", "elektronik", "anlagenmechan"])
    check(len(nur_titel) == 3, "Küchen-Titel via Keyword-Filter raus")
    check(not any("Küche" in t["title"] for t in nur_titel), "kein Küchen-Treffer")
    # Mit Distanz: Fulda (~70 km) raus, Obertshausen (0 km) bleibt.
    mit_dist = q.vorfilter(items, standort="Obertshausen", max_distanz_km=30,
                           titel_keywords=["mechatronik", "elektronik", "anlagenmechan"])
    orte = [t["location"] for t in mit_dist]
    check(not any("Fulda" in o for o in orte), "ferner Ort (Fulda) via Distanz raus")
    check(any("Obertshausen" in o for o in orte), "naher Ort (Obertshausen) bleibt")
    # Leere Keywords -> alle durch (nur Distanz greift, falls gesetzt)
    check(len(q.vorfilter(items, titel_keywords=None)) == 4, "ohne Keywords: alle durch")


def test_unaufloesbarer_ort_bleibt() -> None:
    print("[6] Vorfilter: unauflösbarer Ort bleibt (kein stiller Verlust)")
    items = q.parse_rss(RSS_FIXTURE.encode("utf-8"))
    # Ort künstlich auf unbekannte Stadt setzen -> Distanzfilter darf ihn NICHT droppen
    items[0]["location"] = "99999 Hintertupfingen"
    res = q.vorfilter(items, standort="Obertshausen", max_distanz_km=30,
                      titel_keywords=["mechatronik"])
    check(any("Hintertupfingen" in (t["location"] or "") for t in res),
          "unbekannter Ort bleibt trotz Distanzfilter")


def test_html_zu_text() -> None:
    print("[7] html_zu_text: Detailseite -> Plaintext")
    txt = q.html_zu_text(DETAIL_HTML_FIXTURE)
    check("var a=1" not in txt, "script-Inhalt entfernt")
    check("color:red" not in txt, "style-Inhalt entfernt")
    check("Mechatroniker/in" in txt, "Aufgaben/Profil-Text erhalten")
    check("Hydraulik & Pneumatik" in txt, "&amp; -> & dekodiert")
    check("Vergütung nach TVöD" in txt, "Umlaut-Entities dekodiert (TV&#246;D)")
    check("WAS FÜR SIE ZÄHLT" in txt, "Überschrift-Entities (F&#220;R/Z&#196;HLT) dekodiert")
    check("<" not in txt and ">" not in txt, "keine Tag-Reste")


def test_pipeline_kompatibel() -> None:
    print("[8] Schema-Kompatibilität: Treffer läuft durch match.bewerte_einen")
    items = q.parse_rss(RSS_FIXTURE.encode("utf-8"))
    pm = match.MatchProfil(
        skills_muss=[], skills_kann=["Mechatronik", "Elektronik"],
        ausschluss_keywords=["Praktikum"], gehalt_min_eur_jahr=None,
        standort="Obertshausen", umkreis_km=30, max_distanz_km=30,
    )
    bew = match.bewerte_einen(items[0], pm)  # Mechatroniker, Obertshausen
    check("match" in bew, "match-Block angehängt (Schema passt)")
    check(bew["match"]["distanz_km"] == 0, "Distanz Obertshausen->Obertshausen = 0 km")
    check(bew["match"]["zu_weit"] is False, "naher Treffer nicht zu_weit")
    fern = match.bewerte_einen(items[1], pm)  # Fulda
    check(fern["match"]["distanz_km"] is None or fern["match"]["zu_weit"] is True
          or fern["match"]["distanz_km"] > 30, "ferner/unauflösbarer Treffer korrekt behandelt")
    # voller Lauf inkl. Distanz-Hard-Filter
    alle = match.bewerte_treffer(items, pm)
    check(all("match" in t for t in alle), "bewerte_treffer akzeptiert service.bund-Treffer")


def main() -> int:
    print("=== verify_servicebund (offline) ===")
    test_parse_rss()
    test_entity_decoding()
    test_pubdate()
    test_datum_filter()
    test_vorfilter()
    test_unaufloesbarer_ort_bleibt()
    test_html_zu_text()
    test_pipeline_kompatibel()
    print()
    if FEHLER:
        print(f"ERGEBNIS: {len(FEHLER)} FAIL — {FEHLER}")
        return 1
    print("ERGEBNIS: alle Checks grün.")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    raise SystemExit(main())

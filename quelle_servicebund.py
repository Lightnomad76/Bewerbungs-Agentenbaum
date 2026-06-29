"""quelle_servicebund.py — service.bund.de RSS-Adapter (öffentlicher Dienst).

Liest den (gefilterten) Stellen-RSS-Feed von service.bund.de und mappt jedes Item
auf das bestehende Treffer-Schema (KERN in main.py), sodass die ganze nachgelagerte
Pipeline (match/jdparser/tailoring/coverletter/UI) UNVERÄNDERT greift.

Warum service.bund: Indeed deckt den öffentlichen Dienst (TVöD, Kommunen, Bundeswehr,
Unikliniken, Stadtwerke) schlecht ab. service.bund aggregiert auch interamt mit.
Legal: RSS-Feeds + Detail-Seiten sind NICHT robots-disallowed (offiziell zum
Abonnieren angeboten); robots.txt verlangt `Crawl-delay: 30` -> 30 s zwischen
Requests (hart eingehalten). Scope/Belege: state/scope_servicebund_quelle.md.

Stdlib-only: xml.etree + urllib + email.utils + html — KEINE neue pip-Dependency.
read-only: nur lesen + parsen + filtern. Kein Login, kein Schreiben.

CLI:  python quelle_servicebund.py <feed_url> [--detail] [--max-tage N] [--max-detail N]
      (Detail-Fetch ist standardmäßig AUS — Crawl-delay-Laufzeit; mit --detail anschalten.)
"""
from __future__ import annotations

import html
import re
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import xml.etree.ElementTree as ET

USER_AGENT = "Mozilla/5.0 (Bewerbungs-Agentenbaum; read-only RSS reader)"
CRAWL_DELAY_S = 30          # robots.txt Crawl-delay (Politeness, hart)
DEFAULT_MAX_ALTER_TAGE = 90  # CAVEAT: Feed enthält Karteileichen (pubDate bis 2023/24)
DEFAULT_MAX_DETAIL = 25      # Obergrenze Detail-Fetches (deckelt Crawl-delay-Laufzeit)

# --- description-CDATA: Arbeitgeber/Ort/Frist stehen in <strong>...</strong> ---
_RE_ARBEITGEBER = re.compile(r"Arbeitgeber:\s*<strong>(.*?)</strong>", re.I | re.S)
_RE_ORT = re.compile(r"Ort:\s*<strong>(.*?)</strong>", re.I | re.S)
_RE_FRIST = re.compile(r"Bewerbungsfrist:\s*<strong>(.*?)</strong>", re.I | re.S)

# --- HTML -> Text (Detailseiten) ---
_RE_SCRIPT = re.compile(r"<(script|style)\b.*?</\1>", re.I | re.S)
_RE_COMMENT = re.compile(r"<!--.*?-->", re.S)
_RE_BLOCK = re.compile(r"</(p|div|li|ul|ol|tr|table|h[1-6]|section|article)>|<br\s*/?>", re.I)
_RE_TAG = re.compile(r"<[^>]+>")


# --------------------------------------------------------------------------- #
# Reine Parser (offline, ohne Netz — der testbare Kern)
# --------------------------------------------------------------------------- #
def _txt(s: object) -> str:
    """HTML-Entities auflösen + Whitespace auf ein Leerzeichen normalisieren."""
    return html.unescape(re.sub(r"\s+", " ", str(s or "")).strip())


def parse_pubdate(s: str | None) -> datetime | None:
    """RFC822-Datum ('Mon, 29 Jun 2026 08:40:39 +0200') -> aware datetime (UTC-fallback).
    Locale-unabhängig via email.utils (NICHT strptime %b — das ist locale-abhängig)."""
    if not s:
        return None
    try:
        dt = parsedate_to_datetime(s.strip())
    except (TypeError, ValueError, IndexError):
        return None
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _parse_description(cdata: str | None) -> tuple[str | None, str | None, str | None]:
    """(Arbeitgeber, Ort, Bewerbungsfrist) aus dem CDATA-HTML der RSS-description."""
    if not cdata:
        return None, None, None
    mr = _RE_ARBEITGEBER.search(cdata)
    mo = _RE_ORT.search(cdata)
    mf = _RE_FRIST.search(cdata)
    return (
        _txt(mr.group(1)) if mr else None,
        _txt(mo.group(1)) if mo else None,
        _txt(mf.group(1)) if mf else None,
    )


def _strip_fragment(url: str | None) -> str | None:
    """'…B.html#track=feed-jobs' -> '…B.html' (guid-konsistent, dedup-stabil)."""
    if not url:
        return url
    return url.split("#", 1)[0].strip()


def item_zu_treffer(item: ET.Element) -> dict:
    """Ein RSS-<item> -> Treffer-Dict im KERN-Schema (+ Zusatzfelder).
    `_pubdate` ist intern (Datum-Filter) und wird vom Orchestrator entfernt."""
    def g(tag: str) -> str | None:
        e = item.find(tag)
        return e.text if e is not None else None

    title = _txt(g("title"))
    link = _strip_fragment((g("link") or "").strip())
    guid = (g("guid") or link or "").strip()
    cdata = g("description")
    arbeitgeber, ort, frist = _parse_description(cdata)
    dt = parse_pubdate(g("pubDate"))

    # description initial = kompakte Kurzinfo aus dem Feed; der Aufgaben/Profil-Volltext
    # kommt erst per Detail-Fetch dazu (für jdparser/tailoring nötig, aber Crawl-delay-teuer).
    kurz = []
    if arbeitgeber:
        kurz.append(f"Arbeitgeber: {arbeitgeber}")
    if ort:
        kurz.append(f"Ort: {ort}")
    if frist:
        kurz.append(f"Bewerbungsfrist: {frist}")

    return {
        "title": title,
        "company": arbeitgeber,
        "location": ort,
        "job_url": link,
        "guid": guid,
        "date_posted": dt.date().isoformat() if dt else None,
        "min_amount": None,
        "max_amount": None,
        "description": " | ".join(kurz) if kurz else None,
        "bewerbungsfrist": frist,
        "site": "servicebund",
        # scalar (wie JobSpy vor dem Dedup) -> main.dedupliziere aggregiert es korrekt
        "such_titel": "service.bund",
        "_pubdate": dt,
    }


def parse_rss(xml_bytes: bytes | str) -> list[dict]:
    """RSS 2.0 -> Liste Treffer-Dicts. Erwartet BYTES (XML hat encoding-Deklaration;
    ET.fromstring lehnt str MIT Deklaration ab)."""
    root = ET.fromstring(xml_bytes)
    return [item_zu_treffer(it) for it in root.findall(".//item")]


def filter_nach_datum(treffer: list[dict], max_alter_tage: int | None = DEFAULT_MAX_ALTER_TAGE,
                      jetzt: datetime | None = None) -> list[dict]:
    """Wirft Karteileichen raus (älter als max_alter_tage). Items mit unlesbarem
    Datum bleiben (kein stiller Verlust). max_alter_tage=None -> kein Filter."""
    if max_alter_tage is None:
        return list(treffer)
    jetzt = jetzt or datetime.now(timezone.utc)
    grenze = jetzt - timedelta(days=max_alter_tage)
    out = []
    for t in treffer:
        dt = t.get("_pubdate")
        if dt is None or dt >= grenze:
            out.append(t)
    return out


def vorfilter(treffer: list[dict], standort: str | None = None,
              max_distanz_km: int | None = None,
              titel_keywords: list[str] | None = None) -> list[dict]:
    """Client-seitiger Vorfilter VOR dem teuren Detail-Fetch (reduziert N):
    - Titel-Keywords: nur technische/ÖD-relevante Titel durchlassen (None/[] = alle).
    - Distanz: Treffer über max_distanz_km raus (NUR wenn Ort UND Heimat auflösbar;
      unauflösbare Orte bleiben — kein stiller Verlust, der Match-Scorer behandelt sie).
    Nutzt die GEO-Tabelle + Haversine aus match.py (keine API/Geocoding)."""
    import match
    heim = match._coords(standort) if standort else None
    kws = [k.lower() for k in (titel_keywords or []) if k]
    out = []
    for t in treffer:
        if kws:
            tt = (t.get("title") or "").lower()
            if not any(k in tt for k in kws):
                continue
        if heim and max_distanz_km is not None:
            xy = match._coords(t.get("location"))
            if xy is not None and match._haversine(heim, xy) > max_distanz_km:
                continue
        out.append(t)
    return out


def html_zu_text(html_str: str) -> str:
    """Detailseiten-HTML -> lesbarer Plaintext (Aufgaben/Profil/Angebot).
    Generisch (script/style/Kommentare raus, Block-Tags -> Zeilenumbruch, Rest-Tags
    weg, Entities auf). Bewusst NICHT auf GSB-spezifische div-IDs angewiesen
    (brüchig bei Relaunch); jdparser segmentiert ohnehin selbst nach Abschnitten."""
    s = _RE_SCRIPT.sub(" ", html_str)
    s = _RE_COMMENT.sub(" ", s)
    s = _RE_BLOCK.sub("\n", s)
    s = _RE_TAG.sub(" ", s)
    s = html.unescape(s)
    zeilen = [re.sub(r"[ \t]+", " ", z).strip() for z in s.splitlines()]
    return "\n".join(z for z in zeilen if z)


# --------------------------------------------------------------------------- #
# Netz (urllib) — getrennt vom Parser, damit der Kern offline testbar bleibt
# --------------------------------------------------------------------------- #
def _http_get_bytes(url: str, timeout: int = 25) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _http_get_text(url: str, timeout: int = 25) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        roh = r.read()
        enc = r.headers.get_content_charset() or "utf-8"
    return roh.decode(enc, errors="replace")


def fetch_detail_text(url: str, timeout: int = 25) -> str:
    """Detailseite holen -> Plaintext. EIN Netz-Request (Crawl-delay regelt der Aufrufer)."""
    return html_zu_text(_http_get_text(url, timeout))


# --------------------------------------------------------------------------- #
# Orchestrator: holen -> parsen -> Datum -> Vorfilter -> (gedrosselt) Detail-Fetch
# --------------------------------------------------------------------------- #
def hole_stellen(feed_url: str, standort: str | None = None,
                 max_distanz_km: int | None = None,
                 titel_keywords: list[str] | None = None,
                 max_alter_tage: int | None = DEFAULT_MAX_ALTER_TAGE,
                 detail_fetch: bool = False,
                 max_detail: int = DEFAULT_MAX_DETAIL,
                 log=print) -> list[dict]:
    """Vollständiger service.bund-Lauf. **detail_fetch ist standardmäßig AUS** —
    der Detail-Fetch ist ein §3.6b-Laufzeit-Posten (block-gepuffert N×30 s Crawl-delay)
    und kann lange blockieren; Titel/Ort/Datum + Scoring reichen zum Sichten. Erst bei
    detail_fetch=True wird der Aufgaben/Profil-Volltext nachgeladen (für jdparser/tailoring),
    dann hart über Vorfilter + max_detail gedeckelt, sequentiell, mit Liveness-Logs."""
    xml_bytes = _http_get_bytes(feed_url)
    treffer = parse_rss(xml_bytes)
    log(f"  [service.bund] {len(treffer)} RSS-Items roh")

    treffer = filter_nach_datum(treffer, max_alter_tage)
    log(f"  [service.bund] {len(treffer)} nach Datum-Filter (<= {max_alter_tage} Tage)")

    treffer = vorfilter(treffer, standort, max_distanz_km, titel_keywords)
    log(f"  [service.bund] {len(treffer)} nach Vorfilter (Titel-Keywords/Distanz)")

    if detail_fetch and treffer:
        zu_holen = treffer[:max_detail]
        gesamt = len(zu_holen)
        if len(treffer) > max_detail:
            log(f"  [service.bund] [Hinweis] {len(treffer)} Überlebende, aber max_detail={max_detail} "
                f"-> nur die ersten {max_detail} Detail-Fetches.")
        # Wall-Clock-Ansage (§3.6b: messen/ansagen statt raten): N-1 Wartezeiten à 30 s.
        sek = (gesamt - 1) * CRAWL_DELAY_S
        log(f"  [service.bund] START Detail-Fetch {gesamt} Seiten, sequentiell, "
            f"Crawl-delay {CRAWL_DELAY_S}s -> ~{sek//60} min {sek%60}s Wall-Clock (+ Fetch-Zeit)")
        for i, t in enumerate(zu_holen):
            if i:
                log(f"  [service.bund] ... Politeness-Pause {CRAWL_DELAY_S}s vor {i+1}/{gesamt}")
                time.sleep(CRAWL_DELAY_S)
            try:
                volltext = fetch_detail_text(t["job_url"])
                kurz = t.get("description") or ""
                t["description"] = (kurz + "\n\n" + volltext).strip() if kurz else volltext
                log(f"  [service.bund] [{i+1}/{gesamt}] OK {t.get('title','')[:48]} "
                    f"({len(volltext)} Zeichen)")
            except Exception as exc:  # ein Detail down -> Treffer bleibt mit Kurzinfo
                log(f"  [service.bund] [{i+1}/{gesamt}] [WARN] Detail-Fetch fehlgeschlagen "
                    f"({t.get('job_url')}): {type(exc).__name__}: {exc}")
        log(f"  [service.bund] ENDE Detail-Fetch ({gesamt} Seiten)")

    for t in treffer:
        t.pop("_pubdate", None)
    return treffer


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def _cli(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    feed_url = argv[0]
    detail = "--detail" in argv  # Default AUS (Crawl-delay-Laufzeit); --no-detail bleibt als No-Op erlaubt
    max_tage = DEFAULT_MAX_ALTER_TAGE
    max_detail = DEFAULT_MAX_DETAIL
    if "--max-tage" in argv:
        max_tage = int(argv[argv.index("--max-tage") + 1])
    if "--max-detail" in argv:
        max_detail = int(argv[argv.index("--max-detail") + 1])
    treffer = hole_stellen(feed_url, detail_fetch=detail,
                           max_alter_tage=max_tage, max_detail=max_detail)
    print(f"\n{len(treffer)} Treffer:")
    for t in treffer:
        print(f"  - {t['title']}  [{t.get('company')}, {t.get('location')}]  {t.get('date_posted')}")
        print(f"    {t['job_url']}")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    raise SystemExit(_cli(sys.argv[1:]))

"""tailor_treffer.py — per-Treffer read-only Tailoring-Report über die Live-Treffer.

Nimmt die vom Engine erzeugte treffer_v*.json (Indeed + service.bund) und rechnet
für jeden Treffer den jdparser/tailoring-Abgleich gegen den eigenen CV-Text:
wie viel % der Anzeigen-Keywords deckt der CV, welche MUSS-Keywords fehlen.
So sieht man auf einen Blick, welche der echten Treffer am besten passen und wo
echte Lücken sind — ohne jede Beschreibung einzeln in die CLI zu kopieren.

read-only / deterministisch / offline / keine API. Komponiert nur bestehende Module
(jdparser via tailoring.abgleich_texte). Verändert KEINE Datei, erfindet KEINEN Inhalt.

CV-Text ist persönlich (PII) -> wird zur Laufzeit als Datei übergeben, NIE eingecheckt.

CLI:  py -3.11 tailor_treffer.py <cv.txt> [treffer_v2.json] [--top N] [--json]
      .\.venv\Scripts\python.exe tailor_treffer.py <cv.txt>   (beides ok — kein jobspy nötig)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import tailoring

BASE = Path(__file__).resolve().parent
DEFAULT_TREFFER = BASE / "treffer_v2.json"


def lade_treffer(pfad: Path) -> list[dict]:
    """Liest die Engine-JSON. Akzeptiert sowohl {meta, treffer:[...]} als auch
    eine nackte Treffer-Liste (Robustheit gegen Format-Varianten)."""
    data = json.loads(Path(pfad).read_text(encoding="utf-8"))
    if isinstance(data, dict):
        return data.get("treffer", []) or []
    if isinstance(data, list):
        return data
    return []


def anzeige_text(t: dict) -> str:
    """Baut den Anzeigen-Text für den Abgleich aus den Treffer-Feldern."""
    teile = [str(t.get(f) or "") for f in ("title", "company", "location", "description")]
    st = t.get("such_titel")
    if isinstance(st, (list, tuple)):
        teile.extend(str(x) for x in st)
    elif st:
        teile.append(str(st))
    return "\n".join(p for p in teile if p.strip())


def tailor_einen(t: dict, cv_text: str) -> dict:
    """Ein Treffer -> kompakte Tailoring-Zeile (Abdeckung% + Lücken). read-only."""
    ab = tailoring.abgleich_texte(anzeige_text(t), cv_text)
    m = t.get("match") or {}
    return {
        "title": t.get("title"),
        "company": t.get("company"),
        "location": t.get("location"),
        "site": t.get("site"),
        "score": m.get("score"),
        "distanz_km": m.get("distanz_km"),
        "abdeckung_prozent": ab["stats"]["abdeckung_prozent"],
        "muss_fehlt": ab["muss_fehlt"],
        "kann_fehlt": ab["kann_fehlt"],
        "vorhanden": ab["vorhanden"],
        "job_url": t.get("job_url"),
    }


def tailor_treffer(treffer: list[dict], cv_text: str, top: int | None = None) -> list[dict]:
    """Alle Treffer in Eingabe-Reihenfolge (= bereits match-priorisiert) tailoren.
    `top` begrenzt auf die ersten N (None = alle)."""
    auswahl = treffer[:top] if top else treffer
    return [tailor_einen(t, cv_text) for t in auswahl]


def report(rows: list[dict]) -> str:
    out = ["=== tailor_treffer — per-Treffer Anzeige<->CV-Abdeckung (read-only) ==="]
    if not rows:
        out.append("(keine Treffer)")
        return "\n".join(out)
    for i, r in enumerate(rows, 1):
        kopf = f"[{i}] {r['title']}"
        meta = []
        if r.get("company"):
            meta.append(str(r["company"]))
        if r.get("location"):
            meta.append(str(r["location"]))
        if r.get("site"):
            meta.append(str(r["site"]))
        if meta:
            kopf += "  (" + ", ".join(meta) + ")"
        out.append(kopf)
        zeile = f"    Abdeckung {r['abdeckung_prozent']}%"
        if r.get("score") is not None:
            zeile += f" | Score {r['score']}"
        if r.get("distanz_km") is not None:
            zeile += f" | {r['distanz_km']} km"
        out.append(zeile)
        if r["muss_fehlt"]:
            out.append("    MUSS fehlt: " + ", ".join(r["muss_fehlt"]))
        else:
            out.append("    MUSS: alle gedeckt")
        if r["kann_fehlt"]:
            out.append("    KANN fehlt: " + ", ".join(r["kann_fehlt"]))
    return "\n".join(out)


def main(argv: list[str]) -> int:
    args = [a for a in argv if not a.startswith("--")]
    flags = [a for a in argv if a.startswith("--")]
    if not args or "--help" in flags or "-h" in flags:
        print(__doc__)
        return 0
    cv_pfad = Path(args[0])
    if not cv_pfad.exists():
        print(f"CV-Textdatei fehlt: {cv_pfad}", file=sys.stderr)
        return 2
    treffer_pfad = Path(args[1]) if len(args) > 1 else DEFAULT_TREFFER
    if not treffer_pfad.exists():
        print(f"Treffer-JSON fehlt: {treffer_pfad} (erst main.py laufen lassen).", file=sys.stderr)
        return 2

    top = None
    if "--top" in argv:
        top = int(argv[argv.index("--top") + 1])

    cv_text = cv_pfad.read_text(encoding="utf-8")
    rows = tailor_treffer(lade_treffer(treffer_pfad), cv_text, top=top)

    if "--json" in flags:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    else:
        print(report(rows))
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    raise SystemExit(main(sys.argv[1:]))

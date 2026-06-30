# -*- coding: utf-8 -*-
"""export_pdf.py — .docx -> PDF (PDF/A) via Word-COM.

Hintergrund: Auf dem Host ist Word installiert (kein LibreOffice). Word kann .docx
verlustfrei nach PDF exportieren. Default = **PDF/A** (ISO 19005-1): ein archiv-
standardisiertes PDF, das aktive Inhalte (JavaScript/Aktionen) technisch ausschliesst
-> sauberstes Format gegenueber E-Mail-/Viren-Scannern.

Lauf:  py -3.11 export_pdf.py                 # alle profile/*.docx -> PDF
       py -3.11 export_pdf.py <datei.docx> .. # gezielt einzelne Dateien
       py -3.11 export_pdf.py --no-pdfa       # normales PDF statt PDF/A

PII-frei (keine Namen hardcodiert): arbeitet ueber Glob/Argumente.
"""
import glob
import os
import sys

import win32com.client as win32

PROFILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "profile")
WD_EXPORT_PDF = 17  # wdExportFormatPDF


def _ziel_dateien(argv):
    namen = [a for a in argv if not a.startswith("--")]
    if namen:
        return [n if os.path.isabs(n) else os.path.join(PROFILE, n) for n in namen]
    return sorted(glob.glob(os.path.join(PROFILE, "*.docx")))


def export(dateien, pdfa=True):
    app = win32.DispatchEx("Word.Application")
    app.Visible = False
    app.DisplayAlerts = 0
    erzeugt = []
    try:
        for src in dateien:
            if not os.path.exists(src):
                print(f"[SKIP] fehlt: {src}")
                continue
            pdf = os.path.splitext(src)[0] + ".pdf"
            d = app.Documents.Open(src, ReadOnly=True)
            try:
                d.ExportAsFixedFormat(pdf, WD_EXPORT_PDF, UseISO19005_1=pdfa)
                print(f"OK -> {pdf}" + ("  (PDF/A)" if pdfa else ""))
                erzeugt.append(pdf)
            finally:
                d.Close(False)
    finally:
        app.Quit()
    return erzeugt


if __name__ == "__main__":
    pdfa = "--no-pdfa" not in sys.argv
    ziele = _ziel_dateien(sys.argv[1:])
    if not ziele:
        print("Keine .docx gefunden (profile/ leer?).", file=sys.stderr)
        raise SystemExit(1)
    erzeugt = export(ziele, pdfa=pdfa)
    print(f"\n{len(erzeugt)} PDF(s) erzeugt.")

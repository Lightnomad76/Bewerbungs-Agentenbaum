# -*- coding: utf-8 -*-
"""Runner für ALLE verify_*.py — codiert den Interpreter-Split des Projekts
ausführbar (statt nur in CLAUDE.md): die meisten Selbsttests laufen über das
projekt-eigene venv (JobSpy/deterministische Agenten), `verify_ats_lint.py`
braucht python-docx und läuft global über `py -3.11`.

Aufruf:  py -3.11 verify_all.py   (oder .\.venv\Scripts\python.exe verify_all.py)
         exit 0 = alle grün, sonst Anzahl Fehlschläge.

Discovery: jede verify_*.py im Projekt-Root. Interpreter-Zuordnung via INTERPRETER
(Default = venv-Python); Einträge in GLOBAL_PY laufen über `py -3.11`.
"""
from __future__ import annotations

import os
import sys
import glob
import subprocess

BASE = os.path.dirname(os.path.abspath(__file__))
VENV_PY = os.path.join(BASE, ".venv", "Scripts", "python.exe")
GLOBAL_PY = ["py", "-3.11"]

# Verifies, die NICHT über das venv laufen (Grund in Klammern):
GLOBAL_PY_VERIFIES = {
    "verify_ats_lint.py",  # braucht python-docx (global installiert, nicht im venv)
}


def _interpreter(name: str):
    if name in GLOBAL_PY_VERIFIES:
        return list(GLOBAL_PY), "py -3.11"
    return [VENV_PY], ".venv"


def main():
    skripte = sorted(os.path.basename(p) for p in glob.glob(os.path.join(BASE, "verify_*.py")))
    skripte = [s for s in skripte if s != "verify_all.py"]
    if not skripte:
        print("Keine verify_*.py gefunden.")
        return 1

    if not os.path.exists(VENV_PY):
        print("WARNUNG: venv-Python nicht gefunden (" + VENV_PY + ") — "
              "venv-Verifies werden fehlschlagen. Setup: py -3.11 -m venv .venv")

    ergebnisse = []
    for name in skripte:
        cmd, label = _interpreter(name)
        proc = subprocess.run(cmd + [os.path.join(BASE, name)],
                              capture_output=True, text=True, encoding="utf-8", errors="replace")
        ok = proc.returncode == 0
        ergebnisse.append((name, ok, proc.returncode, label))
        status = "OK  " if ok else "FAIL"
        print("  " + status + "  " + name.ljust(26) + " [" + label + "]"
              + ("" if ok else "  (exit " + str(proc.returncode) + ")"))
        if not ok:
            # letzte Zeilen des Fehlschlags zeigen (Diagnose)
            tail = (proc.stdout + proc.stderr).strip().splitlines()[-6:]
            for ln in tail:
                print("       | " + ln)

    n = len(ergebnisse)
    fails = [e for e in ergebnisse if not e[1]]
    print()
    if fails:
        print("ERGEBNIS: " + str(n - len(fails)) + "/" + str(n) + " Suites grün — "
              + str(len(fails)) + " FAIL: " + ", ".join(e[0] for e in fails))
        return len(fails)
    print("ERGEBNIS: " + str(n) + "/" + str(n) + " Verify-Suites grün.")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    sys.exit(main())

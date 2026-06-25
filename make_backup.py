"""make_backup.py - re-run-faehiges Snapshot-Tool (reine stdlib).

Packt den aktuellen Projektstand als
  .backup_dateien/Bewerbungs-Agentenbaum_<label>.zip

Exclusions:
  - raus: .git, .backup_dateien (Top-Level), __pycache__ (ueberall), *.pyc, *.zip
  - drin: alles andere inkl. profile/ (persoenliche Daten, nur lokal) + state/ + briefs/
          -> vollstaendiger lokaler Rollback-Snapshot (ZIPs sind .gitignore't).

Alte ZIPs werden NIE angefasst (Rollback-Pfad). Gleiches Label = ueberschreiben.

  py -3.11 make_backup.py v1_stable
  py -3.11 make_backup.py             -> Label 'snapshot'
"""
import fnmatch
import os
import sys
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

BASE = Path(__file__).resolve().parent
TOP = BASE.name                          # "Bewerbungs-Agentenbaum" als Top-Ordner im ZIP
BACKUP_DIR = BASE / ".backup_dateien"

PRUNE_TOP = {".git", ".backup_dateien"}  # nur auf Top-Ebene aus dem Walk
EXCLUDE_DIR_NAMES = {"__pycache__"}      # an JEDER Stelle
EXCLUDE_FILE_GLOBS = ("*.pyc", "*.zip")


def make_backup(label: str):
    """Schreibt das ZIP und gibt (pfad, anzahl_dateien) zurueck."""
    BACKUP_DIR.mkdir(exist_ok=True)
    zip_path = BACKUP_DIR / f"{TOP}_{label}.zip"
    count = 0
    with ZipFile(zip_path, "w", ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(BASE):
            rel = Path(root).relative_to(BASE)
            if rel == Path("."):
                dirs[:] = [d for d in dirs if d not in PRUNE_TOP]
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIR_NAMES]
            for fn in files:
                if any(fnmatch.fnmatch(fn, g) for g in EXCLUDE_FILE_GLOBS):
                    continue
                fp = Path(root) / fn
                if fp == zip_path:        # sich selbst nie einpacken
                    continue
                zf.write(fp, arcname=str(Path(TOP) / fp.relative_to(BASE)))
                count += 1
    return zip_path, count


if __name__ == "__main__":
    label = sys.argv[1] if len(sys.argv) > 1 else "snapshot"
    path, count = make_backup(label)
    size_kb = round(path.stat().st_size / 1024, 1)
    print(f"ZIP geschrieben: {path}")
    print(f"  Dateien: {count}  |  Groesse: {size_kb} KB")

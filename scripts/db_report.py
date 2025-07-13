#!/usr/bin/env python3
"""
db_report.py  –  inventory every SQLite DB under the project

Usage
-----
$ python scripts/db_report.py                # search for *.db
$ python scripts/db_report.py swara.db       # limit to files named swara.db
"""

from __future__ import annotations
import sys, sqlite3
from pathlib import Path
from typing import Iterable, Tuple

# --------------------------------------------------------------------------- #
def find_db_files(pattern: str = "*.db") -> Iterable[Path]:
    """Recursively yield database files matching *pattern* under CWD."""
    root = Path.cwd()
    for path in root.rglob(pattern):
        if path.is_file():
            yield path

def table_counts(db_path: Path) -> Iterable[Tuple[str, int]]:
    """Return (table_name, row_count) tuples for every table in *db_path*."""
    with sqlite3.connect(str(db_path)) as conn:
        conn.row_factory = lambda cur, row: row[0]  # return first column directly
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()

        for tbl in tables:
            count = conn.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()
            yield tbl, count

# --------------------------------------------------------------------------- #
def main(pattern: str = "*.db") -> None:
    any_found = False
    for db in sorted(find_db_files(pattern)):
        any_found = True
        print(f"\n📦  {db.relative_to(Path.cwd())}")
        grand = 0
        for tbl, cnt in table_counts(db):
            grand += cnt
            print(f"   • {tbl:<20} : {cnt}")
        print(f"   └─ TOTAL rows        : {grand:,}")

    if not any_found:
        print(f"No databases matching pattern “{pattern}” found.")

# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    # Allow optional pattern argument, default = '*.db'
    pattern = sys.argv[1] if len(sys.argv) > 1 else "*.db"
    main(pattern)

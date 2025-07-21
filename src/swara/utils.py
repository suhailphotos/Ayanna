#  ── src/swara/utils.py ────────────────────────────────────────────
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Dict, List, Optional

from sqlmodel import select, update

from swara.db     import get_session
from swara.models import Track

RAW = (Path(__file__).resolve().parents[2] / "data" / "raw").resolve()


def _slug(txt: str) -> str:
    """
    Lower-case, collapse whitespace, strip all but a-z & 0-9.
    Useful for matching file stems to DB metadata.
    """
    txt = " ".join(txt.strip().split())               # trim + collapse spaces
    return re.sub(r"[^a-z0-9]", "", txt.casefold())   # keep only ascii letters/digits


def _build_file_index() -> Dict[str, Path]:
    """Return {slug('artist - title'): Path} for every mp3 under RAW/."""
    index: Dict[str, Path] = {}
    for mp3 in RAW.glob("*.mp3"):
        index.setdefault(_slug(mp3.stem), mp3)        # first match wins
    return index


def _rows_needing_fix() -> List[Track]:
    with get_session() as ses:
        return ses.exec(
            select(Track).where(
                (Track.audio_path == None) | (Track.download_status != "success")
            )
        ).all()


def repair_audio_path(debug: bool = False) -> None:
    file_index = _build_file_index()
    if not file_index:
        print("⚠  No .mp3 files found under", RAW)
        return

    fixed = missed = 0
    debug_rows: List[tuple[Track, str, Optional[Path]]] = []

    with get_session() as ses:
        for t in _rows_needing_fix():
            # if either field is blank we have nothing reliable to search with
            if not t.artist or not t.title:
                missed += 1
                if debug:
                    debug_rows.append((t, "(missing artist/title)", None))
                continue

            key   = _slug(f"{t.artist} - {t.title}")
            mp3   = file_index.get(key)

            if not mp3:
                missed += 1
                if debug and len(debug_rows) < 10:
                    debug_rows.append((t, key, None))
                continue

            ses.exec(
                update(Track)
                .where(Track.id == t.id)
                .values(audio_path=str(mp3),
                        download_status="success",
                        download_error=None)
            )
            fixed += 1

        ses.commit()

    print(f"✓ audio_path updated for {fixed} track(s)")
    if missed:
        print(f"  ⚠  {missed} track(s) still have no matching file")

    # optional debug output ---------------------------------------------------
    if debug and debug_rows:
        print("\nFirst few unmatched rows for inspection:")
        for t, slug_val, _ in debug_rows:
            print(f" – id={t.id[:6]}…  artist='{t.artist}'  title='{t.title}'"
                  f"  → slug='{slug_val}'")


if __name__ == "__main__":
    repair_audio_path(debug="--debug" in sys.argv)

#  ── swara/utils/repair_metadata.py ────────────────────────────────
from __future__ import annotations
from pathlib import Path

from sqlmodel import select, update
from oauthmanager.core import get_client

from swara.db import get_session
from swara.models import Track

RAW = (Path(__file__).resolve().parents[2] / "data" / "raw").resolve()

# ------------------------------------------------------------------ #
BATCH = 50                       # sp.tracks() limit
NEEDS_FIX = (
    (Track.title == "(placeholder)") |
    (Track.artist.in_(("", "?")))   |
    (Track.album == None)           |
    (Track.duration_ms == None)
)

def _chunks(seq, n=BATCH):
    for i in range(0, len(seq), n):
        yield seq[i : i + n]

def repair_tracks():
    sp = get_client("spotify")      # only   tracks-read-public   scope needed
    with get_session() as ses:
        to_fix = [row.id for row in ses.exec(select(Track).where(NEEDS_FIX))]
        if not to_fix:
            print("✓ No placeholder rows found")
            return

        print(f"Repairing {len(to_fix)} track rows …")

        for chunk in _chunks(to_fix):
            meta = {
                t["id"]: t for t in sp.tracks(chunk)["tracks"] if t  # filter None
            }

            for tid in chunk:
                m = meta.get(tid)
                if not m:                   # track vanished from Spotify
                    continue

                # ---- map Spotify JSON → columns ------------------
                values = dict(
                    title       = m["name"],
                    artist      = ", ".join(a["name"] for a in m["artists"]),
                    album       = m["album"]["name"],
                    duration_ms = m["duration_ms"],
                    # leave play_count / liked untouched
                )

                # ---- audio file on disk? -------------------------
                path = next(
                    RAW.glob(f"*{tid}*.mp3"),  # crude but works with our naming
                    None,
                )
                if path:
                    values["audio_path"]      = str(path)
                    values["download_status"] = "success"

                ses.exec(
                    update(Track)
                    .where(Track.id == tid)
                    .values(**values)
                )

        ses.commit()
        print("✓ done")

if __name__ == "__main__":
    repair_tracks()

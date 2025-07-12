"""
swara.downloader
================

Download tracks + metadata from every *allowed* Spotify playlist
into  **data/raw/**.

Requirements
------------
* `oauthmanager` for an authenticated spotipy client
* `spotdl` 4.2.x on the PATH (uses its CLI so we get YouTube fallback)
* `ffmpeg` on the PATH
* an `exclude.json` config copied to ~/.config/swara/ by `swara init`
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, Iterable

from oauthmanager.core import get_client

# ──────────────────────────────────────────────
# Paths & constants
# ──────────────────────────────────────────────
PROJECT_ROOT = Path(os.getenv("PROJECT_ROOT", Path(__file__).resolve().parents[2]))
RAW_DIR = PROJECT_ROOT / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

CFG_PATH = (
    Path(os.getenv("XDG_CONFIG_HOME", Path.home() / ".config")) / "swara" / "exclude.json"
)

# ──────────────────────────────────────────────
# Config helpers
# ──────────────────────────────────────────────
def _load_cfg() -> dict:
    if not CFG_PATH.exists():
        raise RuntimeError(
            f"Config not found: {CFG_PATH}. Run `swara init` or add exclude.json."
        )
    return json.loads(CFG_PATH.read_text())


def skip_playlist(pl: dict, cfg: dict) -> bool:
    """Return True if *pl* (a Spotify playlist object) is listed in exclude.json."""
    pl_id = pl["id"]

    # 1. fast path – match by ID
    if any(rec["id"] == pl_id for rec in cfg.get("playlists", [])):
        return True

    # 2. fallback – lenient match on name + owner
    pl_name = pl["name"].lower()
    pl_owner = (pl["owner"]["display_name"] or "").lower()

    for rec in cfg.get("playlists", []):
        if rec["name"].lower() == pl_name:
            owner_ok = not rec["owner"] or rec["owner"].lower() == pl_owner
            if owner_ok:
                return True
    return False


# ──────────────────────────────────────────────
# Spotify helpers
# ──────────────────────────────────────────────
def fetch_all_playlists(sp: Any) -> Iterable[Dict]:
    """Yield every playlist object for the current user."""
    limit, offset = 50, 0
    while True:
        resp = sp.current_user_playlists(limit=limit, offset=offset)
        for pl in resp["items"]:
            yield pl
        if resp["next"] is None:
            break
        offset += limit


def playlist_tracks(sp: Any, playlist_id: str) -> Iterable[Dict]:
    """Yield every *track* object in the given playlist."""
    limit, offset = 100, 0
    while True:
        resp = sp.playlist_items(playlist_id, limit=limit, offset=offset)
        for item in resp["items"]:
            yield item["track"]
        if resp["next"] is None:
            break
        offset += limit


# ──────────────────────────────────────────────
# Download
# ──────────────────────────────────────────────
def download_track(url: str, out_dir: Path, *, dry_run: bool = False) -> None:
    """Invoke spotDL to download one track by its Spotify URL."""
    if dry_run:
        print("  ·", url)
        return

    cmd = [
        "spotdl",
        url,
        "--output",
        str(out_dir / "{track_name}.{output_ext}"),
        "--path-template",
        str(out_dir / "{artist} - {title}.{output_ext}"),
        "--ffmpeg",
    ]
    subprocess.run(cmd, check=True)


# ──────────────────────────────────────────────
# Public entry point
# ──────────────────────────────────────────────
def main(*, dry_run: bool = False) -> None:
    """Download all tracks not excluded in the config."""
    cfg = _load_cfg()

    sp = get_client(
        "spotify",
        scopes=["playlist-read-private", "user-library-read"],
    )

    for pl in fetch_all_playlists(sp):
        if skip_playlist(pl, cfg):
            continue

        print(f"▶  {pl['name']} ({pl['tracks']['total']} tracks)")
        for track in playlist_tracks(sp, pl["id"]):
            url = track["external_urls"]["spotify"]
            try:
                download_track(url, RAW_DIR, dry_run=dry_run)
            except subprocess.CalledProcessError as e:
                print("⚠️  download failed:", url, e)
                continue


# allow `python -m swara.downloader --dry-run`
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Download Spotify playlists with Swara")
    parser.add_argument("--dry-run", action="store_true", help="List URLs only")
    args = parser.parse_args()
    main(dry_run=args.dry_run)

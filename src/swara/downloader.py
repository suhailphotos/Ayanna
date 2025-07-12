"""
swara.downloader
================

Incremental audio fetcher:

* Skips playlists listed in ~/.config/swara/exclude.json
* Downloads each Spotify **track-ID** only once
* Keeps two persistent logs under ~/.cache/swara/
    • downloaded_ids.json   – every successful track-ID
    • failed_ids.json       – track-IDs that spotDL/FFmpeg failed to fetch
* Prints a summary at the end so you know what worked / what didn’t
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, Iterable, Set

from oauthmanager.core import get_client
import click

# ──────────────────────────────────────────────
# Paths
# ──────────────────────────────────────────────
PROJECT_ROOT = Path(os.getenv("PROJECT_ROOT", Path(__file__).resolve().parents[2]))
RAW_DIR = PROJECT_ROOT / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

CONFIG_DIR = Path(os.getenv("XDG_CONFIG_HOME", Path.home() / ".config")) / "swara"
CFG_PATH = CONFIG_DIR / "exclude.json"

CACHE_DIR = Path.home() / ".cache" / "swara"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
DOWNLOADED_IDS = CACHE_DIR / "downloaded_ids.json"
FAILED_IDS = CACHE_DIR / "failed_ids.json"

AUDIO_EXTS = {".mp3", ".m4a", ".flac", ".wav", ".ogg"}

# ──────────────────────────────────────────────
# Helper I/O functions
# ──────────────────────────────────────────────
def _json_load(path: Path) -> Set[str]:
    if not path.exists():
        return set()
    try:
        return set(json.loads(path.read_text()))
    except Exception:
        return set()


def _json_dump(path: Path, data: Set[str]) -> None:
    path.write_text(json.dumps(sorted(data)))


# ──────────────────────────────────────────────
# Exclude-file helpers
# ──────────────────────────────────────────────
def _load_cfg() -> dict:
    if not CFG_PATH.exists():
        raise RuntimeError(
            f"Config not found: {CFG_PATH}. Run `swara init` or add exclude.json."
        )
    return json.loads(CFG_PATH.read_text())


def _skip_playlist(pl: dict, cfg: dict) -> bool:
    if any(rec["id"] == pl["id"] for rec in cfg.get("playlists", [])):
        return True

    name = pl["name"].lower()
    owner = (pl["owner"]["display_name"] or "").lower()
    for rec in cfg.get("playlists", []):
        if rec["name"].lower() == name and (
            not rec["owner"] or rec["owner"].lower() == owner
        ):
            return True
    return False


# ──────────────────────────────────────────────
# Spotify helpers
# ──────────────────────────────────────────────
def _fetch_playlists(sp: Any) -> Iterable[Dict]:
    limit, offset = 50, 0
    while True:
        resp = sp.current_user_playlists(limit=limit, offset=offset)
        yield from resp["items"]
        if resp["next"] is None:
            break
        offset += limit


def _playlist_tracks(sp: Any, playlist_id: str) -> Iterable[Dict]:
    limit, offset = 100, 0
    while True:
        resp = sp.playlist_items(playlist_id, limit=limit, offset=offset)
        for item in resp["items"]:
            yield item["track"]
        if resp["next"] is None:
            break
        offset += limit


# ──────────────────────────────────────────────
# spotDL wrapper
# ──────────────────────────────────────────────
def _ensure_ffmpeg() -> str:
    """
    Verify ffmpeg is discoverable and return its absolute path.
    Raises RuntimeError with install hints otherwise.
    """
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        return ffmpeg_path

    raise RuntimeError(
        "ffmpeg executable not found on PATH – spotDL cannot convert audio.\n\n"
        "Install suggestions:\n"
        "  • Conda:   conda install -c conda-forge ffmpeg\n"
        "  • Ubuntu:  sudo apt install ffmpeg\n"
        "  • macOS:   brew install ffmpeg\n"
        "  • Windows: choco install ffmpeg   (or scoop / winget)"
    )


def _download_track(url: str, out_dir: Path, *, dry: bool = False) -> None:
    """
    Call `spotdl download <url>` with a custom output template.
    """
    if dry:
        click.echo(f"  · {url}")
        return

    subprocess.run(
        [
            "spotdl", "download", url,
            "--output", str(out_dir / "{artist} - {title}")
        ],
        check=True,
    )
    # spotDL appends ".mp3" automatically based on chosen format


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────
def main(*, dry_run: bool = False) -> None:
    _ensure_ffmpeg()

    cfg = _load_cfg()
    downloaded = _json_load(DOWNLOADED_IDS)
    failed = _json_load(FAILED_IDS)

    sp = get_client("spotify", scopes=["playlist-read-private", "user-library-read"])

    new_success, new_fail = 0, 0

    for pl in _fetch_playlists(sp):
        if _skip_playlist(pl, cfg):
            continue

        click.secho(f"▶  {pl['name']} ({pl['tracks']['total']} tracks)", fg="cyan")
        for track in _playlist_tracks(sp, pl["id"]):
            tid = track["id"]
            if tid in downloaded:
                continue  # already have it
            url = track["external_urls"]["spotify"]

            try:
                _download_track(url, RAW_DIR, dry=dry_run)
                if not dry_run:
                    downloaded.add(tid)
                    failed.discard(tid)
                    new_success += 1
            except subprocess.CalledProcessError as exc:
                click.secho(f"  ⚠️  failed {url} → {exc}", fg="red")
                if not dry_run:
                    failed.add(tid)
                    new_fail += 1

    # Persist logs
    if not dry_run:
        _json_dump(DOWNLOADED_IDS, downloaded)
        _json_dump(FAILED_IDS, failed)

    # Summary
    click.echo()
    if dry_run:
        click.secho("Dry-run complete – no files downloaded.", fg="yellow")
    else:
        click.secho(
            f"Finished – {new_success} new ↓   {new_fail} failed (see {FAILED_IDS}).",
            fg="green" if new_fail == 0 else "yellow",
        )


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="Download Spotify playlists with Swara")
    p.add_argument("--dry-run", action="store_true", help="List URLs only, no download")
    main(dry_run=p.parse_args().dry_run)

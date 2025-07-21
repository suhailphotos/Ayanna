"""
swara.downloader
================
DB-backed incremental fetcher
─────────────────────────────
• honours ExcludePlaylist / ExcludeTrack tables
• sets Track.liked from “Liked songs”
• updates Track.play_count (# of playlists it belongs to)
• keeps Track.download_status in sync with the file-system
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Iterable, Dict

import click
from oauthmanager.core import get_client
from sqlmodel import select, update

from swara.db import get_session
from swara.models import Playlist, Track, ExcludePlaylist, ExcludeTrack

# ────────────────────────────── paths ───────────────────────────── #
ROOT = Path(os.getenv("PROJECT_ROOT", Path(__file__).resolve().parents[2]))
RAW  = ROOT / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)

SPOTDL_CACHE = Path.home() / ".spotdl"

# ─────────────────────────── helpers ────────────────────────────── #
def _ensure_ffmpeg() -> None:
    if shutil.which("ffmpeg"):
        return
    raise RuntimeError("ffmpeg not on PATH – e.g. `conda install -c conda-forge ffmpeg`")

def _spotdl(url: str, out_dir: Path, *, dry: bool = False) -> None:
    if dry:
        click.echo(f"  · {url}")
        return
    subprocess.run(
        ["spotdl", "download", url, "--output", str(out_dir / "{artist} - {title}")],
        text=True,
        check=True,
    )
    # polite delay → avoids Spotify 429 during large batches
    time.sleep(0.12)   # 120 ms  ≈ 8-9 requests / second

def _fetch_all_playlists(sp) -> Iterable[Dict]:
    lim = 50
    off = 0
    while True:
        page = sp.current_user_playlists(limit=lim, offset=off)
        yield from page["items"]
        if page["next"] is None:
            break
        off += lim

def _playlist_tracks(sp, pid: str) -> Iterable[Dict]:
    lim = 100
    off = 0
    while True:
        page = sp.playlist_items(pid, limit=lim, offset=off)
        for item in page["items"]:
            yield item["track"]
        if page["next"] is None:
            break
        off += lim

def _saved_track_ids(sp) -> set[str]:
    """One pass over the 'Liked songs' collection (max 50 per page)."""
    ids: set[str] = set()
    lim = 50
    off = 0
    while True:
        page = sp.current_user_saved_tracks(limit=lim, offset=off)
        ids |= {item["track"]["id"] for item in page["items"]}
        if page["next"] is None:
            break
        off += lim
    return ids

def provider_snapshot(sp):
    """Return (playlist_ids, track_ids)."""
    pls = {p["id"] for p in _fetch_all_playlists(sp)}
    tids = set()
    for pid in pls:
        tids |= {t["id"] for t in _playlist_tracks(sp, pid)}
    return pls, tids

# ─────────────────────────── main routine ───────────────────────── #
def main(*, dry_run: bool = False, verbose: bool = False, clear_cache: bool = False) -> None:
    _ensure_ffmpeg()

    if clear_cache and SPOTDL_CACHE.exists():
        shutil.rmtree(SPOTDL_CACHE)
        click.secho("• spotDL cache cleared", fg="yellow")

    sp = get_client("spotify", scopes=["playlist-read-private", "user-library-read"])
    liked_ids = _saved_track_ids(sp)

    with get_session() as ses:
        excluded_pl_ids = set(ses.exec(select(ExcludePlaylist.id)))
        excluded_tr_ids = set(ses.exec(select(ExcludeTrack.id)))

    # ── scan Spotify & upsert DB ─────────────────────────────────── #
    click.secho("Scanning Spotify …", fg="cyan")
    new_tracks: list[str] = []
    track_counts: Counter[str] = Counter()

    with get_session() as ses:
        for pl in _fetch_all_playlists(sp):
            pid = pl["id"]
            if pid in excluded_pl_ids:
                if verbose:
                    click.echo(f"⤼  skip  {pl['name']}")
                continue

            if verbose:
                click.secho(f"▶  {pl['name']}  ({pl['tracks']['total']} tracks)", fg="cyan")

            ses.merge(
                Playlist(
                    id=pid,
                    name=pl["name"],
                    owner_id=pl["owner"]["id"],
                    tracks_total=pl["tracks"]["total"],
                    last_scan=datetime.utcnow(),
                )
            )

            for tr in _playlist_tracks(sp, pid):
                tid = tr["id"]
                if tid in excluded_tr_ids:
                    continue

                track_counts[tid] += 1
                row = ses.get(Track, tid)

                if not row:
                    row = Track(
                        id=tid,
                        title=tr["name"],
                        artist=", ".join(a["name"] for a in tr["artists"]),
                        album=tr["album"]["name"],
                        duration_ms=tr["duration_ms"],
                        play_count=0,           # will set below
                    )
                    new_tracks.append(tid)

                # ── UPDATE corrupted rows ────────────────────────────
                if row.title == "(placeholder)":
                    row.title = tr["name"]
                if row.artist in ("?", None, ""):
                    row.artist = ", ".join(a["name"] for a in tr["artists"])
                if row.album in (None, ""):
                    row.album = tr["album"]["name"]
                if row.duration_ms is None:
                    row.duration_ms = tr["duration_ms"]
                row.liked = tid in liked_ids
                ses.add(row)

        # second pass: update play_count in bulk
        for tid, n in track_counts.items():
            ses.exec(
                update(Track)
                .where(Track.id == tid)
                .values(play_count=n)
            )

        ses.commit()

    click.echo(f"  • discovered {len(new_tracks)} new tracks")
    click.echo(f"  • updated play_count on {len(track_counts)} tracks")

    # ── pending queue ────────────────────────────────────────────── #
    with get_session() as ses:
        pending = ses.exec(
            select(Track).where(Track.download_status == "pending")
        ).all()

    if not pending:
        click.secho("Nothing to download – library up-to-date.", fg="green")
        return

    click.secho(f"\nDownloading {len(pending)} tracks …", fg="cyan")
    ok = bad = 0
    for t in pending:
        try:
            _spotdl(f"https://open.spotify.com/track/{t.id}", RAW, dry=dry_run)
        except subprocess.CalledProcessError as exc:
            bad += 1
            if not dry_run:
                with get_session() as ses:
                    ses.exec(
                        update(Track)
                        .where(Track.id == t.id)
                        .values(download_status="failed",
                                download_error=str(exc))
                    )
                    ses.commit()
            click.secho(f"  ⚠  {t.title} failed", fg="red")
            continue

        if not dry_run:
            rel = f"{t.artist} - {t.title}.mp3"
            with get_session() as ses:
                ses.exec(
                    update(Track)
                    .where(Track.id == t.id)
                    .values(download_status="success",
                            audio_path=str(RAW / rel),
                            download_error=None)
                )
                ses.commit()
        ok += 1

    # ── summary ──────────────────────────────────────────────────── #
    click.echo()
    if dry_run:
        click.secho("Dry-run complete – no files downloaded.", fg="yellow")
    else:
        click.secho(
            f"Finished – {ok} downloaded   {bad} failed",
            fg="green" if bad == 0 else "yellow",
        )

# ─────────────────────────── CLI glue ──────────────────────────── #
if __name__ == "__main__":
    import argparse, sys
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run",     action="store_true", help="list but don’t download")
    ap.add_argument("-v", "--verbose", action="store_true", help="show playlists while scanning")
    ap.add_argument("--clear-cache", action="store_true", help="delete ~/.spotdl/ first")
    args = ap.parse_args()
    sys.exit(main(dry_run=args.dry_run, verbose=args.verbose, clear_cache=args.clear_cache))

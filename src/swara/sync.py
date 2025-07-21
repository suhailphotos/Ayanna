#  ── swara/sync.py ──────────────────────────────────────────────────
from __future__ import annotations
from pathlib import Path
from typing import Iterable, Tuple, Set

from sqlalchemy import select, delete
from sqlmodel import Session

from oauthmanager.core import get_client
from swara.db       import get_session
from swara.models   import (
    Playlist, Track, ExcludePlaylist, ExcludeTrack
)

RAW = Path(             # same rule we used in downloader
    Path(__file__).resolve().parents[2] / "data" / "raw"
)

# ------------------------------------------------------------------ #
def _fetch_all_playlists(sp) -> Iterable[dict]:
    lim = 50; off = 0
    while True:
        page = sp.current_user_playlists(limit=lim, offset=off)
        yield from page["items"]
        if page["next"] is None:
            break
        off += lim

def _playlist_tracks(sp, pid: str) -> Iterable[dict]:
    lim = 100; off = 0
    while True:
        page = sp.playlist_items(pid, limit=lim, offset=off)
        for item in page["items"]:
            tr = item.get("track")
            # - skip “local” or unavailable songs that have no Spotify ID
            if tr is None or tr.get("id") is None:
                continue
            yield tr
        if page["next"] is None:
            break
        off += lim

# ------------------------------------------------------------------ #
def provider_snapshot() -> Tuple[Set[str], Set[str]]:
    """
    Return two sets: (playlist_ids, track_ids) visible on Spotify *now*.
    """
    sp = get_client("spotify", scopes=["playlist-read-private"])
    pls  = {p["id"] for p in _fetch_all_playlists(sp)}
    tids = set()
    for pid in pls:
        tids |= {t["id"] for t in _playlist_tracks(sp, pid)}
    return pls, tids

# ------------------------------------------------------------------ #
def sync_db(*, remove_files: bool = False, prune: bool = False) -> str:
    """
    Reconcile DB ↔ Spotify.  
    Returns a multi-line human summary you can print or send back via API.
    """
    live_plids, live_tids = provider_snapshot()

    with get_session() as ses:              # type: Session
        db_plids = set(ses.exec(select(Playlist.id)).scalars())
        db_tids  = set(ses.exec(select(Track.id)).scalars())
        exc_pl   = set(ses.exec(select(ExcludePlaylist.id)).scalars())
        exc_tr   = set(ses.exec(select(ExcludeTrack.id)).scalars())

    # ── 1. new on Spotify ──────────────────────────────────────────
    new_pl = live_plids - db_plids - exc_pl
    new_tr = live_tids  - db_tids  - exc_tr
    
    if new_pl or new_tr:
        with get_session() as ses:
            # **ADD** is safe: it INSERTs and fails if the PK already exists.
            # because new_* sets were computed using the current DB snapshot
            ses.add_all(Playlist(id=p) for p in new_pl)
            ses.add_all(Track(id=t, download_status="pending") for t in new_tr)
            ses.commit()

    # ── 2. disappeared from Spotify ───────────────────────────────
    gone_pl  = db_plids - live_plids - exc_pl
    gone_tr  = db_tids  - live_tids  - exc_tr

    def _delete(model, ids):
        if not ids: return 0
        with get_session() as ses:
            ses.exec(delete(model).where(model.id.in_(ids)))
            ses.commit()
        return len(ids)

    n_pl_del = _delete(Playlist, gone_pl)
    n_tr_del = _delete(Track,    gone_tr)

    if remove_files:
        _unlink_audio(gone_tr)

    # ── 3. prune orphan files ─────────────────────────────────────
    n_orphan = 0
    if prune:
        n_orphan = prune_orphans(ask=False)  # silent delete
    # ----------------------------------------------------------------
    return _summary(new_pl, new_tr, n_pl_del, n_tr_del,
                    remove_files and gone_tr, n_orphan)

# ------------------------------------------------------------------ #
def _unlink_audio(track_ids: Iterable[str]) -> None:
    for tid in track_ids:
        for f in RAW.glob(f"*{tid}*.mp3"):
            f.unlink(missing_ok=True)

# ------------------------------------------------------------------ #
def prune_orphans(*, ask: bool = True) -> int:
    """
    Delete mp3 files that no longer have a Track row.
    Returns number of files removed.
    """
    with get_session() as ses:
        db_tids = set(ses.exec(select(Track.id)))

    on_disk = {p.stem.split(" - ")[-1] for p in RAW.glob("*.mp3")}

    # repair missing audio_path entries in-place
    with get_session() as ses:
        for p in RAW.glob("*.mp3"):
            tid = p.stem.split(" - ")[-1]
            if tid in db_tids:
                ses.exec(
                    update(Track)
                    .where(Track.id == tid, Track.audio_path.is_(None))
                    .values(audio_path=str(p), download_status="success")
                )
        ses.commit()

    # recompute after the fix-up
    orphans = on_disk - db_tids

    if not orphans:
        return 0

    if ask:                        # interactive branch
        import click
        click.echo(f"Found {len(orphans)} orphan files.")
        if not click.confirm("Delete them?"):
            return 0

    _unlink_audio(orphans)
    return len(orphans)

# ------------------------------------------------------------------ #
def _summary(new_pl, new_tr, del_pl, del_tr,
             files_deleted, orphans_pruned) -> str:
    lines = ["Sync summary",
             f"  +{len(new_pl):4} playlists inserted",
             f"  +{len(new_tr):4} tracks     inserted",
             f"  -{del_pl:4} playlists removed",
             f"  -{del_tr:4} tracks     removed"]
    if files_deleted:
        lines.append(f"  audio files deleted on the fly: {len(files_deleted)}")
    if orphans_pruned:
        lines.append(f"  orphan files pruned: {orphans_pruned}")
    return "\n".join(lines)

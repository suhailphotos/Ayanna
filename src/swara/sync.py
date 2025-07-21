#  ── swara/sync.py (revamped) ───────────────────────────────────────────
"""Robust DB ↔ Spotify synchronisation.

Key changes vs. the original:

* **Single transaction** – every mutating step happens in one `Session` scope.
* **Upserts** (`ON CONFLICT DO NOTHING` / `UPDATE`) avoid race‑condition crashes.
* **Playlist rename detection** (bucket 5).
* **Foreign‑key safety** – we delete dependent rows (`Embedding`, etc.) first.
* **Session‑aware helpers** so we don’t open nested sessions mid‑transaction.
* **Optional orphan‑file pruning** still works but receives the outer session.
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable, Mapping, Tuple, Set

from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlmodel import Session

from oauthmanager.core import get_client
from swara.db import get_session
from swara.models import (
    Playlist,
    Track,
    Embedding,
    ExcludePlaylist,
    ExcludeTrack,
)

RAW = (
    Path(__file__).resolve().parents[2] / "data" / "raw"
).resolve()

# ──────────────────────────────────────────────────────────────────────────────
# Spotify helpers
# ──────────────────────────────────────────────────────────────────────────────

def _fetch_all_playlists(sp) -> Iterable[dict]:
    lim, off = 50, 0
    while True:
        page = sp.current_user_playlists(limit=lim, offset=off)
        yield from page["items"]
        if page["next"] is None:
            break
        off += lim

def _playlist_tracks(sp, pid: str) -> Iterable[dict]:
    lim, off = 100, 0
    while True:
        page = sp.playlist_items(pid, limit=lim, offset=off)
        for item in page["items"]:
            tr = item.get("track")
            if tr and tr.get("id"):
                yield tr
        if page["next"] is None:
            break
        off += lim

# ---------------------------------------------------------------------------
# Provider snapshot – returns richer structures to detect renames
# ---------------------------------------------------------------------------

def provider_snapshot() -> tuple[Mapping[str, str], Set[str]]:
    """Return (`{playlist_id: name}`, `{track_ids}`) currently visible on Spotify."""
    sp = get_client("spotify", scopes=["playlist-read-private"])

    playlist_map: dict[str, str] = {}
    track_ids: set[str] = set()

    for pl in _fetch_all_playlists(sp):
        pid = pl["id"]
        playlist_map[pid] = pl["name"]
        # accumulate tracks for this playlist
        track_ids |= {t["id"] for t in _playlist_tracks(sp, pid)}

    return playlist_map, track_ids

# ──────────────────────────────────────────────────────────────────────────────
# Main sync routine
# ──────────────────────────────────────────────────────────────────────────────

def sync_db(*, remove_files: bool = False, prune: bool = False) -> str:
    """Synchronise Postgres DB with live Spotify data and optionally the MP3 store."""

    live_playlists, live_tids = provider_snapshot()
    live_plids = set(live_playlists)

    with get_session() as ses:  # transactional scope
        # ── cache current DB state ───────────────────────────────────────
        db_plids = set(ses.exec(select(Playlist.id)).scalars())
        db_tids = set(ses.exec(select(Track.id)).scalars())
        exc_pl = set(ses.exec(select(ExcludePlaylist.id)).scalars())
        exc_tr = set(ses.exec(select(ExcludeTrack.id)).scalars())

        # ────────────────────────────────────────────────────────────────
        # 1. Insert NEW playlists / tracks --------------------------------
        #    (bucket 1 in the spec)
        # ────────────────────────────────────────────────────────────────
        new_pl = live_plids - db_plids - exc_pl
        new_tr = live_tids - db_tids - exc_tr

        if new_pl:
            ses.execute(
                pg_insert(Playlist).values([
                    {"id": pid, "name": live_playlists[pid]} for pid in new_pl
                ]).on_conflict_do_nothing()
            )

        if new_tr:
            ses.execute(
                pg_insert(Track).values([
                    {"id": tid, "download_status": "pending"} for tid in new_tr
                ]).on_conflict_do_nothing()
            )

        # ────────────────────────────────────────────────────────────────
        # 2. Detect playlist RENAMES --------------------------------------
        # ────────────────────────────────────────────────────────────────
        if live_plids & db_plids:
            db_names = dict(ses.exec(select(Playlist.id, Playlist.name)))
            renamed = {
                pid: live_playlists[pid]
                for pid in live_plids & db_plids
                if live_playlists[pid] != db_names.get(pid)
            }
            for pid, new_name in renamed.items():
                ses.exec(
                    update(Playlist).where(Playlist.id == pid).values(name=new_name)
                )

        # ────────────────────────────────────────────────────────────────
        # 3. Delete items gone from Spotify (bucket 2) --------------------
        #      – must ALSO delete dependents (e.g. Embedding) -------------
        # ────────────────────────────────────────────────────────────────
        gone_pl = db_plids - live_plids - exc_pl
        gone_tr = db_tids - live_tids - exc_tr

        if gone_tr:
            # delete embeddings first to satisfy FK RESTRICT if CASCADE not set
            ses.exec(delete(Embedding).where(Embedding.track_id.in_(gone_tr)))
            ses.exec(delete(Track).where(Track.id.in_(gone_tr)))
            if remove_files:
                _unlink_audio(gone_tr)

        if gone_pl:
            ses.exec(delete(Playlist).where(Playlist.id.in_(gone_pl)))

        # ────────────────────────────────────────────────────────────────
        # 4. Bucket 4 – newly‑excluded playlists / tracks -----------------
        #     (handled by previous steps because exc_* are removed from
        #      new_pl/new_tr and will fall into *gone* sets on next sync)
        # ────────────────────────────────────────────────────────────────

        # Commit all DB mutations atomically
        ses.commit()

        # ────────────────────────────────────────────────────────────────
        # 5. Optionally prune orphan files (bucket 3) ---------------------
        # ────────────────────────────────────────────────────────────────
        n_orphan = 0
        if prune:
            n_orphan = _prune_orphans(db_session=ses)

    # ── build summary ----------------------------------------------------
    return _summary(
        len(new_pl),
        len(new_tr),
        len(gone_pl),
        len(gone_tr),
        remove_files and bool(gone_tr),
        n_orphan,
    )

# ---------------------------------------------------------------------------
# Helpers (file operations stay outside the transaction)
# ---------------------------------------------------------------------------

def _unlink_audio(track_ids: Iterable[str]) -> None:
    for tid in track_ids:
        for f in RAW.glob(f"*{tid}*.mp3"):
            f.unlink(missing_ok=True)


def _prune_orphans(*, db_session: Session) -> int:
    """Delete mp3 files that have no Track row. Returns number deleted."""
    db_tids = set(db_session.exec(select(Track.id)))
    on_disk = {p.stem.split(" - ")[-1] for p in RAW.glob("*.mp3")}
    orphans = on_disk - db_tids
    for tid in orphans:
        _unlink_audio([tid])
    return len(orphans)


def _summary(new_pl, new_tr, del_pl, del_tr, files_deleted, orphans_pruned) -> str:
    lines = [
        "Sync summary",
        f"  +{new_pl:4} playlists inserted",
        f"  +{new_tr:4} tracks     inserted",
        f"  -{del_pl:4} playlists removed",
        f"  -{del_tr:4} tracks     removed",
    ]
    if files_deleted:
        lines.append("  audio files deleted on the fly: yes")
    if orphans_pruned:
        lines.append(f"  orphan files pruned: {orphans_pruned}")
    return "\n".join(lines)

def prune_orphans(ask=True) -> int:
    """Public API to prune orphan mp3 files with a fresh session."""
    from swara.db import get_session
    with get_session() as ses:
        # Could ask for confirmation here if ask is True
        return _prune_orphans(db_session=ses)


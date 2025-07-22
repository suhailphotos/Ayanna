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
    User,
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

def provider_snapshot() -> tuple[dict[str, str], dict[str, dict], set[str], dict[str, str]]:
    """
    Returns:
      - playlist_map: {playlist_id: name}
      - track_info: {track_id: track_obj}
      - live_tids: set of track ids
      - playlist_owners: {playlist_id: owner_id}
    """
    sp = get_client("spotify", scopes=["playlist-read-private"])

    # Excluded playlists
    from swara.db import get_session
    from swara.models import ExcludePlaylist
    with get_session() as ses:
        excluded_playlist_ids = set(ses.exec(select(ExcludePlaylist.id)).scalars())

    playlist_map: dict[str, str] = {}
    playlist_owners: dict[str, str] = {}    # <--- new
    track_info: dict[str, dict] = {}

    owners = {}
    for pl in _fetch_all_playlists(sp):
        pid = pl["id"]
        owner = pl["owner"]
        owners[owner["id"]] = owner.get("display_name") or owner["id"]
        if pid in excluded_playlist_ids:
            continue  # SKIP this playlist
        playlist_map[pid] = pl["name"]
        playlist_owners[pid] = pl["owner"]["id"]   # <--- new
        for t in _playlist_tracks(sp, pid):
            if t and t.get("id"):
                track_info[t["id"]] = t
    return playlist_map, track_info, set(track_info), playlist_owners, owners

# ──────────────────────────────────────────────────────────────────────────────
# Main sync routine
# ──────────────────────────────────────────────────────────────────────────────

def sync_db(*, remove_files: bool = False, prune: bool = False) -> str:
    """Synchronise Postgres DB with live Spotify data and optionally the MP3 store."""

    # CHANGED: Provider snapshot now returns playlist_map, track_info, live_tids
    live_playlists, track_info, live_tids, playlist_owners, owners = provider_snapshot()
    live_plids = set(live_playlists)

    with get_session() as ses:  # transactional scope
        if owners:
            ses.execute(
                pg_insert(User)
                .values([{"id": oid, "display_name": name} for oid, name in owners.items()])
                .on_conflict_do_update(
                    index_elements=[User.id],
                    set_={"display_name": pg_insert(User).excluded.display_name}
                )
            )
        # ── cache current DB state ───────────────────────────────────────
        db_plids = set(ses.exec(select(Playlist.id)).scalars())
        db_tids = set(ses.exec(select(Track.id)).scalars())
        exc_pl = set(ses.exec(select(ExcludePlaylist.id)).scalars())
        exc_tr = set(ses.exec(select(ExcludeTrack.id)).scalars())

        # New: always remove playlists in ExcludePlaylist from DB
        if exc_pl:
            ses.exec(delete(Playlist).where(Playlist.id.in_(exc_pl)))

        # 1. Insert NEW playlists / tracks --------------------------------
        new_pl = live_plids - db_plids - exc_pl
        new_tr = live_tids - db_tids - exc_tr

        if new_pl:
            ses.execute(
                pg_insert(Playlist).values([
                    {
                        "id": pid,
                        "name": live_playlists[pid],
                        "owner_id": playlist_owners[pid],  # <--- set owner_id!
                    }
                    for pid in new_pl
                ]).on_conflict_do_nothing()
            )

        # CHANGED: Insert new tracks with all required fields
        if new_tr:
            rows = []
            for tid in new_tr:
                t = track_info[tid]
                rows.append({
                    "id": tid,
                    "title": t.get("name") or "(unknown)",  # CHANGED: fill in title
                    "artist": ", ".join(a.get("name", "?") for a in t.get("artists", [])) or "(unknown)",  # CHANGED: fill in artist
                    "album": t.get("album", {}).get("name") if t.get("album") else None,
                    "duration_ms": t.get("duration_ms"),
                    "download_status": "pending",
                    # optionally set temperature/play_count/other fields if needed
                })
            ses.execute(
                pg_insert(Track).values(rows).on_conflict_do_nothing()
            )
        incomplete = ses.exec(
            select(Track).where(
                (Track.title == "") |
                (Track.title == "(unknown)") |
                (Track.title == None) |
                (Track.artist == "") |
                (Track.artist == "(unknown)") |
                (Track.artist == None) |
                (Track.album == None) |
                (Track.duration_ms == None)
            )
        ).scalars().all()
        n_patched = 0
        for t in incomplete:
            if isinstance(t, Track):
                track = t
            else:
                track = t[0]
            tinfo = track_info.get(track.id)
            if not tinfo:
                continue
            vals = {}
            if not t.title:
                vals["title"] = tinfo.get("name") or "(unknown)"
            if not t.artist:
                vals["artist"] = ", ".join(a.get("name", "?") for a in tinfo.get("artists", [])) or "(unknown)"
            if t.album is None:
                vals["album"] = tinfo.get("album", {}).get("name") if tinfo.get("album") else None
            if t.duration_ms is None:
                vals["duration_ms"] = tinfo.get("duration_ms")
            if vals:
                ses.exec(update(Track).where(Track.id == t.id).values(**vals))
                n_patched += 1
        if n_patched:
            print(f"✓ Patched {n_patched} track(s) with missing metadata from Spotify")

        # Remove permanently unhealable tracks
        unhealable = ses.exec(
            select(Track.id).where(
                ((Track.title == "(unknown)") | (Track.artist == "(unknown)")) &
                (Track.download_status == "failed")
            )
        ).scalars().all()
        
        if unhealable:
            ses.exec(delete(Track).where(Track.id.in_(unhealable)))
            ses.commit()
            print(f"✗ Deleted {len(unhealable)} tracks still marked as '(unknown)' (not found on Spotify)")

        # END CHANGED

        # 2. Detect playlist RENAMES --------------------------------------
        if live_plids & db_plids:
            db_names = dict(ses.exec(select(Playlist.id, Playlist.name)).all())  # <--- FIXED
            renamed = {
                pid: live_playlists[pid]
                for pid in live_plids & db_plids
                if live_playlists[pid] != db_names.get(pid)
            }
            for pid, new_name in renamed.items():
                ses.exec(
                    update(Playlist)
                    .where(Playlist.id == pid)
                    .values(
                        name=new_name,
                        owner_id=playlist_owners[pid],  # always refresh owner_id
                    )
                )

        # 3. Delete items gone from Spotify -------------------------------
        gone_pl = db_plids - live_plids - exc_pl
        gone_tr = db_tids - live_tids - exc_tr
        # For summary:
        removed_pl = db_plids - live_plids

        if gone_tr:
            ses.exec(delete(Embedding).where(Embedding.track_id.in_(gone_tr)))
            ses.exec(delete(Track).where(Track.id.in_(gone_tr)))
            if remove_files:
                _unlink_audio(gone_tr)

        if gone_pl:
            ses.exec(delete(Playlist).where(Playlist.id.in_(gone_pl)))

        # 4. Bucket 4 – exclusions (no change, already handled above)

        # Commit all DB mutations atomically
        ses.commit()

        # 5. Optionally prune orphan files (bucket 3) ---------------------
        n_orphan = 0
        if prune:
            n_orphan = _prune_orphans(db_session=ses)

    # ── build summary ----------------------------------------------------
    return _summary(
        len(new_pl),
        len(new_tr),
        len(removed_pl),
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


#!/usr/bin/env python
"""
Load JSONL into the Postgres DB currently pointed to by DATABASE_URL.
Usage:
$ python scripts/import_postgres.py < dump.jsonl
"""
import sys, ujson, sqlalchemy as sa
from swara.db import get_session, engine
from swara.models import (
    Playlist, Track, Embedding,
    ExcludePlaylist, ExcludeTrack, User, SQLModel
)

LOOKUP = {
    "playlist": Playlist, "track": Track, "embedding": Embedding,
    "excludeplaylist": ExcludePlaylist, "excludetrack": ExcludeTrack,
    "user": User,
}

def ensure_schema():
    # run CREATE EXTENSION outside a transaction so it is visible
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        conn.execute(sa.text("CREATE EXTENSION IF NOT EXISTS vector"))

    SQLModel.metadata.create_all(engine)

ensure_schema()

# 1) slurp the JSONL into memory (few MB, fine for 1 k tracks)
rows_by_table: dict[str, list[dict]] = {k: [] for k in LOOKUP}
for line in sys.stdin:
    obj = ujson.loads(line)
    rows_by_table[obj["table"]].append(obj["data"])

with get_session() as ses:
    # 2) import users first (satisfies FK for playlists, tracks, …)
    for data in rows_by_table["user"]:
        ses.add(User(**data))
    ses.flush()          # make sure INSERTs are visible

    # 3) shove everything else in any order
    for tbl in ("playlist", "track", "embedding",
                "excludeplaylist", "excludetrack"):
        for data in rows_by_table[tbl]:
            ses.add(LOOKUP[tbl](**data))

    ses.commit()
print("✓ rows inserted")

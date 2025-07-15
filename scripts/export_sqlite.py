#!/usr/bin/env python
"""
Dump every row from SQLite to JSONL.
$ poetry run python scripts/export_sqlite.py > dump.jsonl
"""
from __future__ import annotations
import sys, json
from sqlmodel import select
from swara.db import get_session
from swara.models import (
    Playlist, Track, Embedding,
    ExcludePlaylist, ExcludeTrack, User,
)

TABLES = [Playlist, Track, Embedding, ExcludePlaylist, ExcludeTrack, User]

with get_session() as ses:
    for model in TABLES:
        for row in ses.exec(select(model)):
            out = {"table": model.__tablename__, "data": row.model_dump(mode="json")}
            sys.stdout.write(json.dumps(out, default=str) + "\n")

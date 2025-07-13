from datetime import datetime
from sqlmodel import Field, SQLModel, Column
from pgvector.sqlalchemy import Vector

# ──────────────────────────────────────────────
# Core entities
# ──────────────────────────────────────────────


class User(SQLModel, table=True):
    id: str = Field(primary_key=True)      # Spotify user-ID or email
    display_name: str | None = None
    is_active: bool = True
    created: datetime = Field(default_factory=datetime.utcnow)


class Playlist(SQLModel, table=True):
    id: str = Field(primary_key=True)
    name: str
    owner: str | None = None
    tracks_total: int | None = None
    first_seen: datetime = Field(default_factory=datetime.utcnow)
    last_scan: datetime | None = None

class Track(SQLModel, table=True):
    id: str = Field(primary_key=True)
    title: str
    artist: str
    album: str | None = None
    duration_ms: int | None = None

    liked: bool = False

    # playback / curation knobs
    play_count: int = 0
    temperature: float = 1.0      # 1.0 = neutral, >1 = play more often
    last_played: datetime | None = None

    # download metadata
    audio_path: str | None = None
    download_status: str = "pending"   # pending | success | failed
    download_error: str | None = None
    first_seen: datetime = Field(default_factory=datetime.utcnow)

    # NEW FIELD (foreign key to user)
    owner_id: str | None = Field(default=None, foreign_key="user.id")

class Embedding(SQLModel, table=True):
    track_id: str = Field(
        foreign_key="track.id", primary_key=True, index=True
    )
    vector: list[float] = Field(sa_column=Column(Vector(768)))
    model: str = "CLAP-630M"
    created: datetime = Field(default_factory=datetime.utcnow)

# ──────────────────────────────────────────────
# DB-based exclusions
# ──────────────────────────────────────────────
class ExcludePlaylist(SQLModel, table=True):
    id: str = Field(primary_key=True)      # Spotify playlist ID
    reason: str | None = None

class ExcludeTrack(SQLModel, table=True):
    id: str = Field(primary_key=True)      # Spotify track ID
    reason: str | None = None

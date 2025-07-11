"""
Download tracks + metadata from every (non-auto) Spotify playlist
and save audio files to data/raw/.

Relies on:
    • oauthManager – to get a spotipy client with proper user scopes
    • spotdl        – to actually download the audio
"""


from __future__ import annotations
from pathlib import Path
import subprocess
import json
import shutil
from typing import Iterable, Dict, Any

import spotdl.utils.metadata
from oauthmanager.core import get_client

CACHE = Path.home() / ".cache" / "swara"
CACHE.mkdir(parents=True, exist_ok=True)
PROJECT_ROOT = Path(
    os.environ.get("PROJECT_ROOT") or Path(__file__).resolve().parents[2]
)
RAW_DIR = PROJECT_ROOT / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)





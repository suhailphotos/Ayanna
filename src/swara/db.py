# src/swara/db.py
import os, re
from pathlib import Path
from sqlmodel import create_engine, Session

def _expand_all(s: str, depth: int = 10) -> str:
    """Recursively expand $VARS / ${VARS} up to *depth* times."""
    for _ in range(depth):
        new = os.path.expandvars(s)
        if new == s:
            return new
        s = new
    raise RuntimeError("Environment variable expansion seems recursive")

raw_url = os.getenv("DATABASE_URL")
if raw_url:
    DATABASE_URL = _expand_all(raw_url)
else:
    project_root = Path(__file__).resolve().parents[2]
    DATABASE_URL = f"sqlite:///{project_root}/data/db/swara.db"

engine = create_engine(DATABASE_URL, echo=False)
def get_session(): return Session(engine)

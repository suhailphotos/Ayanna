# src/swara/db.py
import os
from pathlib import Path
from sqlmodel import create_engine, Session

# ----------------------------------------------------------------------------- #
# 1) Resolve project root *robustly*                                             #
# ----------------------------------------------------------------------------- #
PROJECT_ROOT = Path(
    os.getenv("PROJECT_ROOT", Path(__file__).resolve().parents[2])
).resolve()

DB_DIR  = PROJECT_ROOT / "data" / "db"
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_FILE = DB_DIR / "swara.db"

# If the caller hasn’t overridden with a DATABASE_URL env-var,
# fall back to this absolute SQLite URL:
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_FILE}")

engine = create_engine(DATABASE_URL, echo=False)

def get_session() -> Session:
    return Session(engine)

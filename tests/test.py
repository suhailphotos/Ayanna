import os
from pathlib import Path
from dotenv import load_dotenv
from sqlmodel import create_engine
from sqlalchemy import text

# Load .env (always override to avoid stale envs)
project_root = os.getenv("PROJECT_ROOT", ".")
load_dotenv(dotenv_path=Path(project_root) / ".env", override=True)

# Prefer explicit DATABASE_URL (Postgres), else use SQLite fallback
db_url = os.getenv("DATABASE_URL")
if not db_url or db_url.strip() == "":
    sqlite_path = os.getenv("SQLITE_FALLBACK")
    if not sqlite_path:
        # Final fallback to relative path if not set
        sqlite_path = str(Path(project_root) / "data/db/swara.db")
    db_url = f"sqlite:///{sqlite_path}"

engine = create_engine(db_url)

# Determine query based on backend
if db_url.startswith("sqlite"):
    query = "SELECT name FROM sqlite_master WHERE type='table'"
else:
    query = (
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema='public'"
    )

with engine.connect() as conn:
    res = conn.execute(text(query))
    print("Tables in DB:", [r[0] for r in res])

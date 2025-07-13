# scripts/manage_db.py
import os, sys, json
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import text, make_url
from sqlmodel import SQLModel, select

# ── 1. Load env vars early – nothing else touches them yet ──────────
load_dotenv(dotenv_path=Path(os.environ["PROJECT_ROOT"]) / ".env")

# ── 2. Import the DB helpers *after* the env is ready ───────────────
from swara.db import engine, get_session, DATABASE_URL      # ← already expanded
from swara.models import ExcludePlaylist, ExcludeTrack, Playlist, Track, Embedding

# ── 3. Ensure the SQLite folder exists (only matters for sqlite:///) ─
if DATABASE_URL.startswith("sqlite"):
    db_file = make_url(DATABASE_URL).database
    Path(db_file).parent.mkdir(parents=True, exist_ok=True)

# ─────────────────────────────────────────────────────────────────────
# Commands
# ─────────────────────────────────────────────────────────────────────
def create_db() -> None:
    SQLModel.metadata.create_all(engine)
    print("Database and tables created.")

def import_exclusions(json_path: str) -> None:
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    with get_session() as ses:
        for rec in data.get("playlists", []):
            ses.merge(ExcludePlaylist(id=rec["id"], reason="json-import"))
        ses.commit()
    print(f"Imported {len(data.get('playlists', []))} excluded playlists.")

def list_tables() -> None:
    with engine.connect() as c:
        rows = c.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
        print("Tables:", ", ".join(r[0] for r in rows))

TABLES = {
    "excludeplaylist": ExcludePlaylist,
    "excludetrack": ExcludeTrack,
    "playlist": Playlist,
    "track": Track,
    "embedding": Embedding,
}

def list_table_contents(table: str, filter_expr: str | None = None) -> None:
    model = TABLES.get(table.lower())
    if not model:
        print(f"Unknown table: {table}")
        print("Available:", ", ".join(TABLES))
        return

    stmt = select(model)

    # simple "field=value" filter
    if filter_expr and "=" in filter_expr:
        field, value = (s.strip() for s in filter_expr.split("=", 1))
        if hasattr(model, field):
            anno = model.__annotations__.get(field, str)
            if anno is bool:
                value = value.lower() in {"true", "1", "yes"}
            elif anno is int:
                value = int(value)
            elif anno is float:
                value = float(value)
            stmt = stmt.where(getattr(model, field) == value)
        else:
            print(f"Unknown field '{field}'")
            return

    with get_session() as ses:
        rows = ses.exec(stmt).all()

    if not rows:
        print("(no records)")
        return

    cols = list(rows[0].__fields__)
    print("\t".join(cols))
    for row in rows:
        print("\t".join(str(getattr(row, c)) for c in cols))

# ─────────────────────────────────────────────────────────────────────
def usage() -> None:
    print(
        "Usage: python manage_db.py <command> [args]\n\n"
        "Commands:\n"
        "  create                       Create database and tables\n"
        "  import_exclusions <path>     Import exclusions from JSON file\n"
        "  list_tables                  List all tables\n"
        "  list <table> [field=value]   List rows (optional filter)\n"
    )

if __name__ == "__main__":
    if len(sys.argv) < 2:
        usage()
        sys.exit(1)

    cmd, *args = sys.argv[1:]

    match cmd:
        case "create":
            create_db()
        case "import_exclusions" if len(args) == 1:
            import_exclusions(args[0])
        case "list_tables":
            list_tables()
        case "list" if args:
            list_table_contents(args[0], args[1] if len(args) > 1 else None)
        case _:
            usage()
            sys.exit(1)

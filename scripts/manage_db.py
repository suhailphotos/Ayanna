# scripts/manage_db.py
import os, sys, json
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import text, make_url
from sqlmodel import SQLModel, select

try:
    from tabulate import tabulate
except ImportError:
    tabulate = None  # Fallback to manual formatting if not installed

load_dotenv(dotenv_path=Path(os.environ["PROJECT_ROOT"]) / ".env")

from swara.db import engine, get_session, DATABASE_URL
from swara.models import ExcludePlaylist, ExcludeTrack, Playlist, Track, Embedding, User

if DATABASE_URL.startswith("sqlite"):
    db_file = make_url(DATABASE_URL).database
    Path(db_file).parent.mkdir(parents=True, exist_ok=True)

TABLES = {
    "excludeplaylist": ExcludePlaylist,
    "excludetrack": ExcludeTrack,
    "playlist": Playlist,
    "track": Track,
    "embedding": Embedding,
    "user": User,
}

def create_db():
    SQLModel.metadata.create_all(engine)
    print("Database and tables created.")

def import_exclusions(json_path):
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    with get_session() as ses:
        for rec in data.get("playlists", []):
            ses.merge(ExcludePlaylist(id=rec["id"], reason="json-import"))
        ses.commit()
    print(f"Imported {len(data.get('playlists', []))} excluded playlists.")

def ls(table=None, filter_expr=None, full=False, truncate_len=32):
    """List contents of one or all tables (pretty, truncating long text by default)."""
    if not table:
        print(f"Database: {DATABASE_URL}\n")
        for tname in TABLES:
            print(f"== {tname.upper()} ==")
            ls(tname, full=full, truncate_len=truncate_len)
            print()
        return

    model = TABLES.get(table.lower())
    if not model:
        print(f"Unknown table: {table}")
        print("Available:", ", ".join(TABLES))
        return

    stmt = select(model)
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

    def trunc(val):
        """Truncate long strings unless full output requested."""
        if full or not isinstance(val, str) or len(val) <= truncate_len:
            return val
        return val[:truncate_len - 1] + "…"

    data = [[trunc(getattr(row, c)) for c in cols] for row in rows]

    if tabulate:
        print(tabulate(data, headers=cols, tablefmt="github"))
    else:
        # Manual fallback: tab-separated, aligned
        widths = [max(len(str(val)) for val in [col] + [row[i] for row in data]) for i, col in enumerate(cols)]
        fmt = "  ".join(f"{{:<{w}}}" for w in widths)
        print(fmt.format(*cols))
        for row in data:
            print(fmt.format(*(str(v) for v in row)))

def schema_report():
    with engine.connect() as c:
        # List all user tables (not sqlite internal)
        tables = [
            row[0] for row in c.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            )
        ]
        if not tables:
            print("No tables found.")
            return

        print(f"\nDatabase: {DATABASE_URL}")
        for tname in tables:
            print(f"\n— {tname} —")
            cols = c.execute(text(f"PRAGMA table_info('{tname}')")).fetchall()
            print("Columns:")
            for col in cols:
                name, ctype, notnull, dflt, pk = col[1], col[2], col[3], col[4], col[5]
                print(f"  {name:<20} {ctype:<12} {'NOT NULL' if notnull else ''} {'PK' if pk else ''} default={dflt}")
            fks = c.execute(text(f"PRAGMA foreign_key_list('{tname}')")).fetchall()
            if fks:
                print("Foreign Keys:")
                for fk in fks:
                    print(f"  {fk[3]} → {fk[2]}.{fk[4]} (on_update={fk[5]}, on_delete={fk[6]})")
            rowcount = c.execute(text(f"SELECT COUNT(*) FROM '{tname}'")).scalar_one()
            print(f"Rows: {rowcount}")
        print()

def usage():
    print(
        "Usage: python manage_db.py <command> [args]\n\n"
        "Commands:\n"
        "  create                       Create database and tables\n"
        "  import_exclusions <path>     Import exclusions from JSON file\n"
        "  ls [<table>] [field=value]   List rows (optional filter). No args: all tables\n"
        "  schema_report                Print schema of all tables and row counts\n"
    )

if __name__ == "__main__":
    if len(sys.argv) < 2:
        usage()
        sys.exit(1)

    cmd, *args = sys.argv[1:]
    full = False

    # Allow "--full" or "full" as last argument
    if args and args[-1] in {"--full", "full"}:
        full = True
        args = args[:-1]

    match cmd:
        case "create":
            create_db()
        case "import_exclusions" if len(args) == 1:
            import_exclusions(args[0])
        case "ls":
            if not args:
                ls(full=full)
            elif len(args) == 1:
                ls(args[0], full=full)
            else:
                ls(args[0], args[1], full=full)
        case "schema_report":
            schema_report()
        case _:
            usage()
            sys.exit(1)

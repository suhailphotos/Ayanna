# src/swara/db_cli.py
import os, sys, json, shutil
import pydoc
from pathlib import Path
from wcwidth import wcswidth
from dotenv import load_dotenv
from sqlalchemy import text, make_url, delete
from sqlmodel import SQLModel, select

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
        for t in data.get("tracks", []):
            # If you want to save the reason, pull from the JSON; otherwise default
            track_id = t["id"] if isinstance(t, dict) else t
            reason = t.get("reason", "json-import") if isinstance(t, dict) else "json-import"
            ses.merge(ExcludeTrack(id=track_id, reason=reason))
        ses.commit()
        excluded_track_ids = [t["id"] if isinstance(t, dict) else t for t in data.get("tracks", [])]
        if excluded_track_ids:
            ses.exec(delete(Embedding).where(Embedding.track_id.in_(excluded_track_ids)))
            ses.exec(delete(Track).where(Track.id.in_(excluded_track_ids)))
            ses.commit()
        # Same for playlists if you want
        excluded_playlist_ids = [p["id"] for p in data.get("playlists", [])]
        if excluded_playlist_ids:
            ses.exec(delete(Playlist).where(Playlist.id.in_(excluded_playlist_ids)))
            ses.commit()
    print(f"Imported {len(data.get('playlists', []))} excluded playlists and {len(data.get('tracks', []))} excluded tracks.")

def ls(table=None, filter_expr=None, full=False, head=False, head_n=20, truncate_len=32):
    """List contents of one or all tables (pretty, paged by default)."""
    if not table:
        buf = []
        buf.append(f"Database: {DATABASE_URL}\n")
        for tname in TABLES:
            buf.append(f"== {tname.upper()} ==")
            buf.append(ls(tname, full=full, head=head, head_n=head_n, truncate_len=truncate_len))
            buf.append("")
        return "\n".join(buf)

    model = TABLES.get(table.lower())
    if not model:
        return f"Unknown table: {table}\nAvailable: {', '.join(TABLES)}"

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
            return f"Unknown field '{field}'"

    with get_session() as ses:
        rows = ses.exec(stmt).all()

    if not rows:
        return "(no records)"

    if head:
        rows = rows[:head_n]

    # Collect column names
    cols = list(type(rows[0]).model_fields.keys())

    def realwidth(s):
        return wcswidth(s) if s is not None else 0
    
    def pad_cell(val, width):
        v = str(val)
        vwidth = realwidth(v)
        return v + ' ' * (width - vwidth)

    # Prepare (truncated & trimmed) data for display
    def trunc(val):
        if full or not isinstance(val, str) or len(val) <= truncate_len:
            return val
        return val[:truncate_len - 1] + "…"
    
    def clean(val):
        # Truncate and strip whitespace for display
        s = str(trunc(val)) if val is not None else ""
        return s.strip()  # <-- trims both leading and trailing spaces
    
    data = [[clean(getattr(row, c)) for c in cols] for row in rows]
    
    # Calculate the width for each column (header or max data cell)
    col_widths = [max(realwidth(str(col)), max((realwidth(row[i]) for row in data), default=0)) for i, col in enumerate(cols)]
    
    def fmt_row(row):
        return " | ".join(pad_cell(val, col_widths[i]) for i, val in enumerate(row))
    
    lines = []
    lines.append(f"Table: {table.upper()} ({len(data)} rows)")
    lines.append(fmt_row(cols))  # header
    lines.append("-+-".join("-" * w for w in col_widths))  # separator
    for row in data:
        lines.append(fmt_row(row))
    if not full and not head:
        lines.append(f"\n(Tip: Use --head to see only first {head_n} rows, --full to show untruncated text.)")
    return "\n".join(lines)

from sqlalchemy import inspect

def schema_report():
    insp = inspect(engine)
    tables = insp.get_table_names()
    if not tables:
        print("No tables found.")
        return

    print(f"\nDatabase: {DATABASE_URL}")
    for tname in tables:
        print(f"\n— {tname} —")
        columns = insp.get_columns(tname)
        print("Columns:")
        for col in columns:
            name = col['name']
            ctype = str(col['type'])
            nullable = "NOT NULL" if not col['nullable'] else ""
            default = col.get('default', None)
            pk = "PK" if col.get('primary_key', False) else ""
            print(f"  {name:<20} {ctype:<20} {nullable:<8} {pk:<4} default={default}")

        fks = insp.get_foreign_keys(tname)
        if fks:
            print("Foreign Keys:")
            for fk in fks:
                cols = ', '.join(fk['constrained_columns'])
                referred_table = fk['referred_table']
                referred_cols = ', '.join(fk['referred_columns'])
                print(f"  {cols} → {referred_table}({referred_cols})")
        # Get row count (works on both sqlite/pg)
        with engine.connect() as c:
            rowcount = c.execute(text(f'SELECT COUNT(*) FROM "{tname}"')).scalar_one()
        print(f"Rows: {rowcount}")
    print()

# ---- CLI Handler ----

if __name__ == "__main__":
    if len(sys.argv) < 2:
        usage()
        sys.exit(1)

    cmd, *args = sys.argv[1:]

    # Flags
    full = False
    head = False
    head_n = 20
    # Remove flags from args for easier processing
    args_copy = []
    for arg in args:
        if arg in {"--full", "full"}:
            full = True
        elif arg.startswith("--head"):
            head = True
            if "=" in arg:
                try:
                    head_n = int(arg.split("=")[1])
                except ValueError:
                    pass
        elif arg == "head":
            head = True
        else:
            args_copy.append(arg)
    args = args_copy

    match cmd:
        case "create":
            create_db()
        case "import_exclusions" if len(args) == 1:
            import_exclusions(args[0])
        case "ls":
            if not args:
                result = ls(full=full, head=head, head_n=head_n)
            elif len(args) == 1:
                result = ls(args[0], full=full, head=head, head_n=head_n)
            else:
                result = ls(args[0], args[1], full=full, head=head, head_n=head_n)
            if result:
                if not head:
                    pydoc.pager(result)
                else:
                    print(result)
        case "schema_report":
            schema_report()
        case _:
            usage()
            sys.exit(1)

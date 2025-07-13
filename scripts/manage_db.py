import sys
import os
import json
from sqlmodel import SQLModel, select
from sqlalchemy import text
from swara.db import engine, get_session, DATABASE_URL
from swara.models import ExcludePlaylist

if DATABASE_URL.startswith("sqlite:///"):
    db_file = DATABASE_URL.replace("sqlite:///", "")
    db_dir = os.path.dirname(db_file)
    os.makedirs(db_dir, exist_ok=True)

def create_db():
    SQLModel.metadata.create_all(engine)
    print("Database and tables created.")

def import_exclusions(json_path):
    with open(json_path) as f:
        data = json.load(f)
    with get_session() as ses:
        for rec in data.get("playlists", []):
            ses.merge(ExcludePlaylist(id=rec["id"], reason="json-import"))
        ses.commit()
    print("Imported", len(data.get("playlists", [])), "excluded playlists.")

def list_tables():
    # This is SQLite-specific
    with engine.connect() as c:
        result = c.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
        tables = [r[0] for r in result]
    print("Tables:", ", ".join(tables))

def list_table_contents(table_name, filter_expr=None):
    from swara.models import ExcludePlaylist, ExcludeTrack, Playlist, Track, Embedding
    TABLES = {
        "excludeplaylist": ExcludePlaylist,
        "excludetrack": ExcludeTrack,
        "playlist": Playlist,
        "track": Track,
        "embedding": Embedding,
    }
    model = TABLES.get(table_name.lower())
    if not model:
        print(f"Unknown table: {table_name}")
        print(f"Available: {', '.join(TABLES.keys())}")
        return

    stmt = select(model)

    # Optional filter parsing: field=value
    if filter_expr:
        if "=" in filter_expr:
            field, value = filter_expr.split("=", 1)
            # Try to cast value type based on model type
            field = field.strip()
            value = value.strip()
            if hasattr(model, field):
                # Get python type from the model annotation
                field_type = model.__annotations__.get(field, str)
                try:
                    # e.g. convert "True"/"False" to bool, ints, etc.
                    if field_type is bool:
                        value = value.lower() in ("true", "1", "yes")
                    elif field_type is int:
                        value = int(value)
                    elif field_type is float:
                        value = float(value)
                    # else leave as str
                except Exception:
                    pass
                stmt = stmt.where(getattr(model, field) == value)
            else:
                print(f"Unknown field '{field}' for table '{table_name}'")
                return
        else:
            print("Invalid filter syntax: use field=value")
            return

    with get_session() as ses:
        rows = ses.exec(stmt).all()

    if not rows:
        print("(no records)")
        return

    colnames = [field for field in rows[0].__fields__.keys()]
    print("\t".join(colnames))
    for row in rows:
        print("\t".join(str(getattr(row, col)) for col in colnames))

def usage():
    print(f"""
Usage: python manage_db.py <command> [args...]

Commands:
  create                       Create database and tables
  import_exclusions <path>     Import exclusions from JSON file
  list_tables                  List all tables in the database
  list <table> [filter]        List all rows in <table> (optional filter: field=value)
""")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        usage()
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "create":
        create_db()
    elif cmd == "import_exclusions" and len(sys.argv) == 3:
        import_exclusions(sys.argv[2])
    elif cmd == "list_tables":
        list_tables()
    elif cmd == "list" and len(sys.argv) >= 3:
        filter_expr = sys.argv[3] if len(sys.argv) == 4 else None
        list_table_contents(sys.argv[2], filter_expr)
    else:
        usage()
        sys.exit(1)

from sqlmodel import create_engine
from sqlalchemy import text

engine = create_engine(os.getenv("DATABASE_URL"))
with engine.connect() as conn:
    res = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
    print("Tables in DB:", [r[0] for r in res])

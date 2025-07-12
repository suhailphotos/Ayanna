import os
from sqlmodel import create_engine, Session

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///swara.db")
engine = create_engine(DATABASE_URL, echo=False)

def get_session() -> Session:
    from contextlib import contextmanager
    @contextmanager
    def _session():
        with Session(engine) as s:
            yield s
    return _session()

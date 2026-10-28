"""Engine/session factory."""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .models import Base

_engines: dict[str, Engine] = {}


def get_engine(url: str) -> Engine:
    if url not in _engines:
        kwargs = {}
        if url.startswith("sqlite"):
            path = url.replace("sqlite:///", "")
            if path and path != ":memory:":
                Path(path).parent.mkdir(parents=True, exist_ok=True)
            kwargs["connect_args"] = {"check_same_thread": False, "timeout": 15}
        eng = create_engine(url, future=True, **kwargs)
        if url.startswith("sqlite"):
            @event.listens_for(eng, "connect")
            def _pragma(dbapi_conn, _):  # WAL lets API + executor share the file safely
                cur = dbapi_conn.cursor()
                cur.execute("PRAGMA journal_mode=WAL")
                cur.execute("PRAGMA busy_timeout=15000")
                cur.execute("PRAGMA foreign_keys=ON")
                cur.close()
        Base.metadata.create_all(eng)
        _engines[url] = eng
    return _engines[url]


def session_factory(url: str) -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(url), expire_on_commit=False, future=True)


@contextmanager
def session_scope(factory: sessionmaker[Session]) -> Iterator[Session]:
    s = factory()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()

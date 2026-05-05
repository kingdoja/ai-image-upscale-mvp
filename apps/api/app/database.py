from typing import Generator, Optional

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.pool import StaticPool

from .config import get_settings


Base = declarative_base()


def _engine_kwargs(database_url: str) -> dict:
    if database_url.startswith("sqlite"):
        kwargs = {"connect_args": {"check_same_thread": False}}
        if database_url in {"sqlite://", "sqlite:///:memory:"}:
            kwargs["poolclass"] = StaticPool
        return kwargs
    return {}


def create_db_engine(database_url: Optional[str] = None):
    url = database_url or get_settings().database_url
    return create_engine(url, future=True, **_engine_kwargs(url))


engine = create_db_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def init_db() -> None:
    import app.models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _ensure_sqlite_columns()


def _ensure_sqlite_columns() -> None:
    if engine.dialect.name != "sqlite":
        return
    inspector = inspect(engine)
    if "jobs" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("jobs")}
    if "selected_candidates" in columns:
        return
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE jobs ADD COLUMN selected_candidates TEXT NOT NULL DEFAULT '[]'"))


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

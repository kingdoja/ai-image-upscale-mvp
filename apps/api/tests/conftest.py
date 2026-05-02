from collections.abc import Generator
from io import BytesIO
from pathlib import Path
import os
import sys

import pytest
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture()
def sample_image_bytes() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (16, 10), color=(30, 120, 200)).save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture()
def temp_storage(tmp_path, monkeypatch) -> Path:
    root = tmp_path / "storage"
    monkeypatch.setenv("STORAGE_ROOT", str(root))
    return root


@pytest.fixture()
def db_session() -> Generator:
    from app.database import Base
    import app.models  # noqa: F401

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    Base.metadata.create_all(bind=engine)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    monkeypatch.setenv("STORAGE_ROOT", str(tmp_path / "storage"))
    monkeypatch.setenv("ENQUEUE_JOBS", "false")
    from app import config
    from app import database

    config.get_settings.cache_clear()
    database.engine = database.create_db_engine("sqlite://")
    database.SessionLocal.configure(bind=database.engine)

    from app.main import create_app
    from fastapi.testclient import TestClient

    app = create_app()
    return TestClient(app)

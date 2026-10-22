"""Database engine and session management for SQLModel / Relational inventory store."""

import os
from collections.abc import Generator
from pathlib import Path
from typing import Optional

from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy.engine import Engine

_engine: Optional[Engine] = None


def normalize_database_url(url: str) -> str:
    """Normalize PostgreSQL URL scheme for SQLAlchemy compatibility."""
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url


def get_default_sqlite_url() -> str:
    """Build a fallback local SQLite URL inside services/api/data/."""
    current_dir = Path(__file__).resolve().parent
    data_dir = current_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    sqlite_path = data_dir / "inventory.db"
    return f"sqlite:///{sqlite_path.as_posix()}"


def get_database_url() -> str:
    """Retrieve DATABASE_URL from environment or fallback to local SQLite."""
    raw_url = os.getenv("DATABASE_URL")
    if raw_url and raw_url.strip():
        return normalize_database_url(raw_url.strip())
    return get_default_sqlite_url()


def create_db_engine(db_url: Optional[str] = None) -> Engine:
    """Create a new SQLModel/SQLAlchemy engine for the given or resolved URL."""
    url = normalize_database_url(db_url) if db_url else get_database_url()
    connect_args = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    return create_engine(url, echo=False, connect_args=connect_args)


def get_engine() -> Engine:
    """Return the singleton Engine, initializing it on first use."""
    global _engine
    if _engine is None:
        _engine = create_db_engine()
    return _engine


def set_engine(engine: Optional[Engine]) -> None:
    """Set or override the singleton engine (primarily for testing)."""
    global _engine
    _engine = engine


def init_db(target_engine: Optional[Engine] = None) -> None:
    """Initialize database tables registered in SQLModel.metadata.
    
    Safe for local development. Does not affect TinyDB collections.
    """
    # Import inventory models dynamically to ensure registration in SQLModel.metadata
    try:
        import services.api.models  # noqa: F401
    except ImportError:
        pass

    engine_to_use = target_engine or get_engine()
    SQLModel.metadata.create_all(engine_to_use)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a per-request SQLModel Session."""
    engine = get_engine()
    with Session(engine) as session:
        yield session


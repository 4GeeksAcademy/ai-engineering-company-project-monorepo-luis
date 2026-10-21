"""Unit tests for the SQLModel database engine and session management."""

import os
from unittest.mock import patch

import pytest
from sqlmodel import Session
from sqlalchemy.engine import Engine

from services.api.database import (
    create_db_engine,
    get_database_url,
    get_db,
    get_default_sqlite_url,
    get_engine,
    init_db,
    normalize_database_url,
    set_engine,
)


def test_normalize_database_url():
    assert (
        normalize_database_url("postgres://user:pass@localhost:5432/test")
        == "postgresql://user:pass@localhost:5432/test"
    )
    assert (
        normalize_database_url("postgresql://user:pass@localhost:5432/test")
        == "postgresql://user:pass@localhost:5432/test"
    )
    assert normalize_database_url("sqlite:///data.db") == "sqlite:///data.db"


def test_get_database_url_from_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgres://test_user:pass@host.supabase.co:5432/postgres")
    resolved = get_database_url()
    assert resolved == "postgresql://test_user:pass@host.supabase.co:5432/postgres"


def test_get_database_url_fallback(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    resolved = get_database_url()
    assert resolved.startswith("sqlite:///")
    assert "inventory.db" in resolved


def test_create_db_engine_sqlite():
    engine = create_db_engine("sqlite:///:memory:")
    assert isinstance(engine, Engine)
    assert "sqlite" in str(engine.url)


def test_get_and_set_engine():
    custom_engine = create_db_engine("sqlite:///:memory:")
    original_engine = get_engine()
    try:
        set_engine(custom_engine)
        assert get_engine() is custom_engine
    finally:
        set_engine(original_engine)


def test_init_db_in_memory():
    test_engine = create_db_engine("sqlite:///:memory:")
    # Should run create_all cleanly without exceptions
    init_db(target_engine=test_engine)


def test_get_db_session_lifecycle():
    test_engine = create_db_engine("sqlite:///:memory:")
    original_engine = get_engine()
    try:
        set_engine(test_engine)
        session_gen = get_db()
        session = next(session_gen)
        assert isinstance(session, Session)
        assert session.is_active
        # Terminate generator cleanly
        with pytest.raises(StopIteration):
            next(session_gen)
    finally:
        set_engine(original_engine)

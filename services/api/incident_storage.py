"""TinyDB storage configuration for Nexova incident records."""

import os
from contextlib import contextmanager
from pathlib import Path
from threading import RLock
from typing import Iterator

from tinydb import TinyDB
from tinydb.table import Table

DATABASE_ENV_VAR = "NEXOVA_INCIDENTS_DB_PATH"
DEFAULT_DATABASE_PATH = Path(__file__).resolve().parent / "data" / "incidents.json"
_INCIDENTS_LOCK = RLock()


def get_incident_database_path() -> Path:
    """Return the configured database path or the local default."""
    configured_path = os.environ.get(DATABASE_ENV_VAR)
    if configured_path:
        return Path(configured_path).expanduser().resolve()
    return DEFAULT_DATABASE_PATH


@contextmanager
def open_incident_database() -> Iterator[TinyDB]:
    """Open the TinyDB database and close its handle after use."""
    with _INCIDENTS_LOCK:
        database_path = get_incident_database_path()
        database_path.parent.mkdir(parents=True, exist_ok=True)
        database = TinyDB(database_path, ensure_ascii=False)
        try:
            yield database
        finally:
            database.close()


@contextmanager
def open_incident_table() -> Iterator[Table]:
    """Open the incident table and close its TinyDB handle after use."""
    with open_incident_database() as database:
        yield database.table("incidents")

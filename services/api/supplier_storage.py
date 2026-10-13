"""TinyDB storage configuration for supplier records."""

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from tinydb import TinyDB
from tinydb.table import Table

DATABASE_ENV_VAR = "NEXOVA_SUPPLIERS_DB_PATH"
DEFAULT_DATABASE_PATH = Path(__file__).resolve().parent / "data" / "suppliers.json"


def get_supplier_database_path() -> Path:
    """Return the configured database path or the ignored local default."""
    configured_path = os.environ.get(DATABASE_ENV_VAR)
    if configured_path:
        return Path(configured_path).expanduser().resolve()
    return DEFAULT_DATABASE_PATH


@contextmanager
def open_supplier_table() -> Iterator[Table]:
    """Open the supplier table and close its TinyDB handle after use."""
    database_path = get_supplier_database_path()
    database_path.parent.mkdir(parents=True, exist_ok=True)
    database = TinyDB(database_path, ensure_ascii=False)
    try:
        yield database.table("suppliers")
    finally:
        database.close()
"""Single-process TinyDB operations committed through an atomic file replacement."""

import json
import os
import tempfile
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
from threading import RLock
from typing import Any, Iterator

from tinydb import TinyDB
from tinydb.storages import MemoryStorage

DATABASE_ENV_VAR = "NEXOVA_AUTH_DB_PATH"
DEFAULT_DATABASE_PATH = Path(__file__).resolve().parent / "data" / "auth.json"
_AUTH_LOCK = RLock()


def get_auth_database_path() -> Path:
    configured_path = os.environ.get(DATABASE_ENV_VAR)
    if configured_path:
        return Path(configured_path).expanduser().resolve()
    return DEFAULT_DATABASE_PATH


def _write_snapshot(database_path: Path, snapshot: dict[str, Any]) -> None:
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=database_path.parent,
            prefix=".auth-",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            json.dump(snapshot, temporary, ensure_ascii=False)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_path, database_path)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


@contextmanager
def open_auth_database() -> Iterator[TinyDB]:
    with _AUTH_LOCK:
        database_path = get_auth_database_path()
        database_path.parent.mkdir(parents=True, exist_ok=True)
        with TinyDB(database_path, ensure_ascii=False) as persisted:
            original = deepcopy(persisted.storage.read() or {})
        staged = TinyDB(storage=MemoryStorage)
        staged.storage.write(deepcopy(original))
        try:
            yield staged
            snapshot = staged.storage.read() or {}
            if snapshot != original:
                _write_snapshot(database_path, snapshot)
        finally:
            staged.close()
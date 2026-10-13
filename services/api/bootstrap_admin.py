"""Explicit offline promotion of an existing active user, without credentials."""

import argparse
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.api.auth_models import UserRole, UserUpdate
from services.api.auth_storage import DATABASE_ENV_VAR
from services.api.user_service import get_user_by_id, update_user


def _positive_id(value: str) -> int:
    try:
        user_id = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("user ID must be a positive integer") from None
    if user_id <= 0:
        raise argparse.ArgumentTypeError("user ID must be a positive integer")
    return user_id


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Promote an existing active user offline; stop the API first."
    )
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--user-id", type=_positive_id, required=True)
    parser.add_argument("--confirm", action="store_true", required=True)
    args = parser.parse_args(argv)
    database_path = args.database.expanduser().resolve()
    if not database_path.is_file():
        print("Admin promotion failed: an existing database is required", file=sys.stderr)
        return 1
    previous_path = os.environ.get(DATABASE_ENV_VAR)
    os.environ[DATABASE_ENV_VAR] = str(database_path)
    try:
        user = get_user_by_id(args.user_id)
        if not user.is_active:
            print("Admin promotion failed: user must be active", file=sys.stderr)
            return 1
        if user.role == UserRole.ADMIN:
            print("User is already an active admin")
            return 0
        update_user(user.id, UserUpdate(role=UserRole.ADMIN))
        print("User promoted to admin")
        return 0
    except (ValueError, OSError):
        print("Admin promotion failed: verify the database and user", file=sys.stderr)
        return 1
    finally:
        if previous_path is None:
            os.environ.pop(DATABASE_ENV_VAR, None)
        else:
            os.environ[DATABASE_ENV_VAR] = previous_path


if __name__ == "__main__":
    raise SystemExit(main())
from __future__ import annotations

from collections.abc import Generator

from astra.common.config import settings
from astra.storage.db import connect
from astra.storage.repo import Repo


def get_repo() -> Generator[Repo, None, None]:
    conn = connect(settings.db_path)
    try:
        yield Repo(conn)
    finally:
        conn.close()

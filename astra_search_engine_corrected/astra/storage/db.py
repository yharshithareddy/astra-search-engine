from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator
from uuid import uuid4

from astra.common.config import settings


SCHEMA_SQL = """
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;

CREATE TABLE IF NOT EXISTS documents (
  doc_id INTEGER PRIMARY KEY AUTOINCREMENT,
  url TEXT NOT NULL UNIQUE,
  title TEXT NOT NULL,
  body TEXT NOT NULL,
  length INTEGER NOT NULL,
  fetched_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS terms (
  term_id INTEGER PRIMARY KEY AUTOINCREMENT,
  term TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS postings (
  term_id INTEGER NOT NULL,
  doc_id INTEGER NOT NULL,
  tf_title INTEGER NOT NULL,
  tf_body INTEGER NOT NULL,
  PRIMARY KEY(term_id, doc_id),
  FOREIGN KEY(term_id) REFERENCES terms(term_id) ON DELETE CASCADE,
  FOREIGN KEY(doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS stats (
  avg_doc_len REAL NOT NULL,
  doc_count INTEGER NOT NULL,
  index_version INTEGER NOT NULL,
  created_at TEXT NOT NULL
);

-- auxiliary table for safe incremental indexing
CREATE TABLE IF NOT EXISTS indexed_docs (
  doc_id INTEGER PRIMARY KEY,
  index_version INTEGER NOT NULL,
  indexed_at TEXT NOT NULL,
  FOREIGN KEY(doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_postings_term ON postings(term_id);
CREATE INDEX IF NOT EXISTS idx_postings_doc ON postings(doc_id);
"""


def connect(db_path: str | None = None) -> sqlite3.Connection:
    path = Path(db_path or settings.db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_SQL)
    # ensure there is at least one stats row
    cur = conn.execute("SELECT COUNT(*) AS c FROM stats")
    if cur.fetchone()["c"] == 0:
        conn.execute(
            "INSERT INTO stats(avg_doc_len, doc_count, index_version, created_at) VALUES(?, ?, ?, datetime('now'))",
            (0.0, 0, 1),
        )
    conn.commit()


@contextmanager
def tx(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """Transaction helper that supports nesting.

    - If not already in a transaction: BEGIN / COMMIT / ROLLBACK
    - If already in a transaction: use a SAVEPOINT so nesting works safely
    """

    # Nested transaction -> use SAVEPOINT
    if conn.in_transaction:
        sp = f"sp_{uuid4().hex}"
        conn.execute(f"SAVEPOINT {sp}")
        try:
            yield conn
        except Exception:
            conn.execute(f"ROLLBACK TO {sp}")
            conn.execute(f"RELEASE {sp}")
            raise
        else:
            conn.execute(f"RELEASE {sp}")
        return

    # Top-level transaction
    conn.execute("BEGIN")
    try:
        yield conn
    except Exception:
        conn.rollback()
        raise
    else:
        conn.commit()

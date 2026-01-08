from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Iterable

from .db import init_db, tx


@dataclass(frozen=True)
class Document:
    doc_id: int
    url: str
    title: str
    body: str
    length: int
    fetched_at: str


class Repo:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        init_db(self.conn)

    # -------------------- documents --------------------
    def upsert_document(self, url: str, title: str, body: str, fetched_at: str) -> int:
        length = len(body.split())
        with tx(self.conn):
            self.conn.execute(
                """
                INSERT INTO documents(url, title, body, length, fetched_at)
                VALUES(?, ?, ?, ?, ?)
                ON CONFLICT(url) DO UPDATE SET
                  title=excluded.title,
                  body=excluded.body,
                  length=excluded.length,
                  fetched_at=excluded.fetched_at
                """,
                (url, title, body, length, fetched_at),
            )
            cur = self.conn.execute("SELECT doc_id FROM documents WHERE url=?", (url,))
            return int(cur.fetchone()["doc_id"])

    def iter_unindexed_documents(self, limit: int | None = None) -> Iterable[Document]:
        sql = """
        SELECT d.*
        FROM documents d
        LEFT JOIN indexed_docs i ON i.doc_id = d.doc_id
        WHERE i.doc_id IS NULL
        ORDER BY d.doc_id ASC
        """
        if limit:
            sql += " LIMIT ?"
            rows = self.conn.execute(sql, (limit,)).fetchall()
        else:
            rows = self.conn.execute(sql).fetchall()
        for r in rows:
            yield Document(**dict(r))

    def get_document(self, doc_id: int) -> Document | None:
        row = self.conn.execute("SELECT * FROM documents WHERE doc_id=?", (doc_id,)).fetchone()
        return Document(**dict(row)) if row else None

    def fetch_documents_by_ids(self, doc_ids: list[int]) -> list[Document]:
        if not doc_ids:
            return []
        q = ",".join("?" for _ in doc_ids)
        rows = self.conn.execute(f"SELECT * FROM documents WHERE doc_id IN ({q})", doc_ids).fetchall()
        docs = [Document(**dict(r)) for r in rows]
        # stable ordering same as input
        by_id = {d.doc_id: d for d in docs}
        return [by_id[i] for i in doc_ids if i in by_id]

    # -------------------- terms/postings --------------------
    def ensure_term_id(self, term: str) -> int:
        row = self.conn.execute("SELECT term_id FROM terms WHERE term=?", (term,)).fetchone()
        if row:
            return int(row["term_id"])
        with tx(self.conn):
            self.conn.execute("INSERT OR IGNORE INTO terms(term) VALUES(?)", (term,))
        row2 = self.conn.execute("SELECT term_id FROM terms WHERE term=?", (term,)).fetchone()
        return int(row2["term_id"])

    def upsert_posting(self, term_id: int, doc_id: int, tf_title: int, tf_body: int) -> None:
        self.conn.execute(
            """
            INSERT INTO postings(term_id, doc_id, tf_title, tf_body)
            VALUES(?, ?, ?, ?)
            ON CONFLICT(term_id, doc_id) DO UPDATE SET
              tf_title=excluded.tf_title,
              tf_body=excluded.tf_body
            """,
            (term_id, doc_id, tf_title, tf_body),
        )

    def get_postings_for_term_ids(self, term_ids: list[int]) -> dict[int, list[sqlite3.Row]]:
        if not term_ids:
            return {}
        q = ",".join("?" for _ in term_ids)
        rows = self.conn.execute(
            f"""
            SELECT p.term_id, p.doc_id, p.tf_title, p.tf_body, d.length
            FROM postings p
            JOIN documents d ON d.doc_id = p.doc_id
            WHERE p.term_id IN ({q})
            """,
            term_ids,
        ).fetchall()
        out: dict[int, list[sqlite3.Row]] = {}
        for r in rows:
            out.setdefault(int(r["term_id"]), []).append(r)
        return out

    def df_for_term_id(self, term_id: int) -> int:
        row = self.conn.execute("SELECT COUNT(*) AS c FROM postings WHERE term_id=?", (term_id,)).fetchone()
        return int(row["c"])

    def mark_indexed(self, doc_id: int, index_version: int) -> None:
        self.conn.execute(
            """
            INSERT OR REPLACE INTO indexed_docs(doc_id, index_version, indexed_at)
            VALUES(?, ?, datetime('now'))
            """,
            (doc_id, index_version),
        )

    # -------------------- stats --------------------
    def get_stats(self) -> sqlite3.Row:
        return self.conn.execute("SELECT * FROM stats ORDER BY created_at DESC LIMIT 1").fetchone()

    def bump_stats(self) -> None:
        # Recompute avg_doc_len and doc_count; increment index_version
        row = self.conn.execute("SELECT COUNT(*) AS c, AVG(length) AS a FROM documents").fetchone()
        doc_count = int(row["c"] or 0)
        avg_len = float(row["a"] or 0.0)
        cur = self.conn.execute("SELECT index_version FROM stats ORDER BY created_at DESC LIMIT 1").fetchone()
        next_ver = int(cur["index_version"]) + 1 if cur else 1
        self.conn.execute(
            "INSERT INTO stats(avg_doc_len, doc_count, index_version, created_at) VALUES(?, ?, ?, datetime('now'))",
            (avg_len, doc_count, next_ver),
        )

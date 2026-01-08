from __future__ import annotations

import logging

from astra.common.tokenizer import count_terms, tokenize
from astra.storage.db import tx
from astra.storage.repo import Repo

log = logging.getLogger(__name__)


class Indexer:
    def __init__(self, repo: Repo):
        self.repo = repo

    def index_new_documents(self, batch_size: int = 100) -> int:
        stats = self.repo.get_stats()
        index_version = int(stats["index_version"])

        indexed = 0
        for doc in self.repo.iter_unindexed_documents(limit=batch_size):
            title_tokens = tokenize(doc.title)
            body_tokens = tokenize(doc.body)

            tf_title = count_terms(title_tokens)
            tf_body = count_terms(body_tokens)

            with tx(self.repo.conn):
                for term in set(tf_title) | set(tf_body):
                    term_id = self.repo.ensure_term_id(term)
                    self.repo.upsert_posting(
                        term_id=term_id,
                        doc_id=doc.doc_id,
                        tf_title=tf_title.get(term, 0),
                        tf_body=tf_body.get(term, 0),
                    )
                self.repo.mark_indexed(doc.doc_id, index_version)

            indexed += 1
            log.info("indexed_doc", extra={"doc_id": doc.doc_id, "url": doc.url})

        if indexed > 0:
            with tx(self.repo.conn):
                self.repo.bump_stats()

        return indexed

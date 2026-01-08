from __future__ import annotations

import math
from dataclasses import dataclass

from astra.common.config import settings
from astra.common.tokenizer import Query
from astra.storage.repo import Repo


@dataclass(frozen=True)
class ScoredDoc:
    doc_id: int
    score: float


class BM25Ranker:
    def __init__(self, repo: Repo):
        self.repo = repo

    def search(self, query: Query, k: int) -> list[ScoredDoc]:
        stats = self.repo.get_stats()
        N = max(int(stats["doc_count"]), 1)
        avgdl = float(stats["avg_doc_len"] or 0.0) or 1.0

        # resolve term -> term_id
        term_ids: dict[str, int] = {}
        for t in query.terms:
            row = self.repo.conn.execute("SELECT term_id FROM terms WHERE term=?", (t,)).fetchone()
            if row:
                term_ids[t] = int(row["term_id"])

        postings_by_tid = self.repo.get_postings_for_term_ids(list(term_ids.values()))

        scores: dict[int, float] = {}

        for term, tid in term_ids.items():
            postings = postings_by_tid.get(tid, [])
            df = len(postings)
            if df == 0:
                continue

            # BM25 IDF variant with +1 to avoid negatives on very common terms
            idf = math.log(1.0 + (N - df + 0.5) / (df + 0.5))

            for r in postings:
                doc_id = int(r["doc_id"])
                dl = float(r["length"] or 0.0) or 1.0

                tf_title = int(r["tf_title"])
                tf_body = int(r["tf_body"])
                tf = tf_body + settings.title_boost * tf_title

                denom = tf + settings.k1 * (1.0 - settings.b + settings.b * (dl / avgdl))
                score = idf * ((tf * (settings.k1 + 1.0)) / denom)

                scores[doc_id] = scores.get(doc_id, 0.0) + float(score)

        # Phrase filtering is handled outside (requires doc content).
        top = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:k]
        return [ScoredDoc(doc_id=doc_id, score=score) for doc_id, score in top]

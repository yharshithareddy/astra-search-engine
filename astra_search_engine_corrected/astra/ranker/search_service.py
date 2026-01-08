from __future__ import annotations

from dataclasses import dataclass

from astra.common.tokenizer import Query
from astra.ranker.bm25 import BM25Ranker, ScoredDoc
from astra.storage.repo import Repo


@dataclass(frozen=True)
class SearchHit:
    doc_id: int
    url: str
    title: str
    snippet: str
    score: float


class SearchService:
    def __init__(self, repo: Repo):
        self.repo = repo
        self.ranker = BM25Ranker(repo)

    def search(self, query: Query, k: int, page: int, page_size: int) -> tuple[list[SearchHit], int]:
        # Retrieve more than we need so phrase filtering doesn't underflow
        pre_k = max(k, (page * page_size) + page_size) * 5
        scored = self.ranker.search(query, k=pre_k)

        doc_ids = [s.doc_id for s in scored]
        docs = {d.doc_id: d for d in self.repo.fetch_documents_by_ids(doc_ids)}

        filtered: list[ScoredDoc] = []
        for s in scored:
            d = docs.get(s.doc_id)
            if not d:
                continue
            if self._phrases_match(query, d.title, d.body):
                filtered.append(s)

        total = len(filtered)

        start = max(0, (page - 1) * page_size)
        end = start + page_size
        page_scored = filtered[start:end]

        hits: list[SearchHit] = []
        for s in page_scored:
            d = docs[s.doc_id]
            hits.append(
                SearchHit(
                    doc_id=d.doc_id,
                    url=d.url,
                    title=d.title,
                    snippet=self._make_snippet(query, d.body),
                    score=s.score,
                )
            )
        return hits, total

    def _phrases_match(self, query: Query, title: str, body: str) -> bool:
        if not query.phrases:
            return True
        hay_title = title.lower()
        hay_body = body.lower()
        for p in query.phrases:
            needle = p.lower()
            if needle not in hay_title and needle not in hay_body:
                return False
        return True

    def _make_snippet(self, query: Query, body: str, max_len: int = 220) -> str:
        text = body.strip().replace("\n", " ")
        if not query.terms:
            return text[:max_len] + ("…" if len(text) > max_len else "")
        t = query.terms[0].lower()
        idx = text.lower().find(t)
        if idx == -1:
            return text[:max_len] + ("…" if len(text) > max_len else "")
        start = max(0, idx - 60)
        end = min(len(text), idx + max_len)
        snippet = text[start:end].strip()
        if start > 0:
            snippet = "…" + snippet
        if end < len(text):
            snippet = snippet + "…"
        return snippet

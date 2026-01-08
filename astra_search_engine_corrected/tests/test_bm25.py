import tempfile

from astra.common.tokenizer import parse_query
from astra.indexer.indexer import Indexer
from astra.ranker.bm25 import BM25Ranker
from astra.storage.db import connect
from astra.storage.repo import Repo


def test_bm25_ranks_relevant_doc_higher():
    with tempfile.TemporaryDirectory() as td:
        db = f"{td}/test.db"
        conn = connect(db)
        repo = Repo(conn)

        repo.upsert_document("http://x/a", "FastAPI tutorial", "FastAPI is great for APIs", "2025-01-01T00:00:00Z")
        repo.upsert_document("http://x/b", "Cooking pasta", "Boil water and add pasta", "2025-01-01T00:00:00Z")

        idx = Indexer(repo)
        idx.index_new_documents(batch_size=10)

        ranker = BM25Ranker(repo)
        scored = ranker.search(parse_query("fastapi api"), k=5)

        assert scored[0].doc_id in {1, 2}
        # ensure the FastAPI document is first
        assert scored[0].doc_id == 1
        conn.close()

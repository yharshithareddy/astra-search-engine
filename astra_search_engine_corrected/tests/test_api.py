import tempfile

from fastapi.testclient import TestClient

from astra.api.main import create_app
from astra.common.config import settings
from astra.indexer.indexer import Indexer
from astra.storage.db import connect
from astra.storage.repo import Repo


def test_search_endpoint():
    with tempfile.TemporaryDirectory() as td:
        settings.db_path = f"{td}/api.db"  # override for test

        conn = connect(settings.db_path)
        repo = Repo(conn)
        repo.upsert_document("http://x/a", "Hello World", "This is a hello world document", "2025-01-01T00:00:00Z")
        repo.upsert_document("http://x/b", "Other", "Completely unrelated text", "2025-01-01T00:00:00Z")
        Indexer(repo).index_new_documents(batch_size=10)
        conn.close()

        client = TestClient(create_app())
        r = client.get("/search", params={"q": "hello world", "k": 10, "page": 1, "page_size": 10})
        assert r.status_code == 200
        data = r.json()
        assert data["total_hits"] >= 1
        assert data["hits"][0]["url"] == "http://x/a"

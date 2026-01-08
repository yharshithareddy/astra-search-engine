from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import typer
import uvicorn

from astra.api.main import create_app
from astra.common.config import settings
from astra.common.logging import setup_logging
from astra.crawler.crawler import PoliteCrawler
from astra.indexer.indexer import Indexer
from astra.storage.db import connect
from astra.storage.repo import Repo

app = typer.Typer(add_completion=False, help="Astra mini search engine CLI")


@app.command()
def crawl(
    seeds: Path = typer.Option(..., help="Path to a seeds.txt file (one URL per line)"),
    allowed_domains: str = typer.Option(..., "--allowed-domains", help="Comma-separated domain allowlist"),
    max_pages: int = typer.Option(200, help="Max pages to fetch"),
    max_depth: int = typer.Option(3, help="Max BFS depth from seeds"),
) -> None:
    """Crawl documents and persist into SQLite."""
    setup_logging()
    log = logging.getLogger("astra.cli")

    domains = {d.strip() for d in allowed_domains.split(",") if d.strip()}
    seed_urls = [ln.strip() for ln in seeds.read_text(encoding="utf-8").splitlines() if ln.strip()]

    conn = connect(settings.db_path)
    repo = Repo(conn)
    crawler = PoliteCrawler(repo=repo, allowed_domains=domains, max_pages=max_pages, max_depth=max_depth)
    try:
        results = crawler.crawl(seed_urls)
        stored = sum(1 for r in results if r.status == "stored")
        skipped = sum(1 for r in results if r.status == "skipped")
        errors = sum(1 for r in results if r.status == "error")
        log.info("crawl_done", extra={"stored": stored, "skipped": skipped, "errors": errors})
    finally:
        crawler.close()
        conn.close()


@app.command()
def index(batch_size: int = typer.Option(200, help="Number of unindexed documents to index per run")) -> None:
    """Index newly crawled documents into the SQLite inverted index."""
    setup_logging()
    log = logging.getLogger("astra.cli")

    conn = connect(settings.db_path)
    try:
        repo = Repo(conn)
        indexer = Indexer(repo)
        n = indexer.index_new_documents(batch_size=batch_size)
        log.info("index_done", extra={"indexed_docs": n})
    finally:
        conn.close()


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", help="Host to bind"),
    port: int = typer.Option(8000, help="Port to bind"),
    log_level: str = typer.Option("info", help="Uvicorn log level"),
) -> None:
    """Run the FastAPI service."""
    setup_logging()
    uvicorn.run(create_app(), host=host, port=port, log_level=log_level)


def main() -> None:
    app()


if __name__ == "__main__":
    main()

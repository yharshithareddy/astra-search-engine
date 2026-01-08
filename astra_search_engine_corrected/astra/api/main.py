from __future__ import annotations

import logging

from fastapi import Depends, FastAPI, Query
from fastapi.responses import JSONResponse

from astra.api.deps import get_repo
from astra.api.middleware import request_logging_middleware
from astra.api.schemas import HealthResponse, SearchResponse
from astra.common.tokenizer import parse_query
from astra.ranker.search_service import SearchService
from astra.storage.repo import Repo

log = logging.getLogger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(title="Astra Search", version="1.0.0")

    app.middleware("http")(request_logging_middleware)

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(status="ok")

    @app.get("/search", response_model=SearchResponse)
    def search(
        q: str = Query(..., min_length=1),
        k: int = Query(10, ge=1, le=1000),
        page: int = Query(1, ge=1),
        page_size: int = Query(10, ge=1, le=100),
        repo: Repo = Depends(get_repo),
    ) -> SearchResponse:
        query = parse_query(q)
        svc = SearchService(repo)

        hits, total = svc.search(query=query, k=k, page=page, page_size=page_size)
        return SearchResponse(
            query=q,
            k=k,
            page=page,
            page_size=page_size,
            total_hits=total,
            hits=[h.__dict__ for h in hits],
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_, exc: Exception):
        log.exception("unhandled_exception", exc_info=exc)
        return JSONResponse(status_code=500, content={"error": "internal_server_error"})

    return app

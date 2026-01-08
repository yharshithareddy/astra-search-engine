from __future__ import annotations

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"


class SearchHit(BaseModel):
    doc_id: int
    url: str
    title: str
    snippet: str
    score: float


class SearchResponse(BaseModel):
    query: str
    k: int = Field(ge=1, le=1000)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    total_hits: int
    hits: list[SearchHit]

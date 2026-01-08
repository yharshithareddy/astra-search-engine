from __future__ import annotations

import logging
import time
import uuid
from typing import Callable

from fastapi import Request, Response

log = logging.getLogger("astra.api")


async def request_logging_middleware(request: Request, call_next: Callable) -> Response:
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    start = time.perf_counter()
    try:
        response = await call_next(request)
        return response
    finally:
        latency_ms = (time.perf_counter() - start) * 1000.0
        record = logging.LogRecord(
            name="astra.api",
            level=logging.INFO,
            pathname=__file__,
            lineno=0,
            msg="request",
            args=(),
            exc_info=None,
        )
        record.request_id = request_id
        record.path = str(request.url.path)
        record.method = request.method
        record.status_code = getattr(locals().get("response", None), "status_code", 500)
        record.latency_ms = round(latency_ms, 2)
        log.handle(record)

from __future__ import annotations

import re
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse


_TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "gclid",
    "fbclid",
}


def normalize_url(base_url: str, href: str) -> str | None:
    try:
        abs_url = urljoin(base_url, href)
        parsed = urlparse(abs_url)

        if parsed.scheme not in {"http", "https"}:
            return None

        netloc = parsed.netloc.lower()
        netloc = re.sub(r":(80|443)$", "", netloc)

        path = re.sub(r"/{2,}", "/", parsed.path or "/")

        # drop fragments
        fragment = ""

        # remove common tracking params
        query_items = [(k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True) if k not in _TRACKING_PARAMS]
        query = urlencode(query_items, doseq=True)

        normalized = urlunparse((parsed.scheme, netloc, path, "", query, fragment))
        return normalized
    except Exception:
        return None

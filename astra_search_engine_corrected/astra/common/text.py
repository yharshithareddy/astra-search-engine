from __future__ import annotations

import re

from bs4 import BeautifulSoup

_WHITESPACE_RE = re.compile(r"\s+")
_SCRIPT_STYLE = {"script", "style", "noscript"}


def html_to_text(html: str) -> tuple[str, str]:
    """Extract (title, body_text) from HTML."""
    soup = BeautifulSoup(html, "lxml")

    for tag in soup.find_all(list(_SCRIPT_STYLE)):
        tag.decompose()

    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()

    # Prefer main content-ish tags when available; else fallback to body
    main = soup.find("main") or soup.find("article") or soup.body or soup
    text = main.get_text(separator=" ", strip=True)
    text = _WHITESPACE_RE.sub(" ", text).strip()

    return title, text

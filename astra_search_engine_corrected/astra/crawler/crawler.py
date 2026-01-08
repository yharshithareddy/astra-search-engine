from __future__ import annotations

import logging
import re
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx

from astra.common.config import settings
from astra.common.text import html_to_text
from astra.common.url import normalize_url
from astra.storage.repo import Repo

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class CrawlResult:
    url: str
    stored_doc_id: int | None
    status: str
    error: str | None = None


class PoliteCrawler:
    def __init__(
        self,
        repo: Repo,
        allowed_domains: set[str],
        max_pages: int = 200,
        max_depth: int = 3,
    ) -> None:
        self.repo = repo
        self.allowed_domains = {d.lower() for d in allowed_domains}
        self.max_pages = max_pages
        self.max_depth = max_depth
        self._last_fetch_by_host: dict[str, float] = defaultdict(lambda: 0.0)
        self._robots: dict[str, RobotFileParser] = {}

        self._client = httpx.Client(
            headers={"User-Agent": settings.user_agent},
            timeout=httpx.Timeout(settings.http_timeout_seconds),
            follow_redirects=True,
        )

    def close(self) -> None:
        self._client.close()

    def _host_allowed(self, url: str) -> bool:
        host = (urlparse(url).hostname or "").lower()
        return any(host == d or host.endswith("." + d) for d in self.allowed_domains)

    def _get_robot(self, url: str) -> RobotFileParser:
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        if base in self._robots:
            return self._robots[base]
        rp = RobotFileParser()
        rp.set_url(f"{base}/robots.txt")
        try:
            rp.read()
        except Exception:
            # if robots is unreachable, default to allow
            rp = RobotFileParser()
            rp.parse([])
        self._robots[base] = rp
        return rp

    def _polite_wait(self, url: str) -> None:
        host = (urlparse(url).hostname or "").lower()
        elapsed = time.time() - self._last_fetch_by_host[host]
        delay = max(0.0, settings.crawl_delay_seconds - elapsed)
        if delay > 0:
            time.sleep(delay)

    def crawl(self, seeds: Iterable[str]) -> list[CrawlResult]:
        seen: set[str] = set()
        q: deque[tuple[str, int]] = deque()

        for s in seeds:
            u = normalize_url(s.strip(), "")
            if not u:
                continue
            if not self._host_allowed(u):
                continue
            if u not in seen:
                seen.add(u)
                q.append((u, 0))

        results: list[CrawlResult] = []
        pages = 0

        while q and pages < self.max_pages:
            url, depth = q.popleft()
            if depth > self.max_depth:
                continue

            if not self._host_allowed(url):
                continue

            rp = self._get_robot(url)
            if not rp.can_fetch(settings.user_agent, url):
                results.append(CrawlResult(url=url, stored_doc_id=None, status="skipped", error="robots"))
                continue

            try:
                self._polite_wait(url)
                self._last_fetch_by_host[(urlparse(url).hostname or "").lower()] = time.time()

                resp = self._client.get(url)
                pages += 1

                if resp.status_code >= 400:
                    results.append(
                        CrawlResult(url=url, stored_doc_id=None, status="error", error=f"http_{resp.status_code}")
                    )
                    continue

                ctype = resp.headers.get("content-type", "")
                if "text/html" not in ctype:
                    results.append(CrawlResult(url=url, stored_doc_id=None, status="skipped", error="non_html"))
                    continue

                content = resp.content[: settings.max_response_bytes].decode(resp.encoding or "utf-8", errors="ignore")
                title, body = html_to_text(content)
                if not body:
                    results.append(CrawlResult(url=url, stored_doc_id=None, status="skipped", error="empty_body"))
                    continue

                doc_id = self.repo.upsert_document(
                    url=url,
                    title=title or url,
                    body=body,
                    fetched_at=datetime.now(timezone.utc).isoformat(),
                )
                results.append(CrawlResult(url=url, stored_doc_id=doc_id, status="stored"))
                log.info("crawled", extra={"url": url, "doc_id": doc_id})

                # extract outgoing links
                if depth < self.max_depth:
                    links = self._extract_links(url, content)
                    for link in links:
                        if link not in seen and self._host_allowed(link):
                            seen.add(link)
                            q.append((link, depth + 1))

            except Exception as e:
                results.append(CrawlResult(url=url, stored_doc_id=None, status="error", error=str(e)))

        return results

    def _extract_links(self, base_url: str, html: str) -> list[str]:
        # lightweight link extraction (no need for full soup)
        # find href="..."
        hrefs = []
        for m in re.finditer(r'href=[\\"\']([^\\"\']+)[\\"\']', html, flags=re.IGNORECASE):
            hrefs.append(m.group(1))
        out = []
        for h in hrefs:
            u = normalize_url(base_url, h)
            if u:
                out.append(u)
        return out

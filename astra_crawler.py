import os
import time
from collections import deque
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


DATA_DIR = "data"


def safe_filename(url: str) -> str:
    return url.replace("https://", "").replace("http://", "").replace("/", "_")


def save_page(url: str, title: str, text: str):
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

    name = safe_filename(url)
    path = os.path.join(DATA_DIR, name + ".txt")

    with open(path, "w", encoding="utf-8") as f:
        f.write(f"URL: {url}\n")
        f.write(f"TITLE: {title}\n\n")
        f.write(text)

    print(f"[astra] Saved: {path}")


def crawl(start_url: str, max_pages: int = 5, delay: float = 0.5):
    queue = deque([start_url])
    visited = set()
    count = 0

    print(f"[astra] Starting crawl at: {start_url}")

    while queue and count < max_pages:
        url = queue.popleft()

        if url in visited:
            continue
        visited.add(url)

        try:
            print(f"[astra] GET {url}")
            resp = requests.get(url, timeout=10)

            if resp.status_code != 200:
                print(f"[astra] Skipping (status {resp.status_code})")
                continue

            if "text/html" not in resp.headers.get("Content-Type", ""):
                print("[astra] Skipping non-HTML")
                continue

            soup = BeautifulSoup(resp.text, "html.parser")

            for tag in soup(["script", "style", "noscript"]):
                tag.extract()

            text = soup.get_text(separator=" ", strip=True)
            title = soup.title.string.strip() if soup.title else "No Title"

            save_page(url, title, text)

            count += 1

            for a in soup.find_all("a", href=True):
                href = urljoin(url, a["href"])
                if href.startswith(start_url) and href not in visited:
                    queue.append(href)

            time.sleep(delay)

        except Exception as e:
            print(f"[astra] Error fetching {url}: {e}")

    print(f"[astra] Finished. Pages saved: {count}")


def main():
    START_URLS = [
        "https://example.com",
        "https://wikipedia.org",
        "https://docs.python.org",
        "https://www.geeksforgeeks.org",
        "https://www.britannica.com"
    ]

    for url in START_URLS:
        crawl(url, max_pages=3)



if __name__ == "__main__":
    main()

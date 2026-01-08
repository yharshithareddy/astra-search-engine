# Astra — production-style mini web search engine (FastAPI + SQLite + BM25)

Astra is an end-to-end mini search platform that **crawls → indexes → serves** results via an HTTP API.
It’s intentionally designed to look like a real backend system you’d ship and operate.

## Features

- **Crawler**
  - Domain-restricted, polite crawling (`robots.txt`, per-host rate limiting)
  - URL normalization & deduplication
  - Timeouts, retries, and robust error handling
  - HTML → clean text extraction
  - Stores documents persistently in SQLite

- **Indexer**
  - Tokenization + stopwords (configurable)
  - Persistent **inverted index** in SQLite
  - Stores term frequencies for title & body
  - Incremental indexing (only newly crawled docs)

- **Ranker**
  - **BM25** scoring with title boosting
  - Phrase query support (quoted phrases)
  - Pagination

- **API**
  - `GET /health`
  - `GET /search?q=...&k=10&page=1&page_size=10`
  - Request latency metrics in logs

- **CLI (Typer)**
  - `astra crawl --seeds seeds.txt --allowed-domains example.com`
  - `astra index`
  - `astra serve`

- **Reliability**
  - Structured logging (JSON)
  - Centralized config (env vars)
  - Defensive DB operations / transactions

- **Quality**
  - Tests for tokenizer, BM25 ranking, API endpoint
  - GitHub Actions CI: lint, tests, Docker build
  - Dockerized API service

---

## Quickstart (local)

### 1) Install deps
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2) Crawl
Create a `seeds.txt` (one URL per line). Example:
```txt
https://example.com
```

Run:
```bash
python -m astra.cli crawl --seeds seeds.txt --allowed-domains example.com --max-pages 50
```

### 3) Index
```bash
python -m astra.cli index
```

### 4) Serve the API
```bash
python -m astra.cli serve --host 0.0.0.0 --port 8000
```

### 5) Search
```bash
curl "http://localhost:8000/search?q=example&k=10&page=1&page_size=10"
```

---

## Docker

### Build
```bash
docker build -t astra-search .
```

### Run
The DB is persisted to `/data/astra.db` inside the container. Mount a volume for persistence:
```bash
docker run --rm -p 8000:8000 -v "$(pwd)/data:/data" astra-search
```

---

## Configuration

Astra uses environment variables (see `astra/common/config.py`).

Common:
- `ASTRA_DB_PATH` (default: `./data/astra.db`)
- `ASTRA_USER_AGENT` (default: `AstraSearchBot/1.0`)
- `ASTRA_CRAWL_DELAY_SECONDS` (default: `1.0`)
- `ASTRA_HTTP_TIMEOUT_SECONDS` (default: `10.0`)
- `ASTRA_TITLE_BOOST` (default: `2.0`)
- `ASTRA_K1` (default: `1.2`)
- `ASTRA_B` (default: `0.75`)

---

## Storage schema (required)

Astra implements the required schema:

- `documents(doc_id, url, title, body, length, fetched_at)`
- `terms(term_id, term)`
- `postings(term_id, doc_id, tf_title, tf_body)`
- `stats(avg_doc_len, doc_count, index_version, created_at)`

Additionally, an `indexed_docs` table is used to support incremental indexing safely.

---

## Project structure

```
astra/
  crawler/
  indexer/
  ranker/
  storage/
  api/
  common/
  cli.py
tests/
.github/workflows/ci.yml
Dockerfile
requirements.txt
README.md
```

---

## Notes

- Phrase queries: use quotes, e.g. `q="machine learning" search`.
  Astra enforces phrase matches by filtering candidate docs for the substring in title/body.
- SQLite is used for both storage & inverted index to keep deployment simple.

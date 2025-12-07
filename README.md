# astra-search-engine

# Astra — Mini Search Engine

Astra is a mini search engine built from scratch using Python. It implements the core ideas behind a real-world search system including crawling, indexing, TF-IDF ranking, caching, and a web interface.

This project demonstrates backend engineering, algorithmic thinking, and system design fundamentals through a complete end-to-end implementation of a search pipeline.

---

## Features

- Web crawler that downloads and stores web pages
- Text extraction from HTML documents
- Inverted index construction
- TF-IDF relevance scoring
- Ranked search results
- Query caching for repeat searches
- Web-based interface using Flask
- Clean and modular project structure

---

## System Architecture

Crawler → Storage → Indexer → Ranker → Web Interface
---

## Components

### Crawler
- Fetches web pages from seed URLs
- Extracts readable text
- Saves each page to the `data/` directory

### Indexer
- Tokenizes stored documents
- Builds an inverted index
- Computes term frequency (TF)
- Computes document frequency (DF)
- Calculates TF-IDF scores

### Search Engine
- Accepts query input
- Ranks documents using TF-IDF
- Returns top-ranked results with snippets

### Web App
- Flask backend
- HTML interface for live searching
- Displays ranked links and snippets

---

## Project Structure

astra-search-engine
├── astra_crawler.py # Web crawler
├── astra_search.py # Indexing and TF-IDF logic
├── astra_web.py # Flask web interface
├── data/ # Crawled documents (.txt)
└── README.md


---

## How to Run

### 1. Install dependencies

```bash
pip install requests beautifulsoup4 flask

2. Run the crawler
python astra_crawler.py
This downloads web pages and stores text files inside the data/ directory.

Start the search engine
python astra_web.py

Open your browser at:
http://127.0.0.1:5000

🔎 Example Queries
python
science
history
programming
data structures
artificial intelligence

Ranking Algorithm

Astra uses TF-IDF scoring:

TF  = term frequency in document
IDF = log(total documents / documents containing term)
Score = TF × IDF

Results are sorted by score for relevance.

Why This Project Stands Out

Most student projects are UI-heavy and logic-light.
Astra is system-heavy and algorithm-focused.

This project demonstrates:

Understanding of real-world search systems
Backend engineering skills
Algorithmic implementation
Data processing
Scalable architecture thinking

Future Enhancements

PageRank
Multi-word phrase support
Query spell correction
Highlighted search terms
Stop-word filtering
Deployment
Performance profiling

⚠ Current Limitations

Not distributed
No backlink analysis
Designed for small-scale crawling

License
MIT License

Author
Built by Harshitha Reddy Yarva





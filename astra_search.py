import os
import math
import re
from collections import defaultdict

DATA_DIR = "data"


def load_documents():
    """
    Read all .txt files from the data/ folder.
    Returns: dict {doc_id -> text}
    """
    docs = {}
    if not os.path.exists(DATA_DIR):
        print(f"[astra-search] No '{DATA_DIR}' folder found. Run the crawler first.")
        return docs

    for filename in os.listdir(DATA_DIR):
        # only use .txt files
        if not filename.endswith(".txt"):
            continue

        path = os.path.join(DATA_DIR, filename)
        try:
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
            docs[filename] = text
        except Exception as e:
            print(f"[astra-search] Error reading {path}: {e}")

    print(f"[astra-search] Loaded {len(docs)} documents from '{DATA_DIR}'")
    return docs


def tokenize(text: str):
    """
    Lowercase and split into words.
    """
    return re.findall(r"[a-zA-Z0-9']+", text.lower())


def build_index(docs):
    """
    Build a TF-IDF-ready index.

    postings: term -> {doc_id: term_frequency}
    doc_lengths: doc_id -> total tokens in doc
    doc_freq: term -> in how many docs this term appears
    num_docs: total number of documents
    """
    postings = defaultdict(lambda: defaultdict(int))
    doc_lengths = defaultdict(int)
    doc_freq = defaultdict(int)

    for doc_id, text in docs.items():
        tokens = tokenize(text)
        doc_lengths[doc_id] = len(tokens)

        seen_in_doc = set()

        for token in tokens:
            postings[token][doc_id] += 1
            if token not in seen_in_doc:
                doc_freq[token] += 1
                seen_in_doc.add(token)

    num_docs = len(docs)
    print(f"[astra-search] Index built with {len(postings)} unique terms")
    return postings, doc_lengths, doc_freq, num_docs


def compute_idf(term: str, doc_freq, num_docs: int) -> float:
    """
    Inverse Document Frequency (IDF) with smoothing.
    """
    df = doc_freq.get(term, 0)
    if df == 0:
        return 0.0
    # +1 smoothing to avoid division by zero
    return math.log((num_docs + 1) / (df + 1)) + 1.0


def search(query: str, postings, doc_lengths, doc_freq, num_docs, docs, top_k: int = 5):
    """
    TF-IDF style search:
    - For each query term, look up the docs that contain it
    - Score(doc) += tf_normalized * idf * boost
    - tf_normalized = term_freq / doc_length
    - boost > 1 if term appears in URL/TITLE
    """
    tokens = tokenize(query)
    if not tokens:
        print("[astra-search] Empty query.")
        return []

    scores = defaultdict(float)

    for token in tokens:
        if token not in postings:
            continue

        idf = compute_idf(token, doc_freq, num_docs)
        if idf <= 0:
            continue

        for doc_id, tf in postings[token].items():
            dl = doc_lengths.get(doc_id, 1)
            tf_norm = tf / dl  # normalize by doc length

            # ---------- BOOST BLOCK (properly indented) ----------
            boost = 1.0

            # boost words that appear in the first two lines (URL + TITLE)
            head = docs[doc_id].splitlines()[:2]
            head_text = " ".join(head).lower()

            if token in head_text:
                boost = 2.0

            scores[doc_id] += tf_norm * idf * boost
            # ----------------------------------------------------

    if not scores:
        print("[astra-search] No results.")
        return []

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

    results = []
    for doc_id, score in ranked:
        text = docs[doc_id]
        lines = text.splitlines()
        first_line = lines[0] if lines else ""
        url = first_line.replace("URL: ", "") if first_line.startswith("URL: ") else "(unknown URL)"

        # body (skip URL + TITLE lines)
        body = "\n".join(lines[2:]) if len(lines) > 2 else text
        snippet = body[:200].replace("\n", " ")

        results.append(
            {
                "doc_id": doc_id,
                "url": url,
                "score": score,
                "snippet": snippet,
            }
        )

    return results


def interactive_search():
    docs = load_documents()
    if not docs:
        return

    postings, doc_lengths, doc_freq, num_docs = build_index(docs)

    while True:
        query = input("Enter search query (or 'quit'): ").strip()
        if query.lower() in ("quit", "exit"):
            print("[astra-search] Bye!")
            break

        results = search(query, postings, doc_lengths, doc_freq, num_docs, docs)
        if not results:
            continue

        print(f"\n[astra-search] Results for: '{query}'")
        for r in results:
            print(f"- {r['url']}")
            print(f"  score: {r['score']:.4f}  file: {r['doc_id']}")
            print(f"  snippet: {r['snippet']}...")
            print()
        print()


if __name__ == "__main__":
    interactive_search()

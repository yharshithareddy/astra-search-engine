from flask import Flask, request, render_template_string

from astra_search import load_documents, build_index, search

app = Flask(__name__)

# Build index once at startup
docs = load_documents()
if docs:
    postings, doc_lengths, doc_freq, num_docs = build_index(docs)
else:
    postings = doc_lengths = doc_freq = None
    num_docs = 0

# simple in-memory query cache
CACHE = {}


HTML_TEMPLATE = """
<!doctype html>
<html>
<head>
    <title>Astra Search</title>
    <style>
        * {
            box-sizing: border-box;
        }

        body {
            font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            background: #f3f4f6;
            margin: 0;
            padding: 0;
        }

        .page {
            max-width: 900px;
            margin: 40px auto;
            background: #ffffff;
            padding: 24px 28px 32px;
            border-radius: 12px;
            box-shadow: 0 10px 25px rgba(15, 23, 42, 0.08);
        }

        h1 {
            margin: 0 0 0.5rem;
            font-size: 2rem;
            color: #111827;
        }

        .subtitle {
            margin: 0 0 1.5rem;
            color: #6b7280;
            font-size: 0.95rem;
        }

        form {
            margin-bottom: 1.5rem;
            display: flex;
            gap: 8px;
        }

        input[type="text"] {
            flex: 1;
            padding: 10px 12px;
            border-radius: 999px;
            border: 1px solid #d1d5db;
            font-size: 0.95rem;
            outline: none;
            transition: border-color 0.15s ease, box-shadow 0.15s ease;
        }

        input[type="text"]:focus {
            border-color: #2563eb;
            box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.25);
        }

        button {
            padding: 10px 16px;
            border-radius: 999px;
            border: none;
            background: #2563eb;
            color: white;
            font-size: 0.95rem;
            font-weight: 500;
            cursor: pointer;
            transition: background 0.15s ease, transform 0.05s ease;
        }

        button:hover {
            background: #1d4ed8;
        }

        button:active {
            transform: scale(0.98);
        }

        .no-index {
            padding: 10px 12px;
            border-radius: 8px;
            background: #fee2e2;
            color: #b91c1c;
            font-size: 0.9rem;
            margin-top: 0.5rem;
        }

        .results-header {
            margin: 0 0 0.75rem;
            font-size: 0.95rem;
            color: #4b5563;
        }

        hr {
            border: none;
            border-top: 1px solid #e5e7eb;
            margin: 0 0 1rem;
        }

        .result {
            margin-bottom: 0.9rem;
            padding: 10px 12px;
            border-radius: 10px;
            background: #f9fafb;
            transition: box-shadow 0.12s ease, transform 0.12s ease, background 0.12s ease;
        }

        .result:hover {
            background: #f3f4ff;
            box-shadow: 0 4px 10px rgba(15, 23, 42, 0.08);
            transform: translateY(-1px);
        }

        .url {
            color: #16a34a;
            font-size: 0.8em;
            margin-bottom: 2px;
            word-break: break-all;
        }

        .url a {
            color: inherit;
            text-decoration: none;
        }

        .url a:hover {
            text-decoration: underline;
        }

        .score {
            color: #9ca3af;
            font-size: 0.8em;
            margin-bottom: 4px;
        }

        .snippet {
            font-size: 0.92em;
            color: #111827;
            line-height: 1.4;
        }

        .empty-state {
            margin-top: 0.5rem;
            font-size: 0.9rem;
            color: #6b7280;
        }
    </style>
</head>
<body>
    <div class="page">
        <h1>Astra Search</h1>
        <p class="subtitle">Mini search engine with crawling, TF-IDF ranking & caching.</p>

        <form method="get" action="/">
            <input type="text" name="q" placeholder="Search..." value="{{ query or '' }}">
            <button type="submit">Search</button>
        </form>

        {% if not indexed %}
            <div class="no-index">
                <strong>No documents indexed.</strong> Run the crawler first to populate the data folder.
            </div>
        {% else %}
            {% if query %}
                {% if results %}
                    <p class="results-header">Results for: <strong>{{ query }}</strong></p>
                    <hr>
                    {% for r in results %}
                        <div class="result">
                            <div class="url"><a href="{{ r.url }}" target="_blank">{{ r.url }}</a></div>
                            <div class="score">Score: {{ "%.4f"|format(r.score) }}</div>
                            <div class="snippet">{{ r.snippet }}...</div>
                        </div>
                    {% endfor %}
                {% else %}
                    <p class="empty-state">No results for <strong>{{ query }}</strong>.</p>
                {% endif %}
            {% endif %}
        {% endif %}
    </div>
</body>
</html>
"""


class ResultObj:
    def __init__(self, url, score, snippet):
        self.url = url
        self.score = score
        self.snippet = snippet


@app.route("/", methods=["GET"])
def home():
    query = request.args.get("q", "").strip()
    indexed = postings is not None and num_docs > 0
    results = []

    if query and indexed:
        # caching layer
        if query in CACHE:
            raw_results = CACHE[query]
        else:
            raw_results = search(query, postings, doc_lengths, doc_freq, num_docs, docs)
            CACHE[query] = raw_results

        for r in raw_results:
            results.append(ResultObj(r["url"], r["score"], r["snippet"]))

    return render_template_string(
        HTML_TEMPLATE,
        query=query,
        results=results,
        indexed=indexed,
    )


if __name__ == "__main__":
    app.run(debug=True)

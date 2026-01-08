from astra.common.tokenizer import parse_query, tokenize


def test_tokenize_basic():
    tokens = tokenize("The Quick brown fox jumps over the lazy dog.")
    assert "quick" in tokens
    assert "the" not in tokens
    assert "brown" in tokens


def test_parse_query_phrases():
    q = parse_query('"machine learning" fast api')
    assert q.phrases == ["machine learning"]
    assert "fast" in q.terms
    assert "api" in q.terms

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from .config import settings

_WORD_RE = re.compile(r"[A-Za-z0-9]+")

# A compact, curated stopword list (can be extended)
STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "if", "then", "else", "when", "while",
    "is", "are", "was", "were", "be", "been", "being",
    "to", "of", "in", "on", "for", "from", "with", "as", "at", "by", "about",
    "it", "this", "that", "these", "those",
    "i", "you", "he", "she", "we", "they", "them", "us", "our", "your",
    "not", "no", "yes", "do", "does", "did", "doing",
    "can", "could", "should", "would", "may", "might", "will", "just",
}


@dataclass(frozen=True)
class Query:
    terms: list[str]
    phrases: list[str]


def tokenize(text: str) -> list[str]:
    tokens: list[str] = []
    for m in _WORD_RE.finditer(text.lower()):
        t = m.group(0)
        if len(t) < settings.min_token_len:
            continue
        if t in STOPWORDS:
            continue
        tokens.append(t)
    return tokens


_PHRASE_RE = re.compile(r'"([^"]+)"')


def parse_query(q: str) -> Query:
    phrases = [p.strip() for p in _PHRASE_RE.findall(q) if p.strip()]
    q_wo_phrases = _PHRASE_RE.sub(" ", q)
    terms = tokenize(q_wo_phrases)
    return Query(terms=terms, phrases=phrases)


def count_terms(tokens: Iterable[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for t in tokens:
        counts[t] = counts.get(t, 0) + 1
    return counts

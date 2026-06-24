from __future__ import annotations

import math
import re
from collections import Counter
from pathlib import Path
from typing import Any

from reqsys_agent.workspace_reader import build_index, load_index

TOKEN_PATTERN = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9_]{3,}")
STOPWORDS = {
    "a", "ao", "aos", "as", "com", "da", "das", "de", "do", "dos", "e", "em", "na", "nas", "no", "nos", "o", "os", "ou", "para", "por", "que", "quais", "qual", "uma", "um",
    "the", "and", "for", "with", "from", "this", "that", "are", "you", "your",
}


def tokenize(text: str) -> list[str]:
    tokens = [token.lower() for token in TOKEN_PATTERN.findall(text)]
    return [token for token in tokens if token not in STOPWORDS]


def term_frequency(tokens: list[str]) -> dict[str, float]:
    total = max(len(tokens), 1)
    counts = Counter(tokens)
    return {term: count / total for term, count in counts.items()}


def cosine_similarity(left: dict[str, float], right: dict[str, float]) -> float:
    if not left or not right:
        return 0.0
    common = set(left).intersection(right)
    numerator = sum(left[term] * right[term] for term in common)
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return numerator / (left_norm * right_norm)


def build_idf(documents: list[list[str]]) -> dict[str, float]:
    total_docs = max(len(documents), 1)
    document_frequency: Counter[str] = Counter()
    for tokens in documents:
        document_frequency.update(set(tokens))
    return {
        term: math.log((1 + total_docs) / (1 + frequency)) + 1
        for term, frequency in document_frequency.items()
    }


def tfidf_vector(tokens: list[str], idf: dict[str, float]) -> dict[str, float]:
    tf = term_frequency(tokens)
    return {term: value * idf.get(term, 1.0) for term, value in tf.items()}


def semantic_search(workspace: Path, question: str, limit: int = 10) -> dict[str, Any]:
    index = load_index(workspace)
    if index is None:
        index = build_index(workspace)

    files = index.get("files", [])
    documents: list[list[str]] = [
        tokenize(f"{file.get('path', '')}\n{file.get('preview', '')}")
        for file in files
    ]
    query_tokens = tokenize(question)
    idf = build_idf(documents + [query_tokens])
    query_vector = tfidf_vector(query_tokens, idf)

    matches: list[dict[str, Any]] = []
    for file, tokens in zip(files, documents):
        vector = tfidf_vector(tokens, idf)
        score = cosine_similarity(query_vector, vector)
        if score <= 0:
            continue
        matches.append({
            "path": file.get("path"),
            "score": round(score, 6),
            "sha256": file.get("sha256"),
            "preview": file.get("preview", "")[:700],
        })

    matches.sort(key=lambda item: (-float(item["score"]), str(item["path"])))
    return {
        "question": question,
        "answer_mode": "local-tfidf-cosine",
        "file_count": index.get("file_count", 0),
        "matches": matches[:limit],
        "limitations": [
            "no external LLM used",
            "no embeddings provider required",
            "lightweight TF-IDF/cosine ranking",
            "results must be validated against file evidence",
        ],
    }

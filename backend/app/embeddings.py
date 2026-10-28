"""Эмбеддинги. По умолчанию — локальный hashing-эмбеддинг (без внешних вызовов, детерминированный),
для качества — OpenAI или локальная модель через Ollama (openai-совместимый API)."""

import hashlib
import math
import re

from app.config import get_settings
from app.knowledge import normalize

TOKEN_RE = re.compile(r"[a-zа-яё0-9+#]+", re.I)


def _hash_embed(text: str, dim: int) -> list[float]:
    vec = [0.0] * dim
    text = normalize(text)
    tokens = TOKEN_RE.findall(text)
    feats = tokens + [f"{a}_{b}" for a, b in zip(tokens, tokens[1:])]
    for t in tokens:
        padded = f"#{t}#"
        feats += [padded[i : i + 3] for i in range(len(padded) - 2)]
    for f in feats:
        h = int(hashlib.md5(f.encode()).hexdigest(), 16)
        vec[h % dim] += 1.0 if (h >> 8) % 2 else -1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def embed(texts: list[str]) -> list[list[float]]:
    s = get_settings()
    if s.embedding_provider == "hash" or not texts:
        return [_hash_embed(t, s.embedding_dim) for t in texts]

    from openai import OpenAI

    if s.embedding_provider == "openai":
        client = OpenAI(api_key=s.openai_api_key)
        model = s.embedding_model or "text-embedding-3-small"
    elif s.embedding_provider == "ollama":
        client = OpenAI(api_key="ollama", base_url=s.ollama_base_url)
        model = s.embedding_model or "nomic-embed-text"
    else:
        raise ValueError(f"Unknown embedding provider {s.embedding_provider}")
    kwargs = {"dimensions": s.embedding_dim} if s.embedding_provider == "openai" else {}
    resp = client.embeddings.create(model=model, input=texts, **kwargs)
    return [d.embedding for d in resp.data]


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)

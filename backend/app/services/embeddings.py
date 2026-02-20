from __future__ import annotations

from typing import Iterable

from app.core.config import settings
from app.services.openai_client import get_client

def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    client = get_client()
    resp = client.embeddings.create(
        model=settings.openai_embed_model,
        input=texts,
    )
    # resp.data is list of embeddings in same order as inputs
    return [d.embedding for d in resp.data]

def embed_query(text: str) -> list[float]:
    return embed_texts([text])[0]

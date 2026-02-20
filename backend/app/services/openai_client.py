from __future__ import annotations

from openai import OpenAI
from app.core.config import settings

_client: OpenAI | None = None

def get_client() -> OpenAI:
    global _client
    if _client is None:
        # OpenAI SDK reads OPENAI_API_KEY from env automatically.
        # You can also pass api_key=... explicitly if needed.
        _client = OpenAI()
    return _client

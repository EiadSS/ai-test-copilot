from __future__ import annotations

import re

def normalize(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

def chunk_text(text: str, chunk_size: int = 1200, overlap: int = 200) -> list[str]:
    text = normalize(text)
    if not text:
        return []

    chunks: list[str] = []
    start = 0
    n = len(text)

    while start < n:
        end = min(start + chunk_size, n)
        chunk = text[start:end]

        # Try to end on a newline or sentence boundary to keep chunks readable
        cut = max(chunk.rfind("\n"), chunk.rfind(". "), chunk.rfind("; "), chunk.rfind(", "))
        if cut > int(chunk_size * 0.6):
            end = start + cut + 1
            chunk = text[start:end]

        chunks.append(chunk.strip())
        if end >= n:
            break
        start = max(0, end - overlap)

    # Remove tiny chunks
    return [c for c in chunks if len(c) >= 40]

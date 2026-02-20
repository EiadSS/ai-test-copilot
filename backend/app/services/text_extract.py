from __future__ import annotations

from io import BytesIO
from pypdf import PdfReader

def extract_text(data: bytes, content_type: str, filename: str) -> str:
    ct = (content_type or "").lower()
    name = (filename or "").lower()

    if "pdf" in ct or name.endswith(".pdf"):
        reader = PdfReader(BytesIO(data))
        parts: list[str] = []
        for page in reader.pages:
            parts.append(page.extract_text() or "")
        return "\n".join(parts)

    # OpenAPI YAML/JSON or general text
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("utf-8", errors="ignore")

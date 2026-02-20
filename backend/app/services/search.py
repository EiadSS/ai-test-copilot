from __future__ import annotations

import uuid
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.config import settings
from app.db.models import Chunk
from app.services.embeddings import embed_query

def semantic_search(db: Session, project_id: uuid.UUID, query: str, top_k: int | None = None):
    k = top_k or settings.rag_top_k
    qvec = embed_query(query)

    # pgvector provides distance helpers on Vector columns (cosine_distance, l2_distance, etc.)
    stmt = (
        select(Chunk)
        .where(Chunk.project_id == project_id)
        .order_by(Chunk.embedding.cosine_distance(qvec))
        .limit(k)
    )
    rows = db.execute(stmt).scalars().all()
    return [
        {
            "chunk_id": str(r.id),
            "document_id": str(r.document_id),
            "idx": r.idx,
            "text": r.text[:800],
        }
        for r in rows
    ]

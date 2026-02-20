from __future__ import annotations

import uuid
from celery import shared_task
from sqlalchemy import delete

from app.tasks.celery_app import celery
from app.db.session import SessionLocal
from app.db.models import Document, Chunk
from app.core.config import settings
from app.services.text_extract import extract_text
from app.services.chunking import chunk_text
from app.services.embeddings import embed_texts

@celery.task(name="ingest_document_task")
def ingest_document_task(document_id: str, data: bytes, content_type: str, filename: str):
    db = SessionLocal()
    try:
        did = uuid.UUID(document_id)
        doc = db.get(Document, did)
        if not doc:
            raise ValueError("Document not found")

        # Clear prior chunks if re-ingesting
        db.execute(delete(Chunk).where(Chunk.document_id == did))
        db.commit()

        text = extract_text(data, content_type, filename)
        chunks = chunk_text(text, chunk_size=settings.chunk_size, overlap=settings.chunk_overlap)

        # Embed in batches (keep it simple)
        embeddings: list[list[float]] = []
        B = 64
        for i in range(0, len(chunks), B):
            embeddings.extend(embed_texts(chunks[i:i+B]))

        for idx, (ctext, emb) in enumerate(zip(chunks, embeddings)):
            row = Chunk(
                project_id=doc.project_id,
                document_id=doc.id,
                idx=idx,
                text=ctext,
                embedding=emb,
                meta={"filename": doc.filename},
            )
            db.add(row)

        doc.status = "ready"
        db.commit()
        return {"document_id": document_id, "chunks": len(chunks), "status": doc.status}
    finally:
        db.close()

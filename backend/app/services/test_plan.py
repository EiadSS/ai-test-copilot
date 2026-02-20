from __future__ import annotations

import json
import re
import uuid
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import TestPlan
from app.services.search import semantic_search
from app.services.openai_client import get_client

TEST_PLAN_SCHEMA_HINT = {
    "project_overview": "string",
    "tests": [
        {
            "id": "T001",
            "priority": "P0|P1|P2",
            "title": "string",
            "type": "api|ui|integration",
            "preconditions": ["string"],
            "steps": ["string"],
            "expected": ["string"],
            "tags": ["string"],
            "sources": ["doc chunk ids or short citations"],
        }
    ]
}

def _extract_json(text: str) -> dict:
    # Best-effort JSON extraction
    m = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not m:
        raise ValueError("Model did not return JSON")
    return json.loads(m.group(0))

def generate_test_plan(db: Session, project_id: uuid.UUID, job_id: str) -> dict:
    # Retrieve context via semantic search using a broad query
    contexts = semantic_search(db, project_id, "requirements, user flows, API endpoints, error cases, auth, validation", top_k=settings.rag_top_k)
    context_blob = "\n\n".join(
        [f"[Chunk {c['chunk_id']} / doc {c['document_id']} idx {c['idx']}]\n{c['text']}" for c in contexts]
    )

    prompt = f"""You are an expert QA/SDET and software engineer.
Create a practical test plan for the project based ONLY on the context below.

Output STRICT JSON (no markdown) with this shape (keys must exist):
{json.dumps(TEST_PLAN_SCHEMA_HINT, indent=2)}

Rules:
- Prefer high-value tests: auth, validation, error handling, rate limits, permissions, idempotency, boundary cases.
- Include a mix of API, UI, and integration tests if the context supports it.
- Each test MUST include a 'sources' array referencing chunk ids (e.g., 'Chunk <uuid>') that justify the test.
- Keep steps actionable and specific.

CONTEXT:
{context_blob}
"""

    client = get_client()
    resp = client.responses.create(
        model=settings.openai_chat_model,
        input=prompt,
    )
    out = resp.output_text
    plan = _extract_json(out)

    row = TestPlan(project_id=project_id, job_id=job_id, plan_json=plan)
    db.add(row)
    db.commit()
    return plan

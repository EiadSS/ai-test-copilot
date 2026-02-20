from __future__ import annotations

import uuid
from app.tasks.celery_app import celery
from app.db.session import SessionLocal
from app.services.test_plan import generate_test_plan

@celery.task(name="generate_test_plan_task")
def generate_test_plan_task(project_id: str):
    db = SessionLocal()
    try:
        pid = uuid.UUID(project_id)
        job_id = generate_test_plan_task.request.id  # Celery job id
        plan = generate_test_plan(db, pid, job_id=job_id)
        return {"project_id": project_id, "tests": len(plan.get("tests", []))}
    finally:
        db.close()

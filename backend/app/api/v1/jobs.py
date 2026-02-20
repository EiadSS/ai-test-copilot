from fastapi import APIRouter
from celery.result import AsyncResult
from app.tasks.celery_app import celery

router = APIRouter()

@router.get("/{job_id}")
def job_status(job_id: str):
    r = AsyncResult(job_id, app=celery)
    data = {
        "job_id": job_id,
        "state": r.state,
    }
    if r.state == "FAILURE":
        data["error"] = str(r.result)
    if r.state == "SUCCESS":
        data["result"] = r.result
    return data

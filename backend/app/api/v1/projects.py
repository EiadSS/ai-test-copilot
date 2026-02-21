import uuid
import io
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select, desc
from fastapi.responses import StreamingResponse
from app.services.playwright_api_gen import generate_playwright_api_tests_zip
from fastapi.responses import Response

from app.db.session import get_db
from app.db.models import Project, Document, Chunk, TestPlan
from app.tasks.ingest_tasks import ingest_document_task
from app.tasks.plan_tasks import generate_test_plan_task
from app.services.search import semantic_search

router = APIRouter()

@router.post("")
def create_project(payload: dict, db: Session = Depends(get_db)):
    name = (payload or {}).get("name")
    if not name:
        raise HTTPException(status_code=400, detail="Missing project name")
    proj = Project(name=name)
    db.add(proj)
    db.commit()
    db.refresh(proj)
    return {"id": str(proj.id), "name": proj.name, "created_at": proj.created_at}

@router.get("")
def list_projects(db: Session = Depends(get_db)):
    items = db.execute(select(Project).order_by(desc(Project.created_at))).scalars().all()
    return [{"id": str(p.id), "name": p.name, "created_at": p.created_at} for p in items]

@router.post("/{project_id}/documents")
async def upload_document(project_id: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        pid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project_id")

    proj = db.get(Project, pid)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    data = await file.read()
    doc = Document(
        project_id=pid,
        filename=file.filename or "upload",
        content_type=file.content_type or "application/octet-stream",
        status="uploaded",
    )
    # store raw bytes in doc meta for now (MVP). Later: object storage.
    # Keeping MVP simple: store in memory in task payload (Redis).
    db.add(doc)
    db.commit()
    db.refresh(doc)

    job = ingest_document_task.delay(str(doc.id), data, doc.content_type, doc.filename)
    doc.status = "ingesting"
    db.commit()

    return {"document_id": str(doc.id), "job_id": job.id, "status": doc.status}

@router.get("/{project_id}/documents")
def list_documents(project_id: str, db: Session = Depends(get_db)):
    try:
        pid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project_id")

    docs = db.execute(select(Document).where(Document.project_id == pid).order_by(desc(Document.created_at))).scalars().all()
    return [
        {"id": str(d.id), "filename": d.filename, "content_type": d.content_type, "status": d.status, "created_at": d.created_at}
        for d in docs
    ]

@router.get("/{project_id}/search")
def search(project_id: str, q: str, db: Session = Depends(get_db)):
    try:
        pid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project_id")

    results = semantic_search(db, pid, q)
    return {"query": q, "results": results}

@router.post("/{project_id}/generate/test-plan")
def generate_test_plan(project_id: str, db: Session = Depends(get_db)):
    try:
        pid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project_id")

    proj = db.get(Project, pid)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    job = generate_test_plan_task.delay(str(pid))
    return {"job_id": job.id}

@router.get("/{project_id}/test-plans/latest")
def latest_test_plan(project_id: str, db: Session = Depends(get_db)):
    try:
        pid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project_id")

    plan = db.execute(
        select(TestPlan).where(TestPlan.project_id == pid).order_by(desc(TestPlan.created_at)).limit(1)
    ).scalars().first()

    if not plan:
        raise HTTPException(status_code=404, detail="No test plans yet")

    return {"id": str(plan.id), "job_id": plan.job_id, "created_at": plan.created_at, "plan": plan.plan_json}

@router.get("/{project_id}/test-plans/latest/playwright-api.zip")
def download_latest_playwright_api_zip(project_id: str, db: Session = Depends(get_db)):
    try:
        pid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project_id")

    proj = db.get(Project, pid)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    plan = db.execute(
        select(TestPlan).where(TestPlan.project_id == pid).order_by(desc(TestPlan.created_at)).limit(1)
    ).scalars().first()
    if not plan:
        raise HTTPException(status_code=404, detail="No test plans yet")

    zip_bytes = generate_playwright_api_tests_zip(plan.plan_json, project_name=proj.name)
    filename = "playwright-api-tests.zip"

    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="playwright-api-tests.zip"'},
    )
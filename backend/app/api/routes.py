from fastapi import APIRouter
from app.api.v1.projects import router as projects_router
from app.api.v1.jobs import router as jobs_router

router = APIRouter()
router.include_router(projects_router, prefix="/projects", tags=["projects"])
router.include_router(jobs_router, prefix="/jobs", tags=["jobs"])

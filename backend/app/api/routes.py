from fastapi import APIRouter
from app.api.v1.projects import router as projects_router
from app.api.v1.jobs import router as jobs_router
from app.api.v1.demo_auth import router as demo_auth_router

router = APIRouter()
router.include_router(projects_router, prefix="/projects", tags=["projects"])
router.include_router(jobs_router, prefix="/jobs", tags=["jobs"])
router.include_router(demo_auth_router, tags=["demo-auth"])

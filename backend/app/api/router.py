from fastapi import APIRouter
from sqlalchemy import text

from app.api.routes.applications import router as applications_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.salary import router as salary_router
from app.api.routes.auth import router as auth_router
from app.api.routes.interview import router as interview_router
from app.api.routes.job_postings import router as job_postings_router
from app.api.routes.linkedin import router as linkedin_router
from app.api.routes.profiles import router as profiles_router
from app.api.routes.public_share import router as public_share_router
from app.api.routes.resumes import router as resumes_router
from app.api.routes.roadmap import router as roadmap_router
from app.db.session import engine

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(profiles_router)
api_router.include_router(resumes_router)
api_router.include_router(public_share_router)
api_router.include_router(job_postings_router)
api_router.include_router(roadmap_router)
api_router.include_router(linkedin_router)
api_router.include_router(interview_router)
api_router.include_router(applications_router)
api_router.include_router(dashboard_router)
api_router.include_router(salary_router)


@api_router.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@api_router.get("/health/db", tags=["health"])
def health_db() -> dict[str, str]:
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"status": "ok", "database": "reachable"}

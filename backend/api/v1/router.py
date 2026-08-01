from fastapi import APIRouter
from api.v1 import health, profiles, search, jobs, export

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(profiles.router, prefix="/profiles", tags=["profiles"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_router.include_router(export.router, prefix="/export", tags=["export"])

"""Health check endpoint."""
from fastapi import APIRouter
from backend.core.config import settings

router = APIRouter()

@router.get("/health", summary="Health check")
def health():
    return {"status": "ok", "version": settings.APP_VERSION, "app": settings.APP_NAME}

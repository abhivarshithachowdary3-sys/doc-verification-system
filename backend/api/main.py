"""
Smart Document Verification API — FastAPI application entry point.
"""

from contextlib import asynccontextmanager
import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.core.config import settings
from backend.api.routes import verification, status, health
from backend.api.middleware import LoggingMiddleware
from backend.database.connection import create_tables

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Smart Document Verification API...")
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    create_tables()
    logger.info("Database tables created / verified.")
    yield
    logger.info("Shutting down.")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Multi-agent document verification system with OCR, fraud detection & blockchain anchoring.",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── Middleware ────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(LoggingMiddleware)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(health.router,        prefix="/api/v1", tags=["Health"])
app.include_router(verification.router,  prefix="/api/v1", tags=["Verification"])
app.include_router(status.router,        prefix="/api/v1", tags=["Status"])

# ── Static frontend ───────────────────────────────────────────────────────────
if os.path.exists("frontend"):
    app.mount("/", StaticFiles(directory="frontend", html=True), name="static")

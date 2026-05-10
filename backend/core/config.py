"""
Centralised configuration loaded from environment variables.
Never hardcode secrets — always read from .env via python-dotenv.
"""

import os
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── App ───────────────────────────────────────────────────────────
    APP_NAME: str = "Smart Document Verification API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    SECRET_KEY: str = "change-me-in-production"

    # ── Database ──────────────────────────────────────────────────────
    DATABASE_URL: str = "sqlite:///./verification.db"

    # ── Redis (for job queue / caching) ───────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── OCR ───────────────────────────────────────────────────────────
    TESSERACT_CMD: str = "/usr/bin/tesseract"
    OCR_CONFIDENCE_THRESHOLD: float = 60.0

    # ── LLM (OpenAI-compatible endpoint) ─────────────────────────────
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"

    # ── Blockchain ────────────────────────────────────────────────────
    WEB3_PROVIDER_URL: str = "http://localhost:8545"   # local Hardhat / Ganache
    CONTRACT_ADDRESS: str = ""
    DEPLOYER_PRIVATE_KEY: str = ""

    # ── External verification APIs ────────────────────────────────────
    UIDAI_API_URL: str = "https://stage1.uidai.gov.in/onboardingservice/api/v2"
    UIDAI_API_KEY: str = ""

    # ── Storage ───────────────────────────────────────────────────────
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE_MB: int = 10

    # ── Fraud detection ───────────────────────────────────────────────
    FRAUD_SCORE_THRESHOLD: float = 0.65   # above → fraud_suspected

    # ── CORS ──────────────────────────────────────────────────────────
    ALLOWED_ORIGINS: list = ["http://localhost:3000", "http://localhost:8080"]

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

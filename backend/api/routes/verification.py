"""Verification endpoints — upload document, trigger pipeline, get result."""

import os
import uuid
import aiofiles
import logging
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse

from backend.core.config import settings
from backend.core.graph import run_verification
from backend.database.models import VerificationRecord
from backend.database.connection import get_session

router = APIRouter()
logger = logging.getLogger(__name__)

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/tiff"}


@router.post("/verify", summary="Submit a document image for verification")
async def verify_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Identity document image (JPEG/PNG/WEBP/TIFF)"),
):
    # Validate content type
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{file.content_type}'. Accepted: {ALLOWED_TYPES}",
        )

    # Validate file size
    contents = await file.read()
    if len(contents) > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size: {settings.MAX_FILE_SIZE_MB} MB",
        )

    # Save to disk
    request_id = str(uuid.uuid4())
    ext = os.path.splitext(file.filename or "doc.jpg")[1] or ".jpg"
    save_path = os.path.join(settings.UPLOAD_DIR, f"{request_id}{ext}")

    async with aiofiles.open(save_path, "wb") as f:
        await f.write(contents)

    logger.info(f"Saved upload {request_id} → {save_path}")

    # Run pipeline synchronously for MVP (move to Celery/RQ for production)
    try:
        result = run_verification(image_path=save_path, request_id=request_id)
    except Exception as e:
        logger.error(f"Pipeline error for {request_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Verification pipeline error: {str(e)}")

    # Persist to DB in background
    background_tasks.add_task(_persist_result, request_id, result)

    return JSONResponse(content=result.get("report", {}), status_code=200)


@router.get("/verify/{request_id}", summary="Retrieve a previous verification result")
async def get_verification(request_id: str):
    with get_session() as session:
        record = session.get(VerificationRecord, request_id)
        if not record:
            raise HTTPException(status_code=404, detail="Verification record not found")
        return JSONResponse(content=record.report_json)


def _persist_result(request_id: str, state: dict):
    try:
        with get_session() as session:
            rec = VerificationRecord(
                request_id=request_id,
                status=str(state.get("verification_status", "")),
                document_type=str(state.get("document_type", "")),
                fraud_score=state.get("fraud_score"),
                verification_score=state.get("verification_score"),
                blockchain_tx=state.get("blockchain_tx_hash"),
                report_json=state.get("report", {}),
            )
            session.add(rec)
            session.commit()
    except Exception as e:
        logger.error(f"DB persist error for {request_id}: {e}")

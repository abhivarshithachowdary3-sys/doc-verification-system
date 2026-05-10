"""OCR Agent — runs the OCR engine and populates ocr_raw_text in state."""

import logging
from backend.core.state import VerificationState
from backend.ocr.engine import ocr_engine

logger = logging.getLogger(__name__)


def run_ocr(state: VerificationState) -> VerificationState:
    logger.info(f"[OCR] Processing request {state['request_id']}")
    try:
        text, confidence = ocr_engine.extract(state["image_path"])
        if not text:
            state["errors"].append("OCR produced empty output")
            state["ocr_completed"] = False
        else:
            state["ocr_raw_text"] = text
            state["ocr_confidence"] = round(confidence, 2)
            state["ocr_completed"] = True
            logger.info(f"[OCR] Done. Confidence={confidence:.1f}, chars={len(text)}")
    except Exception as e:
        logger.error(f"[OCR] Failed: {e}")
        state["errors"].append(f"OCR error: {str(e)}")
        state["ocr_completed"] = False
    return state

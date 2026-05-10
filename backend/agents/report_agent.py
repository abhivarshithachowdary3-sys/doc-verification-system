"""Report Agent — builds the final structured verification report."""

import logging
from datetime import datetime, timezone
from backend.core.state import VerificationState, VerificationStatus

logger = logging.getLogger(__name__)


def _compute_verification_score(state: VerificationState) -> float:
    score = 0.0
    weights = {
        "ocr":          (state.get("ocr_confidence") or 0) / 100 * 0.20,
        "classification":(state.get("classification_confidence") or 0) * 0.15,
        "extraction":   (state.get("extraction_confidence") or 0) * 0.25,
        "fraud":        (1.0 - (state.get("fraud_score") or 0)) * 0.25,
        "external":     0.15 if state.get("external_verified") else 0.0,
    }
    score = sum(weights.values())
    return round(min(max(score, 0.0), 1.0), 3)


def run_report(state: VerificationState) -> VerificationState:
    logger.info(f"[REPORT] Building report for request {state['request_id']}")

    verification_score = _compute_verification_score(state)
    state["verification_score"] = verification_score

    if state.get("errors") and not state.get("ocr_completed"):
        status = VerificationStatus.FAILED
    elif state.get("is_fraud_suspected"):
        status = VerificationStatus.FRAUD_SUSPECTED
    elif verification_score >= 0.75:
        status = VerificationStatus.VERIFIED
    elif verification_score >= 0.50:
        status = VerificationStatus.MANUAL_REVIEW
    else:
        status = VerificationStatus.FAILED

    state["verification_status"] = status

    fields = state.get("extracted_fields") or {}
    safe_fields = {k: v for k, v in fields.items() if k != "raw_text"}

    state["report"] = {
        "request_id":           state["request_id"],
        "status":               status.value,
        "verification_score":   verification_score,
        "document_type":        (state.get("document_type") or "unknown"),
        "extracted_fields":     safe_fields,
        "fraud_analysis": {
            "fraud_score":      state.get("fraud_score"),
            "is_suspected":     state.get("is_fraud_suspected"),
            "flags":            state.get("fraud_flags", []),
        },
        "external_verification": {
            "verified":         state.get("external_verified"),
            "provider":         state.get("external_provider"),
        },
        "blockchain": {
            "anchored":         state.get("blockchain_anchored"),
            "document_hash":    state.get("document_hash"),
            "tx_hash":          state.get("blockchain_tx_hash"),
        },
        "ocr_confidence":       state.get("ocr_confidence"),
        "errors":               state.get("errors", []),
        "processing_time_ms":   state.get("processing_time_ms"),
        "created_at":           state.get("created_at"),
        "updated_at":           datetime.now(timezone.utc).isoformat(),
    }

    logger.info(f"[REPORT] status={status.value}, score={verification_score}")
    return state

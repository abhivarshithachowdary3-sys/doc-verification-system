"""
External Verification Agent — calls third-party / government APIs for
real-time document validation. Falls back gracefully if unavailable.
"""

import hashlib
import logging
from backend.core.state import VerificationState, DocumentType
from backend.core.config import settings

logger = logging.getLogger(__name__)


def _hash_document_fields(state: VerificationState) -> str:
    fields = state.get("extracted_fields") or {}
    payload = "|".join([
        str(fields.get("aadhaar_number", "")),
        str(fields.get("name", "")),
        str(fields.get("dob", "")),
    ])
    return hashlib.sha256(payload.encode()).hexdigest()


def _mock_uidai_verify(aadhaar_number: str, name: str, dob: str) -> dict:
    """
    Placeholder for UIDAI OTP-based verification.
    Replace with real UIDAI sandbox API call in production.
    Docs: https://uidai.gov.in/en/ecosystem/authentication-devices-documents/developer-section.html
    """
    return {
        "verified": True,
        "provider": "UIDAI_MOCK",
        "message": "Demographic auth simulated (sandbox mode)",
    }


def run_external_verification(state: VerificationState) -> VerificationState:
    logger.info(f"[EXTERNAL] Request {state['request_id']}")
    doc_type = state.get("document_type")
    fields = state.get("extracted_fields") or {}

    doc_hash = _hash_document_fields(state)
    state["document_hash"] = doc_hash

    try:
        if doc_type == DocumentType.AADHAAR:
            aadhaar_num = fields.get("aadhaar_number", "")
            name = fields.get("name", "")
            dob = fields.get("dob", "")

            if settings.UIDAI_API_KEY:
                # TODO: wire real UIDAI API here
                pass

            result = _mock_uidai_verify(aadhaar_num, name, dob)
            state["external_verified"] = result.get("verified", False)
            state["external_provider"] = result.get("provider", "UNKNOWN")
            state["external_response"] = result
        else:
            # Non-Aadhaar docs: mark as not externally verified for now
            state["external_verified"] = None
            state["external_provider"] = "NOT_SUPPORTED"
            state["external_response"] = {"message": "External verification not available for this document type"}

    except Exception as e:
        logger.error(f"[EXTERNAL] Failed: {e}")
        state["errors"].append(f"External verification error: {str(e)}")
        state["external_verified"] = None

    return state

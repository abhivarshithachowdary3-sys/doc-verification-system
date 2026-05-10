"""
Classification Agent — identifies document type from OCR text using
keyword heuristics + regex patterns. No model dependency required.
"""

import re
import logging
from backend.core.state import VerificationState, DocumentType

logger = logging.getLogger(__name__)

PATTERNS: dict[DocumentType, list[str]] = {
    DocumentType.AADHAAR: [
        r"\baadh[ae]{1,2}r\b", r"\bUID(AI)?\b", r"\bEnrollment\s+No\b",
        r"\bGovernment\s+of\s+India\b", r"\bUnique\s+Identification\b",
        r"\d{4}\s\d{4}\s\d{4}",
    ],
    DocumentType.PAN: [
        r"\bPermanent\s+Account\s+Number\b", r"\bIncome\s+Tax\s+Department\b",
        r"\bGovt\.?\s+of\s+India\b", r"[A-Z]{5}[0-9]{4}[A-Z]{1}",
        r"\bPAN\b",
    ],
    DocumentType.PASSPORT: [
        r"\bPassport\b", r"\bRepublic\s+of\s+India\b",
        r"\bMinistry\s+of\s+(External\s+)?Affairs\b",
        r"[A-Z][0-9]{7}", r"\bMRZ\b", r"P<IND",
    ],
    DocumentType.DRIVING_LICENSE: [
        r"\bDriving\s+Licen[sc]e\b", r"\bDL\s+No\b",
        r"\bTransport\s+Authority\b", r"\bMotor\s+Vehicles\b",
    ],
    DocumentType.VOTER_ID: [
        r"\bElection\s+Commission\b", r"\bVoter\b",
        r"\bElector(al)?\s+Photo\b", r"\bEPIC\b",
    ],
}


def run_classification(state: VerificationState) -> VerificationState:
    logger.info(f"[CLASSIFY] Request {state['request_id']}")
    text = (state.get("ocr_raw_text") or "").upper()

    scores: dict[DocumentType, int] = {dt: 0 for dt in PATTERNS}

    for doc_type, patterns in PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                scores[doc_type] += 1

    best_type = max(scores, key=scores.get)
    best_score = scores[best_type]
    total_patterns = len(PATTERNS[best_type])
    confidence = best_score / total_patterns if total_patterns else 0.0

    if best_score == 0:
        state["document_type"] = DocumentType.UNKNOWN
        state["classification_confidence"] = 0.0
        state["errors"].append("Could not classify document type")
    else:
        state["document_type"] = best_type
        state["classification_confidence"] = round(confidence, 3)

    logger.info(f"[CLASSIFY] Type={state['document_type']}, conf={confidence:.2f}")
    return state

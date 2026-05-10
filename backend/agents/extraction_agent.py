"""
Extraction Agent — pulls structured fields from OCR text based on document type.
Aadhaar and PAN have strong regex patterns. Others fall back to heuristics.
"""

import re
import logging
from typing import Optional
from backend.core.state import VerificationState, DocumentType, ExtractedFields

logger = logging.getLogger(__name__)


# ── Aadhaar extractors ────────────────────────────────────────────────────────

def _extract_aadhaar_number(text: str) -> Optional[str]:
    # Matches: 1234 5678 9012 or 1234-5678-9012
    m = re.search(r"\b(\d{4}[\s\-]\d{4}[\s\-]\d{4})\b", text)
    return m.group(1).replace(" ", "").replace("-", "") if m else None


def _extract_name_aadhaar(text: str) -> Optional[str]:
    # Name usually appears after DOB line or before S/O D/O W/O
    patterns = [
        r"(?:Name|नाम)[:\s]+([A-Z][a-z]+(?:\s[A-Z][a-z]+){1,3})",
        r"^([A-Z][a-z]+(?:\s[A-Z][a-z]+){1,3})$",
    ]
    for p in patterns:
        m = re.search(p, text, re.MULTILINE)
        if m:
            return m.group(1).strip()
    return None


def _extract_dob(text: str) -> Optional[str]:
    patterns = [
        r"DOB[:\s]+(\d{2}[/\-]\d{2}[/\-]\d{4})",
        r"Date\s+of\s+Birth[:\s]+(\d{2}[/\-]\d{2}[/\-]\d{4})",
        r"\b(\d{2}[/\-]\d{2}[/\-]\d{4})\b",
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m.group(1)
    return None


def _extract_gender(text: str) -> Optional[str]:
    if re.search(r"\bMALE\b", text, re.IGNORECASE):
        return "MALE"
    if re.search(r"\bFEMALE\b", text, re.IGNORECASE):
        return "FEMALE"
    if re.search(r"\bTRANSGENDER\b", text, re.IGNORECASE):
        return "TRANSGENDER"
    return None


def _extract_pincode(text: str) -> Optional[str]:
    m = re.search(r"\b([1-9][0-9]{5})\b", text)
    return m.group(1) if m else None


# ── PAN extractors ────────────────────────────────────────────────────────────

def _extract_pan_number(text: str) -> Optional[str]:
    m = re.search(r"\b([A-Z]{5}[0-9]{4}[A-Z])\b", text)
    return m.group(1) if m else None


# ── Passport extractors ───────────────────────────────────────────────────────

def _extract_passport_number(text: str) -> Optional[str]:
    m = re.search(r"\b([A-Z][0-9]{7})\b", text)
    return m.group(1) if m else None


def _extract_mrz(text: str):
    lines = [l.strip() for l in text.splitlines() if len(l.strip()) >= 40]
    mrz = [l for l in lines if re.match(r"[A-Z0-9<]{40,}", l)]
    return mrz[0] if len(mrz) > 0 else None, mrz[1] if len(mrz) > 1 else None


# ── Main dispatcher ───────────────────────────────────────────────────────────

def run_extraction(state: VerificationState) -> VerificationState:
    logger.info(f"[EXTRACT] Request {state['request_id']}, type={state.get('document_type')}")
    text = state.get("ocr_raw_text", "") or ""
    doc_type = state.get("document_type")
    fields: ExtractedFields = {"raw_text": text}
    hit_count = 0
    total_fields = 0

    if doc_type == DocumentType.AADHAAR:
        candidates = {
            "aadhaar_number": _extract_aadhaar_number(text),
            "name": _extract_name_aadhaar(text),
            "dob": _extract_dob(text),
            "gender": _extract_gender(text),
            "pincode": _extract_pincode(text),
        }
        total_fields = len(candidates)
        for k, v in candidates.items():
            fields[k] = v
            if v:
                hit_count += 1

    elif doc_type == DocumentType.PAN:
        candidates = {
            "pan_number": _extract_pan_number(text),
            "name": _extract_name_aadhaar(text),
            "dob": _extract_dob(text),
        }
        total_fields = len(candidates)
        for k, v in candidates.items():
            fields[k] = v
            if v:
                hit_count += 1

    elif doc_type == DocumentType.PASSPORT:
        mrz1, mrz2 = _extract_mrz(text)
        candidates = {
            "passport_number": _extract_passport_number(text),
            "name": _extract_name_aadhaar(text),
            "dob": _extract_dob(text),
            "mrz_line1": mrz1,
            "mrz_line2": mrz2,
        }
        total_fields = len(candidates)
        for k, v in candidates.items():
            fields[k] = v
            if v:
                hit_count += 1
    else:
        fields["name"] = _extract_name_aadhaar(text)
        fields["dob"] = _extract_dob(text)
        total_fields = 2
        hit_count = sum(1 for v in [fields.get("name"), fields.get("dob")] if v)

    confidence = hit_count / total_fields if total_fields else 0.0
    state["extracted_fields"] = fields
    state["extraction_confidence"] = round(confidence, 3)
    logger.info(f"[EXTRACT] {hit_count}/{total_fields} fields. Confidence={confidence:.2f}")
    return state

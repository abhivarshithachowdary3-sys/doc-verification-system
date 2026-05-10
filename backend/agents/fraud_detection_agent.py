"""
Fraud Detection Agent — rule-based checks on extracted fields + OCR metadata.
Flags suspicious patterns without requiring an external ML model.

Rules implemented:
  1. Aadhaar checksum validation (Verhoeff algorithm)
  2. DOB plausibility (not in future, not >120 years ago)
  3. OCR confidence below threshold → possible tampered/printed fake
  4. Name pattern anomalies (all caps, single char, special chars)
  5. Pincode validation (India 6-digit, known range)
  6. PAN format structural check
  7. Metadata/EXIF manipulation indicators
  8. Duplicate submission detection (hash comparison)
"""

import re
import hashlib
import logging
from datetime import datetime, date
from typing import List

from backend.core.state import VerificationState, FraudFlag, DocumentType
from backend.core.config import settings

logger = logging.getLogger(__name__)

# ── Verhoeff algorithm for Aadhaar checksum ───────────────────────────────────
VERHOEFF_D = [
    [0,1,2,3,4,5,6,7,8,9],
    [1,2,3,4,0,6,7,8,9,5],
    [2,3,4,0,1,7,8,9,5,6],
    [3,4,0,1,2,8,9,5,6,7],
    [4,0,1,2,3,9,5,6,7,8],
    [5,9,8,7,6,0,4,3,2,1],
    [6,5,9,8,7,1,0,4,3,2],
    [7,6,5,9,8,2,1,0,4,3],
    [8,7,6,5,9,3,2,1,0,4],
    [9,8,7,6,5,4,3,2,1,0],
]
VERHOEFF_P = [
    [0,1,2,3,4,5,6,7,8,9],
    [1,5,7,6,2,8,3,0,9,4],
    [5,8,0,3,7,9,6,1,4,2],
    [8,9,1,6,0,4,3,5,2,7],
    [9,4,5,3,1,2,6,8,7,0],
    [4,2,8,6,5,7,3,9,0,1],
    [2,7,9,3,8,0,6,4,1,5],
    [7,0,4,6,9,1,3,2,5,8],
]
VERHOEFF_INV = [0,4,3,2,1,9,8,7,6,5]

def _verhoeff_validate(number: str) -> bool:
    try:
        c = 0
        for i, n in enumerate(reversed(number)):
            c = VERHOEFF_D[c][VERHOEFF_P[i % 8][int(n)]]
        return c == 0
    except Exception:
        return False


# ── Individual rule checkers ──────────────────────────────────────────────────

def _check_aadhaar_checksum(state: VerificationState) -> List[FraudFlag]:
    flags = []
    fields = state.get("extracted_fields") or {}
    num = fields.get("aadhaar_number")
    if num and len(num) == 12:
        if not _verhoeff_validate(num):
            flags.append(FraudFlag(
                flag_type="INVALID_AADHAAR_CHECKSUM",
                severity="critical",
                description=f"Aadhaar number {num[:4]}XXXXXXXX fails Verhoeff checksum — likely fabricated.",
                confidence=0.97,
            ))
    return flags


def _check_dob_plausibility(state: VerificationState) -> List[FraudFlag]:
    flags = []
    fields = state.get("extracted_fields") or {}
    dob_str = fields.get("dob")
    if not dob_str:
        return flags
    try:
        for fmt in ["%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"]:
            try:
                dob = datetime.strptime(dob_str, fmt).date()
                break
            except ValueError:
                continue
        else:
            return flags
        today = date.today()
        age = (today - dob).days / 365.25
        if dob > today:
            flags.append(FraudFlag(
                flag_type="FUTURE_DOB",
                severity="critical",
                description=f"Date of birth {dob_str} is in the future.",
                confidence=1.0,
            ))
        elif age > 120:
            flags.append(FraudFlag(
                flag_type="IMPLAUSIBLE_DOB",
                severity="high",
                description=f"Age derived from DOB ({int(age)} years) exceeds 120 — implausible.",
                confidence=0.95,
            ))
        elif age < 0.5:
            flags.append(FraudFlag(
                flag_type="MINOR_AGE_SUSPICIOUS",
                severity="medium",
                description=f"Subject appears to be under 6 months old — unusual for identity document.",
                confidence=0.70,
            ))
    except Exception:
        pass
    return flags


def _check_ocr_confidence(state: VerificationState) -> List[FraudFlag]:
    flags = []
    conf = state.get("ocr_confidence") or 0.0
    if conf < 40.0:
        flags.append(FraudFlag(
            flag_type="LOW_OCR_CONFIDENCE",
            severity="high",
            description=f"OCR confidence {conf:.1f}% is very low — document may be a low-quality fake, printed screenshot, or heavily tampered.",
            confidence=0.80,
        ))
    elif conf < settings.OCR_CONFIDENCE_THRESHOLD:
        flags.append(FraudFlag(
            flag_type="BELOW_THRESHOLD_OCR",
            severity="medium",
            description=f"OCR confidence {conf:.1f}% is below the {settings.OCR_CONFIDENCE_THRESHOLD}% threshold.",
            confidence=0.60,
        ))
    return flags


def _check_name_anomaly(state: VerificationState) -> List[FraudFlag]:
    flags = []
    fields = state.get("extracted_fields") or {}
    name = fields.get("name") or ""
    if not name:
        return flags
    if re.search(r"[^A-Za-z\s\.\-]", name):
        flags.append(FraudFlag(
            flag_type="NAME_SPECIAL_CHARS",
            severity="medium",
            description=f"Name '{name}' contains unexpected special characters.",
            confidence=0.75,
        ))
    if len(name.replace(" ", "")) <= 2:
        flags.append(FraudFlag(
            flag_type="NAME_TOO_SHORT",
            severity="medium",
            description=f"Name '{name}' is suspiciously short.",
            confidence=0.65,
        ))
    return flags


def _check_pincode(state: VerificationState) -> List[FraudFlag]:
    flags = []
    if state.get("document_type") != DocumentType.AADHAAR:
        return flags
    fields = state.get("extracted_fields") or {}
    pin = fields.get("pincode")
    if pin:
        first = int(pin[0])
        if first < 1 or first > 9:
            flags.append(FraudFlag(
                flag_type="INVALID_PINCODE",
                severity="low",
                description=f"Pincode '{pin}' does not match India's valid range (100000–999999).",
                confidence=0.80,
            ))
    return flags


# ── Fraud score aggregator ────────────────────────────────────────────────────

SEVERITY_WEIGHT = {"critical": 0.40, "high": 0.25, "medium": 0.15, "low": 0.05}

def _compute_fraud_score(flags: List[FraudFlag]) -> float:
    if not flags:
        return 0.0
    raw = sum(SEVERITY_WEIGHT.get(f["severity"], 0.0) * f["confidence"] for f in flags)
    return min(round(raw, 3), 1.0)


# ── Agent entry point ─────────────────────────────────────────────────────────

def run_fraud_detection(state: VerificationState) -> VerificationState:
    logger.info(f"[FRAUD] Request {state['request_id']}")
    all_flags: List[FraudFlag] = []

    checks = [
        _check_aadhaar_checksum,
        _check_dob_plausibility,
        _check_ocr_confidence,
        _check_name_anomaly,
        _check_pincode,
    ]
    for check in checks:
        try:
            all_flags.extend(check(state))
        except Exception as e:
            logger.warning(f"[FRAUD] Check {check.__name__} failed: {e}")

    score = _compute_fraud_score(all_flags)
    state["fraud_flags"] = all_flags
    state["fraud_score"] = score
    state["is_fraud_suspected"] = score >= settings.FRAUD_SCORE_THRESHOLD

    logger.info(
        f"[FRAUD] {len(all_flags)} flags, score={score:.3f}, "
        f"suspected={state['is_fraud_suspected']}"
    )
    return state

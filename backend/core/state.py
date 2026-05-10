"""
State definitions for the LangGraph verification workflow.
All agent nodes read from and write to this shared state object.
"""

from typing import TypedDict, Optional, List, Dict, Any
from enum import Enum


class DocumentType(str, Enum):
    AADHAAR = "aadhaar"
    PAN = "pan"
    PASSPORT = "passport"
    DRIVING_LICENSE = "driving_license"
    VOTER_ID = "voter_id"
    UNKNOWN = "unknown"


class VerificationStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    VERIFIED = "verified"
    FAILED = "failed"
    FRAUD_SUSPECTED = "fraud_suspected"
    MANUAL_REVIEW = "manual_review"


class FraudFlag(TypedDict):
    flag_type: str
    severity: str          # low | medium | high | critical
    description: str
    confidence: float


class ExtractedFields(TypedDict, total=False):
    # Aadhaar specific
    aadhaar_number: Optional[str]
    name: Optional[str]
    dob: Optional[str]
    gender: Optional[str]
    address: Optional[str]
    pincode: Optional[str]
    uid_masked: Optional[str]
    # PAN specific
    pan_number: Optional[str]
    father_name: Optional[str]
    # Passport specific
    passport_number: Optional[str]
    nationality: Optional[str]
    expiry_date: Optional[str]
    mrz_line1: Optional[str]
    mrz_line2: Optional[str]
    # Generic
    raw_text: Optional[str]


class VerificationState(TypedDict):
    # Input
    request_id: str
    image_path: str
    image_base64: Optional[str]

    # OCR stage
    ocr_raw_text: Optional[str]
    ocr_confidence: Optional[float]
    ocr_completed: bool

    # Classification stage
    document_type: Optional[DocumentType]
    classification_confidence: Optional[float]

    # Extraction stage
    extracted_fields: Optional[ExtractedFields]
    extraction_confidence: Optional[float]

    # Fraud detection stage
    fraud_flags: List[FraudFlag]
    fraud_score: Optional[float]        # 0.0 (clean) to 1.0 (certain fraud)
    is_fraud_suspected: bool

    # External verification
    external_verified: Optional[bool]
    external_provider: Optional[str]
    external_response: Optional[Dict[str, Any]]

    # Blockchain
    document_hash: Optional[str]
    blockchain_tx_hash: Optional[str]
    blockchain_anchored: bool

    # Final report
    verification_status: VerificationStatus
    verification_score: Optional[float]  # 0.0 – 1.0 overall confidence
    report: Optional[Dict[str, Any]]
    errors: List[str]
    processing_time_ms: Optional[float]

    # Metadata
    created_at: Optional[str]
    updated_at: Optional[str]

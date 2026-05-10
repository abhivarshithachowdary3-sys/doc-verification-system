"""
LangGraph orchestration graph for the full document verification pipeline.

Flow:
  START
    └─► ocr_node
          └─► classification_node
                └─► extraction_node
                      └─► fraud_detection_node
                            ├─► (fraud_suspected) ──► report_node ──► END
                            └─► external_verification_node
                                  └─► blockchain_node
                                        └─► report_node
                                              └─► END
"""

import time
import uuid
from datetime import datetime, timezone

from langgraph.graph import StateGraph, END

from backend.core.state import VerificationState, VerificationStatus
from backend.agents.ocr_agent import run_ocr
from backend.agents.classification_agent import run_classification
from backend.agents.extraction_agent import run_extraction
from backend.agents.fraud_detection_agent import run_fraud_detection
from backend.agents.external_verification_agent import run_external_verification
from backend.agents.report_agent import run_report
from backend.blockchain.verifier import anchor_to_blockchain


# ── Node wrappers ─────────────────────────────────────────────────────────────

def ocr_node(state: VerificationState) -> VerificationState:
    return run_ocr(state)


def classification_node(state: VerificationState) -> VerificationState:
    return run_classification(state)


def extraction_node(state: VerificationState) -> VerificationState:
    return run_extraction(state)


def fraud_detection_node(state: VerificationState) -> VerificationState:
    return run_fraud_detection(state)


def external_verification_node(state: VerificationState) -> VerificationState:
    return run_external_verification(state)


def blockchain_node(state: VerificationState) -> VerificationState:
    return anchor_to_blockchain(state)


def report_node(state: VerificationState) -> VerificationState:
    return run_report(state)


# ── Conditional routing ───────────────────────────────────────────────────────

def route_after_fraud(state: VerificationState) -> str:
    """Skip external verification if fraud is detected — go straight to report."""
    if state.get("is_fraud_suspected"):
        return "report"
    return "external_verification"


def route_after_ocr(state: VerificationState) -> str:
    """If OCR fails completely, short-circuit to report with error."""
    if not state.get("ocr_completed") or not state.get("ocr_raw_text"):
        return "report"
    return "classification"


# ── Build graph ───────────────────────────────────────────────────────────────

def build_verification_graph() -> StateGraph:
    graph = StateGraph(VerificationState)

    # Register nodes
    graph.add_node("ocr", ocr_node)
    graph.add_node("classification", classification_node)
    graph.add_node("extraction", extraction_node)
    graph.add_node("fraud_detection", fraud_detection_node)
    graph.add_node("external_verification", external_verification_node)
    graph.add_node("blockchain", blockchain_node)
    graph.add_node("report", report_node)

    # Set entry point
    graph.set_entry_point("ocr")

    # Edges
    graph.add_conditional_edges("ocr", route_after_ocr, {
        "classification": "classification",
        "report": "report",
    })
    graph.add_edge("classification", "extraction")
    graph.add_edge("extraction", "fraud_detection")
    graph.add_conditional_edges("fraud_detection", route_after_fraud, {
        "report": "report",
        "external_verification": "external_verification",
    })
    graph.add_edge("external_verification", "blockchain")
    graph.add_edge("blockchain", "report")
    graph.add_edge("report", END)

    return graph.compile()


# ── Public runner ─────────────────────────────────────────────────────────────

verification_graph = build_verification_graph()


def run_verification(image_path: str, request_id: str = None) -> VerificationState:
    """
    Execute the full verification pipeline and return the final state.
    """
    if not request_id:
        request_id = str(uuid.uuid4())

    initial_state: VerificationState = {
        "request_id": request_id,
        "image_path": image_path,
        "image_base64": None,
        "ocr_raw_text": None,
        "ocr_confidence": None,
        "ocr_completed": False,
        "document_type": None,
        "classification_confidence": None,
        "extracted_fields": None,
        "extraction_confidence": None,
        "fraud_flags": [],
        "fraud_score": None,
        "is_fraud_suspected": False,
        "external_verified": None,
        "external_provider": None,
        "external_response": None,
        "document_hash": None,
        "blockchain_tx_hash": None,
        "blockchain_anchored": False,
        "verification_status": VerificationStatus.PENDING,
        "verification_score": None,
        "report": None,
        "errors": [],
        "processing_time_ms": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": None,
    }

    start = time.perf_counter()
    final_state = verification_graph.invoke(initial_state)
    elapsed_ms = (time.perf_counter() - start) * 1000

    final_state["processing_time_ms"] = round(elapsed_ms, 2)
    final_state["updated_at"] = datetime.now(timezone.utc).isoformat()
    return final_state

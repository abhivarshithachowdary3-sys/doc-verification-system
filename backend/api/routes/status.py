"""System status endpoint — reports pipeline component availability."""
import shutil
from fastapi import APIRouter

router = APIRouter()

@router.get("/status", summary="System component status")
def system_status():
    tesseract_ok = shutil.which("tesseract") is not None
    try:
        from web3 import Web3
        web3_ok = True
    except ImportError:
        web3_ok = False
    try:
        import langgraph
        langgraph_ok = True
    except ImportError:
        langgraph_ok = False
    return {
        "tesseract_ocr": "ok" if tesseract_ok else "not_found",
        "langgraph":     "ok" if langgraph_ok else "not_installed",
        "web3":          "ok" if web3_ok else "not_installed",
    }

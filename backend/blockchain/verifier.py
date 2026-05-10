"""
Blockchain Anchoring — stores a SHA-256 hash of the verified document
on a local Hardhat/Ganache EVM chain using the CredentialRegistry contract.

Falls back gracefully to hash-only mode when Web3 is unavailable.
"""

import hashlib
import logging
from datetime import datetime, timezone
from backend.core.state import VerificationState
from backend.core.config import settings

logger = logging.getLogger(__name__)

try:
    from web3 import Web3
    WEB3_AVAILABLE = True
except ImportError:
    WEB3_AVAILABLE = False
    logger.warning("[BLOCKCHAIN] web3 not installed — running in hash-only mode")

# Minimal ABI for CredentialRegistry.sol
REGISTRY_ABI = [
    {
        "inputs": [{"name": "docHash", "type": "bytes32"}],
        "name": "register",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"name": "docHash", "type": "bytes32"}],
        "name": "isRegistered",
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function",
    },
]


def _compute_document_hash(state: VerificationState) -> str:
    fields = state.get("extracted_fields") or {}
    payload = "|".join([
        state.get("request_id", ""),
        str(fields.get("aadhaar_number") or fields.get("pan_number") or fields.get("passport_number") or ""),
        str(fields.get("name", "")),
        str(fields.get("dob", "")),
        state.get("created_at", ""),
    ])
    return hashlib.sha256(payload.encode()).hexdigest()


def anchor_to_blockchain(state: VerificationState) -> VerificationState:
    logger.info(f"[BLOCKCHAIN] Anchoring request {state['request_id']}")

    doc_hash = state.get("document_hash") or _compute_document_hash(state)
    state["document_hash"] = doc_hash

    if not WEB3_AVAILABLE or not settings.CONTRACT_ADDRESS or not settings.DEPLOYER_PRIVATE_KEY:
        logger.info("[BLOCKCHAIN] Skipping on-chain write — hash-only mode")
        state["blockchain_anchored"] = False
        state["blockchain_tx_hash"] = f"HASH_ONLY:{doc_hash}"
        return state

    try:
        w3 = Web3(Web3.HTTPProvider(settings.WEB3_PROVIDER_URL))
        if not w3.is_connected():
            raise ConnectionError("Cannot connect to Web3 provider")

        contract = w3.eth.contract(
            address=Web3.to_checksum_address(settings.CONTRACT_ADDRESS),
            abi=REGISTRY_ABI,
        )
        account = w3.eth.account.from_key(settings.DEPLOYER_PRIVATE_KEY)
        hash_bytes = bytes.fromhex(doc_hash)

        # Check if already registered
        already = contract.functions.isRegistered(hash_bytes).call()
        if already:
            logger.info("[BLOCKCHAIN] Hash already registered on chain")
            state["blockchain_anchored"] = True
            state["blockchain_tx_hash"] = "ALREADY_REGISTERED"
            return state

        tx = contract.functions.register(hash_bytes).build_transaction({
            "from": account.address,
            "nonce": w3.eth.get_transaction_count(account.address),
            "gas": 200_000,
            "gasPrice": w3.eth.gas_price,
        })
        signed = w3.eth.account.sign_transaction(tx, settings.DEPLOYER_PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)

        state["blockchain_tx_hash"] = receipt.transactionHash.hex()
        state["blockchain_anchored"] = receipt.status == 1
        logger.info(f"[BLOCKCHAIN] Anchored. TX={state['blockchain_tx_hash']}")

    except Exception as e:
        logger.error(f"[BLOCKCHAIN] Failed: {e}")
        state["errors"].append(f"Blockchain error: {str(e)}")
        state["blockchain_anchored"] = False

    return state

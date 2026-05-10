"""
Deploy CredentialRegistry.sol to a local Hardhat/Ganache node.
Run: python -m backend.blockchain.deployer
"""

import json
import logging
from pathlib import Path
from backend.core.config import settings

logger = logging.getLogger(__name__)


def deploy():
    try:
        from web3 import Web3
        from solcx import compile_source, install_solc
    except ImportError:
        logger.error("Install: pip install web3 py-solc-x")
        return

    install_solc("0.8.20")

    sol_path = Path(__file__).parent / "contracts" / "CredentialRegistry.sol"
    source = sol_path.read_text()

    compiled = compile_source(source, output_values=["abi", "bin"], solc_version="0.8.20")
    contract_id = "<stdin>:CredentialRegistry"
    abi = compiled[contract_id]["abi"]
    bytecode = compiled[contract_id]["bin"]

    w3 = Web3(Web3.HTTPProvider(settings.WEB3_PROVIDER_URL))
    if not w3.is_connected():
        logger.error(f"Cannot connect to {settings.WEB3_PROVIDER_URL}")
        return

    account = w3.eth.account.from_key(settings.DEPLOYER_PRIVATE_KEY)
    Contract = w3.eth.contract(abi=abi, bytecode=bytecode)

    tx_hash = Contract.constructor().transact({"from": account.address})
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    address = receipt.contractAddress

    print(f"\n✅ CredentialRegistry deployed at: {address}")
    print(f"   Add to .env:  CONTRACT_ADDRESS={address}\n")

    # Save ABI for reuse
    abi_path = Path(__file__).parent / "contracts" / "CredentialRegistry.abi.json"
    abi_path.write_text(json.dumps(abi, indent=2))
    print(f"   ABI saved to: {abi_path}")
    return address


if __name__ == "__main__":
    deploy()

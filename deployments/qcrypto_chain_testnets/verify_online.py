#!/usr/bin/env python3
"""Verify that the observer deployment is online on the intended public testnets.

This script reads node status only. It does not access signing keys, create
transactions, broadcast value, activate validators, or mutate chain state.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from urllib.request import urlopen

from security.qcrypto.chain_online_guard import ChainOnlineEvidence, assess_chain_online

ROOT = Path(__file__).resolve().parent
COMPOSE = ROOT / "compose.observer.yaml"
ARTIFACT_DIR = ROOT / "artifacts"


def run(*args: str) -> str:
    result = subprocess.run(
        args,
        cwd=ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout.strip()


def docker_exec(service: str, *command: str) -> str:
    return run(
        "docker",
        "compose",
        "-f",
        str(COMPOSE),
        "exec",
        "-T",
        service,
        *command,
    )


def load_last_json(text: str):
    for line in reversed([line.strip() for line in text.splitlines() if line.strip()]):
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            continue
    raise RuntimeError(f"No JSON object found in command output: {text!r}")


def as_int(value) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return int(value, 0)
    raise TypeError(f"Expected integer-like value, got {value!r}")


def main() -> int:
    bitcoin_raw = docker_exec(
        "bitcoin-signet",
        "bitcoin-cli",
        "-signet",
        "getblockchaininfo",
    )
    bitcoin = json.loads(bitcoin_raw)

    geth_raw = docker_exec(
        "ethereum-execution",
        "geth",
        "attach",
        "/data/geth.ipc",
        "--exec",
        "JSON.stringify({chainId:eth.chainId.toString(),blockNumber:eth.blockNumber})",
    )
    geth = load_last_json(geth_raw)
    chain_id = as_int(geth["chainId"])
    execution_block = as_int(geth["blockNumber"])

    with urlopen("http://127.0.0.1:5052/eth/v1/node/syncing", timeout=10) as response:
        beacon = json.loads(response.read().decode("utf-8"))
    sync = beacon.get("data") or {}

    measured = ChainOnlineEvidence(
        bitcoin_reported_chain=str(bitcoin.get("chain", "")),
        bitcoin_blocks=as_int(bitcoin.get("blocks", -1)),
        bitcoin_headers=as_int(bitcoin.get("headers", -1)),
        bitcoin_verification_progress=float(bitcoin.get("verificationprogress", -1.0)),
        ethereum_chain_id=chain_id,
        ethereum_execution_block_number=execution_block,
        ethereum_consensus_head_slot=as_int(sync.get("head_slot", -1)),
        ethereum_consensus_sync_distance=as_int(sync.get("sync_distance", -1)),
        ethereum_consensus_is_syncing=bool(sync.get("is_syncing", True)),
        external_signer_boundary_defined=True,
    )
    assessment = assess_chain_online(measured)
    if not assessment.node_online_evidence_valid:
        raise RuntimeError("; ".join(assessment.blockers))

    receipt = {
        "schema": "WS-QCRYPTO-CHAIN-ONLINE-RECEIPT-V1",
        "status": assessment.state,
        "bitcoin": {
            "network": "SIGNET",
            "reported_chain": measured.bitcoin_reported_chain,
            "blocks": measured.bitcoin_blocks,
            "headers": measured.bitcoin_headers,
            "verification_progress": measured.bitcoin_verification_progress,
            "assessment": assessment.bitcoin_state,
        },
        "ethereum": {
            "network": "HOODI",
            "chain_id": measured.ethereum_chain_id,
            "execution_block_number": measured.ethereum_execution_block_number,
            "consensus_head_slot": measured.ethereum_consensus_head_slot,
            "consensus_sync_distance": measured.ethereum_consensus_sync_distance,
            "consensus_is_syncing": measured.ethereum_consensus_is_syncing,
            "assessment": assessment.ethereum_state,
        },
        "synchronized": assessment.synchronized,
        "claims": {
            "mainnet_permitted": assessment.mainnet_permitted,
            "live_value_authorized": False,
            "private_key_operations_permitted": assessment.private_key_operations_permitted,
            "bitcoin_transaction_broadcast": assessment.transaction_execution_permitted,
            "ethereum_validator_activated": assessment.validator_activation_permitted,
            "end_to_end_post_quantum_security_established": assessment.end_to_end_post_quantum_security_established,
        },
        "warnings": list(assessment.warnings),
    }

    ARTIFACT_DIR.mkdir(exist_ok=True)
    output = ARTIFACT_DIR / "qcrypto_chain_online_receipt.json"
    output.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"CHAIN_ONLINE_VERIFICATION_FAILED: {exc}", file=sys.stderr)
        raise

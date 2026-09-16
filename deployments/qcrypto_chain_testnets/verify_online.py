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


def main() -> int:
    bitcoin_raw = docker_exec(
        "bitcoin-signet",
        "bitcoin-cli",
        "-signet",
        "getblockchaininfo",
    )
    bitcoin = json.loads(bitcoin_raw)
    if bitcoin.get("chain") != "signet":
        raise RuntimeError(f"Bitcoin chain identity mismatch: {bitcoin.get('chain')!r}")

    geth_raw = docker_exec(
        "ethereum-execution",
        "geth",
        "attach",
        "/data/geth.ipc",
        "--exec",
        "JSON.stringify({chainId:eth.chainId.toString(),blockNumber:eth.blockNumber})",
    )
    geth = load_last_json(geth_raw)
    chain_id = int(geth["chainId"], 0) if isinstance(geth["chainId"], str) else int(geth["chainId"])
    if chain_id != 560048:
        raise RuntimeError(f"Ethereum chain identity mismatch: {chain_id}")

    with urlopen("http://127.0.0.1:5052/eth/v1/node/syncing", timeout=10) as response:
        beacon = json.loads(response.read().decode("utf-8"))
    sync = beacon.get("data") or {}

    receipt = {
        "schema": "WS-QCRYPTO-CHAIN-ONLINE-RECEIPT-V1",
        "status": "NODE_ONLINE_EVIDENCE_CAPTURED",
        "bitcoin": {
            "network": "SIGNET",
            "reported_chain": bitcoin.get("chain"),
            "blocks": bitcoin.get("blocks"),
            "headers": bitcoin.get("headers"),
            "verification_progress": bitcoin.get("verificationprogress"),
        },
        "ethereum": {
            "network": "HOODI",
            "chain_id": chain_id,
            "execution_block_number": geth.get("blockNumber"),
            "consensus_head_slot": sync.get("head_slot"),
            "consensus_sync_distance": sync.get("sync_distance"),
            "consensus_is_syncing": sync.get("is_syncing"),
        },
        "claims": {
            "mainnet_permitted": False,
            "live_value_authorized": False,
            "private_key_operations_permitted": False,
            "bitcoin_transaction_broadcast": False,
            "ethereum_validator_activated": False,
            "end_to_end_post_quantum_security_established": False,
        },
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

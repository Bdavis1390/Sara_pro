#!/usr/bin/env python3
"""Verify that the observer deployment is online on the intended public testnets.

This script reads node status only. It does not access signing keys, create
transactions, broadcast value, activate validators, or mutate chain state.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from security.qcrypto.chain_online_guard import ChainOnlineEvidence, assess_chain_online

COMPOSE = ROOT / "compose.observer.yaml"
ARTIFACT_DIR = ROOT / "artifacts"
START_RECEIPT = ARTIFACT_DIR / "qcrypto_chain_start_receipt.json"
CHECKPOINT_RECEIPT = ARTIFACT_DIR / "qcrypto_hoodi_checkpoint_quorum.json"
HOODI_NETWORK_ID = 560048
HOODI_GENESIS_HASH = "0xbbe312868b376a3001692a646dd2d7d1e4406380dfd86b98aa8a34d1557c971b"


def run(*args: str, cwd: Path | None = None) -> str:
    result = subprocess.run(
        args,
        cwd=cwd or ROOT,
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


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_geth_protocol_snapshot(text: str) -> tuple[int, str, int]:
    """Parse and fail-closed validate Geth's running eth protocol NodeInfo snapshot."""
    payload = load_last_json(text)
    try:
        network_id = as_int(payload["network"])
        genesis_hash = str(payload["genesis"]).lower()
        execution_block = as_int(payload["blockNumber"])
    except (KeyError, TypeError, ValueError) as exc:
        raise RuntimeError(f"Incomplete Geth protocol NodeInfo snapshot: {exc}") from exc

    if network_id != HOODI_NETWORK_ID:
        raise RuntimeError(f"Geth network id mismatch: {network_id}")
    if genesis_hash != HOODI_GENESIS_HASH:
        raise RuntimeError(f"Geth Hoodi genesis hash mismatch: {genesis_hash}")
    if execution_block < 0:
        raise RuntimeError("Geth execution block number must be non-negative")
    return network_id, genesis_hash, execution_block


def load_and_verify_start_receipt() -> dict:
    if not START_RECEIPT.is_file():
        raise RuntimeError("Start receipt is missing; run bootstrap_host.sh before online verification")
    start = json.loads(START_RECEIPT.read_text(encoding="utf-8"))
    if start.get("schema") != "WS-QCRYPTO-CHAIN-START-RECEIPT-V3":
        raise RuntimeError("Unsupported or missing chain start receipt schema")

    current_revision = run("git", "rev-parse", "HEAD", cwd=REPO_ROOT)
    if start.get("deployment_revision") != current_revision:
        raise RuntimeError("Repository revision changed after node start; deployment lineage is stale")

    compose_sha256 = hashlib.sha256(COMPOSE.read_bytes()).hexdigest()
    if start.get("compose_sha256") != compose_sha256:
        raise RuntimeError("Compose bytes changed after node start; deployment lineage is stale")

    images = start.get("images") or {}
    for key in ("bitcoin_core", "ethereum_execution", "ethereum_consensus"):
        value = images.get(key)
        if not isinstance(value, str) or "@sha256:" not in value:
            raise RuntimeError(f"Start receipt lacks immutable image digest for {key}")

    bootstrap = start.get("hoodi_checkpoint_bootstrap") or {}
    if bootstrap.get("consensus_verification_replaced") is not False:
        raise RuntimeError("Checkpoint bootstrap must not claim to replace Ethereum consensus verification")
    if not CHECKPOINT_RECEIPT.is_file():
        raise RuntimeError("Hoodi checkpoint quorum receipt is missing")
    expected_quorum_sha = bootstrap.get("quorum_receipt_sha256")
    if not isinstance(expected_quorum_sha, str) or len(expected_quorum_sha) != 64:
        raise RuntimeError("Start receipt lacks Hoodi checkpoint quorum receipt digest")
    if sha256_file(CHECKPOINT_RECEIPT) != expected_quorum_sha:
        raise RuntimeError("Hoodi checkpoint quorum receipt changed after node start")

    quorum = json.loads(CHECKPOINT_RECEIPT.read_text(encoding="utf-8"))
    if quorum.get("schema") != "WS-QCRYPTO-HOODI-CHECKPOINT-QUORUM-V1":
        raise RuntimeError("Unsupported Hoodi checkpoint quorum receipt schema")
    if quorum.get("state") != "HOODI_CHECKPOINT_QUORUM_ACCEPTED" or quorum.get("accepted") is not True:
        raise RuntimeError("Hoodi checkpoint quorum receipt is not accepted")
    if quorum.get("consensus_verification_replaced") is not False:
        raise RuntimeError("Checkpoint quorum receipt improperly replaces consensus verification")
    if quorum.get("quorum_root") != bootstrap.get("quorum_root"):
        raise RuntimeError("Hoodi finalized-root quorum changed after node start")
    if quorum.get("configured_url", "").rstrip("/") != str(bootstrap.get("configured_url", "")).rstrip("/"):
        raise RuntimeError("Hoodi configured checkpoint provider changed after node start")
    if sorted(quorum.get("agreeing_providers") or []) != sorted(bootstrap.get("agreeing_providers") or []):
        raise RuntimeError("Hoodi checkpoint quorum provider set changed after node start")

    claims = start.get("claims") or {}
    for key in (
        "mainnet_permitted",
        "live_value_authorized",
        "private_key_operations_permitted",
        "bitcoin_transaction_broadcast",
        "ethereum_validator_activated",
        "end_to_end_post_quantum_security_established",
    ):
        if claims.get(key) is not False:
            raise RuntimeError(f"Start receipt violates required negative claim: {key}")
    return start


def main() -> int:
    start = load_and_verify_start_receipt()

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
        "JSON.stringify({network:admin.nodeInfo.protocols.eth.network,genesis:admin.nodeInfo.protocols.eth.genesis,blockNumber:eth.blockNumber})",
    )
    network_id, genesis_hash, execution_block = parse_geth_protocol_snapshot(geth_raw)
    chain_id = HOODI_NETWORK_ID

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
        "schema": "WS-QCRYPTO-CHAIN-ONLINE-RECEIPT-V3",
        "status": assessment.state,
        "lineage": {
            "deployment_revision": start["deployment_revision"],
            "compose_sha256": start["compose_sha256"],
            "images": start["images"],
            "start_receipt_schema": start["schema"],
            "hoodi_checkpoint_bootstrap": start["hoodi_checkpoint_bootstrap"],
        },
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
            "network_id": network_id,
            "genesis_hash": genesis_hash,
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

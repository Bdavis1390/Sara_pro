"""Opt-in, synthetic-only PRIME verify/reserve/execute reference controller.

Reads configuration/input bytes ONCE, verifies a narrowly scoped external PRIME
signature against those exact bytes, atomically reserves a local grant, and
executes ONLY the fixed affine toy calculation on those same byte objects.

Not integrated with SARA, not a privileged execution sandbox, not a physical
experiment, and not independently witnessed or preregistered.
"""
from __future__ import annotations

import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from worldshepherd_sara.prime_sentinel_authorization import PrimeSentinelVerifier

import bounded_execution
from bounded_execution import (
    ExecutionCustodyError, calculated_output, canonical, read_bounded,
    receipt_digest, sha256, verify_receipt,
)
from local_grant_ledger import LocalGrantLedger
from scientific_prime_authorization import canonical_scientific_authorization
from scientific_prime_reservation import verify_and_reserve_science_grant

CONTROLLER_SCHEMA = "WS-PRIME-SYNTHETIC-LOCAL-EXECUTION-V1"


class AuthorizedSyntheticExecutionError(ValueError):
    pass


def _validate_output_destination(root: Path, run_id: str) -> Path:
    """Reject unsafe paths before reserving a grant; exclusive writes after."""
    base = root.resolve(strict=True)
    directory = base / "runs"
    if directory.is_symlink():
        raise AuthorizedSyntheticExecutionError("run directory must not be symlinked")
    if directory.exists() and not directory.is_dir():
        raise AuthorizedSyntheticExecutionError("run directory is not a directory")
    for suffix in ("output.json", "receipt.json"):
        path = directory / f"{run_id}.{suffix}"
        if path.exists() or path.is_symlink():
            raise AuthorizedSyntheticExecutionError("run output identity already exists")
    return directory


def execute_authorized_synthetic(
    root: str | Path,
    assertion: dict[str, Any],
    *,
    config_path: str,
    input_path: str,
    ledger: LocalGrantLedger,
    prime_verifier: PrimeSentinelVerifier,
    expected_claim_id: str,
    expected_prereg_sha256: str,
    expected_signer_key_fingerprint_sha256: str,
) -> dict[str, Any]:
    """Perform a fixed synthetic transform only after verified reservation.

    Verification uses the host's current clock; callers cannot override
    authorization time through this entrypoint. The clock is NOT independently
    attested. This function has no arbitrary command or module loading.
    The caller must protect the local filesystem from mutation.
    """
    if not isinstance(assertion, dict):
        raise AuthorizedSyntheticExecutionError("signed grant required")
    run_id = assertion.get("run_id")
    if not isinstance(run_id, str) or bounded_execution.RUN_PATTERN.fullmatch(run_id) is None:
        raise AuthorizedSyntheticExecutionError("invalid run ID")
    root = Path(root)
    config_raw = read_bounded(root, config_path)
    input_raw = read_bounded(root, input_path)
    destination = _validate_output_destination(root, run_id)
    # This is local source-file identity, NOT measured/attested executable code.
    source_raw = Path(bounded_execution.__file__).read_bytes()
    source_digest = sha256(source_raw)

    # Verification uses the exact in-memory bytes later passed to calculation.
    # No computation, output, or grant consumption occurs before validation.
    reserved = verify_and_reserve_science_grant(
        assertion,
        ledger=ledger,
        prime_verifier=prime_verifier,
        expected_claim_id=expected_claim_id,
        expected_prereg_sha256=expected_prereg_sha256,
        expected_run_id=run_id,
        expected_config_bytes=config_raw,
        expected_input_bytes=input_raw,
        expected_executor_sha256=source_digest,
        expected_signer_key_fingerprint_sha256=expected_signer_key_fingerprint_sha256,
    )
    # From this point, any exception deliberately leaves the grant RESERVED.
    output_raw = calculated_output(config_raw, input_raw)
    destination.mkdir(mode=0o700, exist_ok=True)
    if destination.is_symlink():
        raise AuthorizedSyntheticExecutionError("run directory changed to symlink")
    receipt = {
        "schema": bounded_execution.RECEIPT_SCHEMA,
        "run_id": run_id,
        "engine": bounded_execution.ENGINE_ID,
        "configuration": {"path": config_path, "sha256": sha256(config_raw)},
        "input": {"path": input_path, "sha256": sha256(input_raw)},
        "output": {"path": f"runs/{run_id}.output.json", "sha256": sha256(output_raw)},
        "source_sha256": source_digest,
        "runtime": {"python": list(sys.version_info[:3])},
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "self_reported": True,
        "independent_witness": False,
        "authorization": {
            "authorization_id": reserved["authorization"]["authorization_id"],
            "grant_sha256": hashlib.sha256(canonical_scientific_authorization(assertion)).hexdigest(),
            "prime_signature_verified": True,
            "local_reservation_committed": True,
            "scope": reserved["authorization"]["scope"],
            "prereg_sha256": reserved["authorization"]["prereg_sha256"],
            "nonce": reserved["authorization"]["nonce"],
            "key_fingerprint_sha256": reserved["authorization"]["key_fingerprint_sha256"],
        },
    }
    receipt["receipt_sha256"] = receipt_digest(receipt)
    # Exclusive writes never overwrite earlier evidence. Interrupted writing can
    # leave a partial file; no automatic rollback or retry is permitted.
    with (destination / f"{run_id}.output.json").open("xb") as handle:
        handle.write(output_raw)
        handle.flush()
    with (destination / f"{run_id}.receipt.json").open("xb") as handle:
        handle.write(canonical(receipt) + b"\n")
        handle.flush()
    checked = verify_receipt(root, receipt)
    if checked["status"] != "PASS":
        raise ExecutionCustodyError("local receipt verification failed")
    ledger.mark_finished(reserved["authorization"]["authorization_id"])
    return {
        "schema": CONTROLLER_SCHEMA,
        "status": "PASS",
        "authorization_id": reserved["authorization"]["authorization_id"],
        "run_id": run_id,
        "receipt": receipt,
        "output": bounded_execution.parse_object(output_raw),
        "prime_signature_verified_for_this_run": True,
        "grant_consumed_in_local_ledger": True,
        "bounded_synthetic_execution_performed": True,
        "independent_preexecution_freeze_verified": False,
        "independent_process_attestation_verified": False,
        "echo_checkpoint_witness_verified": False,
        "external_timestamp_verified": False,
        "scientific_claim_proven": False,
        "claims_boundary": (
            "A local program verified a scoped PRIME-signed synthetic grant, "
            "reserved it once, and ran its deterministic affine calculation "
            "on the same bytes. No protected SARA service, independently "
            "attested runtime, independent pre-run freeze, external witness, "
            "rollback resistance, instrument validation or science proof."
        ),
    }

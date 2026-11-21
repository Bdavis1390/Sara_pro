"""Verify a PRIME-scoped synthetic grant and reserve it in one bounded API.

Verification and durable local reservation are connected; execution is NEVER
invoked. This is a single-host software reference, not a trusted controller.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from worldshepherd_sara.prime_sentinel_authorization import PrimeSentinelVerifier
from local_grant_ledger import LocalGrantLedger
from scientific_prime_authorization import verify_scientific_authorization


def verify_and_reserve_science_grant(
    assertion: dict[str, Any],
    *,
    ledger: LocalGrantLedger,
    prime_verifier: PrimeSentinelVerifier,
    expected_claim_id: str,
    expected_prereg_sha256: str,
    expected_run_id: str,
    expected_config_bytes: bytes,
    expected_input_bytes: bytes,
    expected_executor_sha256: str,
    expected_signer_key_fingerprint_sha256: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Fail closed on unsigned, expired, mismatched or already-reserved grants.

    This method does not verify an independently timestamped preregistration,
    does not identify trusted local execution hardware and does not authorize
    arbitrary shell commands or perform any computation.
    """
    if not isinstance(ledger, LocalGrantLedger):
        raise TypeError("local grant ledger required")
    verified = verify_scientific_authorization(
        assertion,
        prime_verifier=prime_verifier,
        expected_claim_id=expected_claim_id,
        expected_prereg_sha256=expected_prereg_sha256,
        expected_run_id=expected_run_id,
        expected_config_bytes=expected_config_bytes,
        expected_input_bytes=expected_input_bytes,
        expected_executor_sha256=expected_executor_sha256,
        expected_signer_key_fingerprint_sha256=expected_signer_key_fingerprint_sha256,
        now=now,
    )
    reserved = ledger.reserve(verified)
    return {
        "schema": "WS-SCIENTIFIC-PRIME-VERIFY-RESERVE-RESULT-V1",
        "status": "PASS",
        "authorization": verified,
        "reservation": reserved,
        "local_reservation_committed": True,
        "execution_performed": False,
        "independent_prereg_anchor_verified": False,
        "distributed_replay_protected": False,
        "scientific_claim_proven": False,
    }

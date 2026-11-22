"""PRIME-scoped *candidate* scientific execution authorization verifier.

Verifies an externally signed, domain-separated synthetic-operation grant using
the canonical PRIME public-key verifier. Does NOT issue grants or execute work.
No durable replay ledger, independently timestamped preregistration, or deployed
SARA/PRIME workflow is supplied by this reference.
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timedelta, timezone
from typing import Any

from worldshepherd_sara.prime_sentinel_authorization import (
    PrimeSentinelAuthorizationError,
    PrimeSentinelVerifier,
)
from bounded_execution import canonical, parse_object

SCHEMA = "WS-PRIME-SCIENTIFIC-EXECUTION-AUTHZ-V1"
ACTION = "SCIENTIFIC_EXECUTION_SYNTHETIC"
SCOPE = "LOCAL_AFFINE_SYNTHETIC_ONLY"
SIGNING_DOMAIN = b"WS-PRIME-SCIENTIFIC-EXECUTION-AUTHZ-V1\0"
MAX_LIFETIME = timedelta(minutes=15)
FUTURE_SKEW = timedelta(seconds=60)
SHA = re.compile(r"[0-9a-f]{64}\Z")
IDENT = re.compile(r"[A-Za-z0-9_.:-]{1,128}\Z")
RUN_ID = re.compile(r"[A-Za-z0-9_-]{1,64}\Z")
NONCE = re.compile(r"[A-Za-z0-9_-]{16,128}\Z")
FIELDS = frozenset({
    "schema", "issuer", "action", "scope", "key_id", "authorization_id",
    "nonce", "claim_id", "prereg_sha256", "run_id", "config_sha256",
    "input_sha256", "executor_sha256", "max_samples", "issued_at",
    "expires_at", "signature_b64url",
})


class ScientificPrimeAuthorizationError(ValueError):
    pass


def _digest(value: Any, label: str) -> str:
    if not isinstance(value, str) or SHA.fullmatch(value) is None:
        raise ScientificPrimeAuthorizationError(f"{label} must be lowercase SHA-256")
    return value


def _identifier(value: Any, label: str, pattern=IDENT) -> str:
    if not isinstance(value, str) or pattern.fullmatch(value) is None:
        raise ScientificPrimeAuthorizationError(f"invalid {label}")
    return value


def _time(value: Any, label: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ScientificPrimeAuthorizationError(f"{label} must be UTC with Z suffix")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ScientificPrimeAuthorizationError(f"invalid {label}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise ScientificPrimeAuthorizationError(f"{label} must be UTC")
    return parsed


def canonical_scientific_authorization(assertion: dict[str, Any]) -> bytes:
    """Exact signed message; signature field excluded and schema is isolated."""
    if not isinstance(assertion, dict) or set(assertion) != FIELDS:
        raise ScientificPrimeAuthorizationError("authorization shape mismatch")
    payload = {key: val for key, val in assertion.items() if key != "signature_b64url"}
    return SIGNING_DOMAIN + canonical(payload)


def verify_scientific_authorization(
    assertion: dict[str, Any],
    *,
    prime_verifier: PrimeSentinelVerifier,
    expected_claim_id: str,
    expected_prereg_sha256: str,
    expected_run_id: str,
    expected_config_bytes: bytes,
    expected_input_bytes: bytes,
    expected_executor_sha256: str,
    expected_signer_key_fingerprint_sha256: str,
    now: datetime | None = None,
    consumed_authorization_ids: set[str] | None = None,
    consumed_nonces: set[str] | None = None,
) -> dict[str, Any]:
    """Verify exact scope of signed grant *before* a proposed bounded execution.

    An owner-controlled durable reservation/consumption ledger is REQUIRED for
    actual anti-replay; the optional sets allow negative tests only. This
    verifier deliberately does not mutate external state or execute the run.
    """
    signed_bytes = canonical_scientific_authorization(assertion)
    for field, constant in (
        ("schema", SCHEMA),
        ("issuer", "PRIME_SENTINEL"),
        ("action", ACTION),
        ("scope", SCOPE),
    ):
        if assertion.get(field) != constant:
            raise ScientificPrimeAuthorizationError(f"{field} not allowed")
    for field in ("key_id", "authorization_id", "claim_id"):
        _identifier(assertion.get(field), field)
    _identifier(assertion.get("run_id"), "run_id", RUN_ID)
    _identifier(assertion.get("nonce"), "nonce", NONCE)
    for field in ("prereg_sha256", "config_sha256", "input_sha256", "executor_sha256"):
        _digest(assertion.get(field), field)
    _digest(expected_prereg_sha256, "expected preregistration")
    _digest(expected_executor_sha256, "expected executor")
    _digest(expected_signer_key_fingerprint_sha256, "trusted signing key")

    max_samples = assertion.get("max_samples")
    if type(max_samples) is not int or not 1 <= max_samples <= 128:
        raise ScientificPrimeAuthorizationError("max_samples out of allowed range")
    issued = _time(assertion.get("issued_at"), "issued_at")
    expires = _time(assertion.get("expires_at"), "expires_at")
    if expires <= issued or expires - issued > MAX_LIFETIME:
        raise ScientificPrimeAuthorizationError("authorization duration invalid")
    current = now or datetime.now(timezone.utc)
    if not isinstance(current, datetime) or current.tzinfo is None:
        raise ScientificPrimeAuthorizationError("verification clock must be timezone-aware")
    current = current.astimezone(timezone.utc)
    if issued > current + FUTURE_SKEW or current >= expires:
        raise ScientificPrimeAuthorizationError("authorization not currently valid")
    if (assertion["claim_id"] != expected_claim_id
            or assertion["prereg_sha256"] != expected_prereg_sha256
            or assertion["run_id"] != expected_run_id):
        raise ScientificPrimeAuthorizationError("claim, freeze or run binding mismatch")
    if not isinstance(expected_config_bytes, bytes) or not isinstance(expected_input_bytes, bytes):
        raise ScientificPrimeAuthorizationError("expected input bytes required")
    if assertion["config_sha256"] != hashlib.sha256(expected_config_bytes).hexdigest():
        raise ScientificPrimeAuthorizationError("configuration bytes not authorized")
    if assertion["input_sha256"] != hashlib.sha256(expected_input_bytes).hexdigest():
        raise ScientificPrimeAuthorizationError("input bytes not authorized")
    if assertion["executor_sha256"] != expected_executor_sha256:
        raise ScientificPrimeAuthorizationError("executor source not authorized")
    try:
        config, data = parse_object(expected_config_bytes), parse_object(expected_input_bytes)
    except ValueError as exc:
        raise ScientificPrimeAuthorizationError("synthetic inputs malformed") from exc
    if (set(config) != {"operation", "scale", "offset"}
            or config["operation"] != "affine_v1"
            or any(type(config[k]) is not int or abs(config[k]) > 1000 for k in ("scale", "offset"))):
        raise ScientificPrimeAuthorizationError("operation outside synthetic scope")
    if set(data) != {"samples"} or type(data["samples"]) is not list:
        raise ScientificPrimeAuthorizationError("samples outside synthetic scope")
    samples = data["samples"]
    if (not 1 <= len(samples) <= max_samples
            or any(type(v) is not int or abs(v) > 1000000 for v in samples)):
        raise ScientificPrimeAuthorizationError("sample budget or values invalid")
    if consumed_authorization_ids is not None and assertion["authorization_id"] in consumed_authorization_ids:
        raise ScientificPrimeAuthorizationError("authorization already consumed")
    if consumed_nonces is not None and assertion["nonce"] in consumed_nonces:
        raise ScientificPrimeAuthorizationError("nonce already consumed")
    if not isinstance(prime_verifier, PrimeSentinelVerifier):
        raise ScientificPrimeAuthorizationError("canonical PRIME verifier required")
    try:
        signature = prime_verifier.verify_detached_signature(
            key_id=assertion["key_id"],
            message=signed_bytes,
            signature_b64url=assertion["signature_b64url"],
        )
    except PrimeSentinelAuthorizationError as exc:
        raise ScientificPrimeAuthorizationError("PRIME signature rejected") from exc
    if signature.key_fingerprint_sha256 != expected_signer_key_fingerprint_sha256:
        raise ScientificPrimeAuthorizationError("PRIME signing key is not independently pinned")
    return {
        "schema": "WS-PRIME-SCIENTIFIC-AUTHORIZATION-VERIFICATION-V1",
        "status": "PASS",
        "authorization_id": assertion["authorization_id"],
        "nonce": assertion["nonce"],
        "run_id": expected_run_id,
        "claim_id": expected_claim_id,
        "prereg_sha256": expected_prereg_sha256,
        "config_sha256": assertion["config_sha256"],
        "input_sha256": assertion["input_sha256"],
        "executor_sha256": assertion["executor_sha256"],
        "key_fingerprint_sha256": signature.key_fingerprint_sha256,
        "scope": SCOPE,
        "max_samples": max_samples,
        "prime_signature_verified": True,
        "durable_replay_consumption_verified": False,
        "independent_prereg_freeze_verified": False,
        "authorized_run_executed": False,
        "scientific_claim_proven": False,
        "claims_boundary": (
            "Detached PRIME signature and exact synthetic-operation scope verified "
            "against caller-pinned key and raw bytes. No execution, durable replay "
            "consumption, pre-run independent freeze, protected runtime identity, "
            "external witness, or scientific validity is established."
        ),
    }

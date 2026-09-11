from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from .echo_checkpoint_verify import EchoCheckpointVerificationError, verify_bundle


ANCHOR_REQUEST_SCHEMA = "WS-ECHO-CHECKPOINT-ANCHOR-REQUEST-V1"
ANCHOR_EVIDENCE_SCHEMA = "WS-ECHO-CHECKPOINT-ANCHOR-EVIDENCE-V1"
ANCHOR_RECEIPT_SCHEMA = "WS-ECHO-CHECKPOINT-ANCHOR-RECEIPT-V1"
ANCHOR_PURPOSE = "EXTERNAL_CHECKPOINT_DIGEST_ANCHOR"
TEST_PROVIDER = "WORLDSHEPHERD_TEST_PROVIDER"
TEST_PROVIDER_MODE = "TEST_PROVIDER"
EXTERNAL_READ_BACK_MODE = "EXTERNAL_READ_BACK"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_PROVIDER = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


class EchoCheckpointAnchorError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha256_text(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise EchoCheckpointAnchorError(f"{label} must be a lowercase SHA-256 digest")
    return value


def _text(value: Any, *, label: str, maximum: int = 2048) -> str:
    if not isinstance(value, str) or not value or len(value) > maximum:
        raise EchoCheckpointAnchorError(f"{label} must be non-empty bounded text")
    return value


def _provider(value: Any) -> str:
    if not isinstance(value, str) or not _PROVIDER.fullmatch(value):
        raise EchoCheckpointAnchorError("anchor provider identifier is invalid")
    return value


def _checkpoint_binding(bundle: Any, expected_fingerprint: str) -> dict[str, Any]:
    try:
        verified = verify_bundle(bundle, expected_fingerprint)
    except EchoCheckpointVerificationError as exc:
        raise EchoCheckpointAnchorError(str(exc)) from exc
    return {
        "checkpoint_sequence": verified["sequence"],
        "checkpoint_id": verified["checkpoint_id"],
        "checkpoint_sha256": verified["checkpoint_sha256"],
        "key_id": verified["key_id"],
        "key_fingerprint_sha256": verified["key_fingerprint_sha256"],
    }


def _anchor_payload_digest(binding: dict[str, Any]) -> str:
    return hashlib.sha256(
        b"WS-ECHO-CHECKPOINT-EXTERNAL-ANCHOR-V1\0" + _canonical(binding)
    ).hexdigest()


def build_anchor_request(bundle: Any, expected_fingerprint: str) -> dict[str, Any]:
    """Build a deterministic request for externally recording a verified checkpoint digest."""
    binding = _checkpoint_binding(bundle, expected_fingerprint)
    request = {
        "schema": ANCHOR_REQUEST_SCHEMA,
        "issuer": "ECHO_SENTINEL_LINK",
        "purpose": ANCHOR_PURPOSE,
        **binding,
        "anchor_payload_sha256": _anchor_payload_digest(binding),
        "claims_boundary": (
            "Request artifact only. Its creation does not establish external publication, "
            "immutability/WORM retention, independent third-party attestation, privileged "
            "rollback resistance, legal chain of custody, or exactly-once transport."
        ),
    }
    request["anchor_request_sha256"] = hashlib.sha256(_canonical(request)).hexdigest()
    return request


def verify_anchor_request(
    request: Any,
    bundle: Any,
    expected_fingerprint: str,
) -> dict[str, Any]:
    expected = build_anchor_request(bundle, expected_fingerprint)
    if not isinstance(request, dict) or request != expected:
        raise EchoCheckpointAnchorError("anchor request does not exactly bind the verified checkpoint")
    return expected


def build_test_anchor_evidence(
    request: dict[str, Any],
    *,
    provider_reference: str,
    observed_at: str,
) -> dict[str, Any]:
    """Build a simulated provider document for CI. This never earns external-anchor credit."""
    if request.get("schema") != ANCHOR_REQUEST_SCHEMA:
        raise EchoCheckpointAnchorError("anchor request schema mismatch")
    request_digest = _sha256_text(request.get("anchor_request_sha256"), label="anchor request digest")
    payload_digest = _sha256_text(request.get("anchor_payload_sha256"), label="anchor payload digest")
    reference = _text(provider_reference, label="provider reference")
    if not reference.startswith("test://"):
        raise EchoCheckpointAnchorError("test-provider reference must use test://")
    evidence = {
        "schema": ANCHOR_EVIDENCE_SCHEMA,
        "provider": TEST_PROVIDER,
        "provider_mode": TEST_PROVIDER_MODE,
        "provider_reference": reference,
        "observed_at": _text(observed_at, label="observed_at", maximum=128),
        "checkpoint_sequence": request.get("checkpoint_sequence"),
        "checkpoint_id": request.get("checkpoint_id"),
        "checkpoint_sha256": request.get("checkpoint_sha256"),
        "anchor_payload_sha256": payload_digest,
        "anchor_request_sha256": request_digest,
        "verification_state": "SIMULATED_ONLY",
        "claims_boundary": (
            "Synthetic CI provider evidence only; no external publication or third-party "
            "attestation is established."
        ),
    }
    evidence["evidence_sha256"] = hashlib.sha256(_canonical(evidence)).hexdigest()
    return evidence


def verify_anchor_evidence(
    evidence: Any,
    request: dict[str, Any],
    *,
    expected_provider: str,
    expected_mode: str,
) -> dict[str, Any]:
    if not isinstance(evidence, dict) or evidence.get("schema") != ANCHOR_EVIDENCE_SCHEMA:
        raise EchoCheckpointAnchorError("anchor evidence schema mismatch")
    provider = _provider(evidence.get("provider"))
    if provider != expected_provider:
        raise EchoCheckpointAnchorError("anchor evidence provider mismatch")
    mode = _text(evidence.get("provider_mode"), label="provider mode", maximum=64)
    if mode != expected_mode:
        raise EchoCheckpointAnchorError("anchor evidence provider mode mismatch")
    for field in (
        "checkpoint_sequence",
        "checkpoint_id",
        "checkpoint_sha256",
        "anchor_payload_sha256",
        "anchor_request_sha256",
    ):
        if evidence.get(field) != request.get(field):
            raise EchoCheckpointAnchorError(f"anchor evidence {field} mismatch")
    supplied_digest = _sha256_text(evidence.get("evidence_sha256"), label="anchor evidence digest")
    core = dict(evidence)
    core.pop("evidence_sha256", None)
    if hashlib.sha256(_canonical(core)).hexdigest() != supplied_digest:
        raise EchoCheckpointAnchorError("anchor evidence digest mismatch")
    _text(evidence.get("provider_reference"), label="provider reference")
    _text(evidence.get("observed_at"), label="observed_at", maximum=128)
    state = _text(evidence.get("verification_state"), label="verification state", maximum=64)
    if mode == TEST_PROVIDER_MODE:
        if provider != TEST_PROVIDER or state != "SIMULATED_ONLY":
            raise EchoCheckpointAnchorError("test provider must remain SIMULATED_ONLY")
        if not str(evidence["provider_reference"]).startswith("test://"):
            raise EchoCheckpointAnchorError("test-provider reference must use test://")
    elif mode == EXTERNAL_READ_BACK_MODE:
        if state != "VERIFIED_READ_BACK":
            raise EchoCheckpointAnchorError("external read-back evidence must be VERIFIED_READ_BACK")
        _sha256_text(evidence.get("provider_content_sha256"), label="provider content digest")
    else:
        raise EchoCheckpointAnchorError("unsupported anchor evidence provider mode")
    return evidence


def build_anchor_receipt(
    request: dict[str, Any],
    evidence: dict[str, Any],
    *,
    expected_provider: str,
    expected_mode: str,
) -> dict[str, Any]:
    verified = verify_anchor_evidence(
        evidence,
        request,
        expected_provider=expected_provider,
        expected_mode=expected_mode,
    )
    receipt = {
        "schema": ANCHOR_RECEIPT_SCHEMA,
        "provider": verified["provider"],
        "provider_mode": verified["provider_mode"],
        "provider_reference": verified["provider_reference"],
        "checkpoint_sequence": request["checkpoint_sequence"],
        "checkpoint_id": request["checkpoint_id"],
        "checkpoint_sha256": request["checkpoint_sha256"],
        "anchor_payload_sha256": request["anchor_payload_sha256"],
        "anchor_request_sha256": request["anchor_request_sha256"],
        "evidence_sha256": verified["evidence_sha256"],
        "verification_state": verified["verification_state"],
        "claims_boundary": (
            "Receipt proves only that supplied evidence matches this checkpoint anchor contract. "
            "Provider independence, immutability/WORM retention, privileged rollback resistance, "
            "legal chain of custody, and exactly-once transport require separate evidence."
        ),
    }
    if "provider_content_sha256" in verified:
        receipt["provider_content_sha256"] = verified["provider_content_sha256"]
    receipt["receipt_sha256"] = hashlib.sha256(_canonical(receipt)).hexdigest()
    return receipt


def verify_anchor_receipt(
    receipt: Any,
    bundle: Any,
    expected_fingerprint: str,
    *,
    expected_provider: str,
    expected_mode: str,
) -> dict[str, Any]:
    request = build_anchor_request(bundle, expected_fingerprint)
    if not isinstance(receipt, dict) or receipt.get("schema") != ANCHOR_RECEIPT_SCHEMA:
        raise EchoCheckpointAnchorError("anchor receipt schema mismatch")
    provider = _provider(receipt.get("provider"))
    if provider != expected_provider or receipt.get("provider_mode") != expected_mode:
        raise EchoCheckpointAnchorError("anchor receipt provider binding mismatch")
    for field in (
        "checkpoint_sequence",
        "checkpoint_id",
        "checkpoint_sha256",
        "anchor_payload_sha256",
        "anchor_request_sha256",
    ):
        if receipt.get(field) != request.get(field):
            raise EchoCheckpointAnchorError(f"anchor receipt {field} mismatch")
    _sha256_text(receipt.get("evidence_sha256"), label="anchor evidence digest")
    supplied = _sha256_text(receipt.get("receipt_sha256"), label="anchor receipt digest")
    core = dict(receipt)
    core.pop("receipt_sha256", None)
    if hashlib.sha256(_canonical(core)).hexdigest() != supplied:
        raise EchoCheckpointAnchorError("anchor receipt digest mismatch")
    state = receipt.get("verification_state")
    if expected_mode == TEST_PROVIDER_MODE:
        if provider != TEST_PROVIDER or state != "SIMULATED_ONLY":
            raise EchoCheckpointAnchorError("test anchor receipt must remain SIMULATED_ONLY")
    elif expected_mode == EXTERNAL_READ_BACK_MODE:
        if state != "VERIFIED_READ_BACK":
            raise EchoCheckpointAnchorError("external anchor receipt lacks verified read-back state")
        _sha256_text(receipt.get("provider_content_sha256"), label="provider content digest")
    else:
        raise EchoCheckpointAnchorError("unsupported anchor receipt provider mode")
    return {
        "schema": "WS-ECHO-CHECKPOINT-ANCHOR-VERIFICATION-V1",
        "status": "PASS",
        "checkpoint_sequence": request["checkpoint_sequence"],
        "checkpoint_sha256": request["checkpoint_sha256"],
        "provider": provider,
        "provider_mode": expected_mode,
        "verification_state": state,
        "receipt_sha256": supplied,
        "claims_boundary": receipt.get("claims_boundary"),
    }

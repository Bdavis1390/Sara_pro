from __future__ import annotations

import base64
import hashlib
import json
import re
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives.asymmetric.mldsa import MLDSA65PublicKey

from .echo_checkpoint import (
    CHECKPOINT_BUNDLE_SCHEMA,
    CHECKPOINT_SCHEMA,
    EchoCheckpointError,
    merkle_root,
)
from .echo_checkpoint_signer import CHECKPOINT_SIGNATURE_CONTEXT

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class EchoCheckpointVerificationError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _b64url_decode(value: Any, *, label: str) -> bytes:
    if not isinstance(value, str) or not value:
        raise EchoCheckpointVerificationError(f"{label} must be non-empty base64url text")
    try:
        padded = value + "=" * (-len(value) % 4)
        return base64.b64decode(padded.encode("ascii"), altchars=b"-_", validate=True)
    except (ValueError, UnicodeEncodeError) as exc:
        raise EchoCheckpointVerificationError(f"{label} is not valid base64url") from exc


def _sha256(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise EchoCheckpointVerificationError(f"{label} must be a lowercase SHA-256 digest")
    return value


def _verify_signature(
    *,
    algorithm: str,
    public_bytes: bytes,
    signature: bytes,
    manifest_bytes: bytes,
    manifest: dict[str, Any],
    public: dict[str, Any],
) -> None:
    try:
        if algorithm == "ML-DSA-65":
            if len(public_bytes) != 1952:
                raise EchoCheckpointVerificationError("ML-DSA-65 public key must be 1952 bytes")
            if len(signature) != 3309:
                raise EchoCheckpointVerificationError("ML-DSA-65 signature must be 3309 bytes")
            expected_context = CHECKPOINT_SIGNATURE_CONTEXT.decode("ascii")
            if manifest.get("signature_context") != expected_context:
                raise EchoCheckpointVerificationError("ML-DSA-65 manifest signature context mismatch")
            if public.get("signature_context") != expected_context:
                raise EchoCheckpointVerificationError("ML-DSA-65 public-key signature context mismatch")
            MLDSA65PublicKey.from_public_bytes(public_bytes).verify(
                signature,
                manifest_bytes,
                CHECKPOINT_SIGNATURE_CONTEXT,
            )
            return
        if algorithm == "Ed25519":
            if len(public_bytes) != 32:
                raise EchoCheckpointVerificationError("Ed25519 public key must be 32 bytes")
            if len(signature) != 64:
                raise EchoCheckpointVerificationError("Ed25519 signature must be 64 bytes")
            if "signature_context" in manifest or "signature_context" in public:
                raise EchoCheckpointVerificationError(
                    "legacy Ed25519 checkpoints must not claim ML-DSA signature context"
                )
            Ed25519PublicKey.from_public_bytes(public_bytes).verify(signature, manifest_bytes)
            return
        raise EchoCheckpointVerificationError(
            f"unsupported checkpoint signing algorithm: {algorithm}"
        )
    except InvalidSignature as exc:
        raise EchoCheckpointVerificationError("checkpoint signature verification failed") from exc


def verify_bundle(bundle: Any, expected_fingerprint: str) -> dict[str, Any]:
    expected_fingerprint = _sha256(
        expected_fingerprint, label="expected public-key fingerprint"
    )
    if not isinstance(bundle, dict) or bundle.get("schema") != CHECKPOINT_BUNDLE_SCHEMA:
        raise EchoCheckpointVerificationError("checkpoint bundle schema mismatch")
    manifest = bundle.get("manifest")
    public = bundle.get("public_key")
    if not isinstance(manifest, dict) or manifest.get("schema") != CHECKPOINT_SCHEMA:
        raise EchoCheckpointVerificationError("checkpoint manifest schema mismatch")
    if not isinstance(public, dict):
        raise EchoCheckpointVerificationError("checkpoint public-key record is missing")
    if public.get("schema") != "WS-ECHO-CHECKPOINT-PUBLIC-KEY-V1":
        raise EchoCheckpointVerificationError("checkpoint public-key schema mismatch")
    if public.get("issuer") != "ECHO_SENTINEL_LINK" or public.get("purpose") != "PROVENANCE_CHECKPOINT_SIGNING":
        raise EchoCheckpointVerificationError("checkpoint public-key purpose mismatch")

    algorithm = public.get("algorithm")
    if not isinstance(algorithm, str) or manifest.get("algorithm") != algorithm:
        raise EchoCheckpointVerificationError("checkpoint signing algorithm mismatch")
    if algorithm not in {"ML-DSA-65", "Ed25519"}:
        raise EchoCheckpointVerificationError("checkpoint signing algorithm is unsupported")

    public_bytes = _b64url_decode(public.get("public_key_b64url"), label="public key")
    actual_fingerprint = hashlib.sha256(public_bytes).hexdigest()
    public_fingerprint = _sha256(public.get("fingerprint_sha256"), label="public-key fingerprint")
    manifest_fingerprint = _sha256(
        manifest.get("key_fingerprint_sha256"), label="manifest key fingerprint"
    )
    if not (
        actual_fingerprint
        == public_fingerprint
        == manifest_fingerprint
        == expected_fingerprint
    ):
        raise EchoCheckpointVerificationError("checkpoint public-key fingerprint is not trusted")
    if not isinstance(public.get("key_id"), str) or not public["key_id"]:
        raise EchoCheckpointVerificationError("checkpoint key ID is missing")
    if manifest.get("key_id") != public.get("key_id"):
        raise EchoCheckpointVerificationError("manifest/public-key key ID mismatch")

    sequence = manifest.get("sequence")
    if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 1:
        raise EchoCheckpointVerificationError("checkpoint sequence must be a positive integer")
    if manifest.get("issuer") != "ECHO_SENTINEL_LINK":
        raise EchoCheckpointVerificationError("checkpoint issuer mismatch")
    checkpoint_id = manifest.get("checkpoint_id")
    if not isinstance(checkpoint_id, str) or not checkpoint_id:
        raise EchoCheckpointVerificationError("checkpoint ID is missing")
    previous = manifest.get("previous_checkpoint_sha256")
    if previous is not None:
        _sha256(previous, label="previous checkpoint digest")

    events = manifest.get("events")
    if not isinstance(events, list) or not events:
        raise EchoCheckpointVerificationError("checkpoint must contain at least one event")
    if manifest.get("event_count") != len(events):
        raise EchoCheckpointVerificationError("checkpoint event count mismatch")
    seen: set[str] = set()
    prior_event_id: str | None = None
    normalized: list[dict[str, Any]] = []
    for ordinal, item in enumerate(events, start=1):
        if not isinstance(item, dict) or set(item) != {"ordinal", "event_id", "semantic_sha256"}:
            raise EchoCheckpointVerificationError("checkpoint event record shape mismatch")
        if item.get("ordinal") != ordinal:
            raise EchoCheckpointVerificationError("checkpoint event ordinals are not contiguous")
        event_id = item.get("event_id")
        if not isinstance(event_id, str) or not event_id:
            raise EchoCheckpointVerificationError("checkpoint event ID is invalid")
        if event_id in seen:
            raise EchoCheckpointVerificationError("checkpoint event IDs must be unique")
        if prior_event_id is not None and event_id <= prior_event_id:
            raise EchoCheckpointVerificationError("checkpoint events are not strictly sorted by event ID")
        digest = _sha256(item.get("semantic_sha256"), label="semantic digest")
        seen.add(event_id)
        prior_event_id = event_id
        normalized.append({"ordinal": ordinal, "event_id": event_id, "semantic_sha256": digest})
    try:
        root = merkle_root(normalized)
    except EchoCheckpointError as exc:
        raise EchoCheckpointVerificationError(str(exc)) from exc
    if manifest.get("merkle_root_sha256") != root:
        raise EchoCheckpointVerificationError("checkpoint Merkle root mismatch")

    manifest_bytes = _canonical(manifest)
    checkpoint_digest = hashlib.sha256(manifest_bytes).hexdigest()
    if bundle.get("checkpoint_sha256") != checkpoint_digest:
        raise EchoCheckpointVerificationError("checkpoint manifest digest mismatch")
    signature = _b64url_decode(bundle.get("signature_b64url"), label="checkpoint signature")
    _verify_signature(
        algorithm=algorithm,
        public_bytes=public_bytes,
        signature=signature,
        manifest_bytes=manifest_bytes,
        manifest=manifest,
        public=public,
    )

    return {
        "sequence": sequence,
        "checkpoint_id": checkpoint_id,
        "checkpoint_sha256": checkpoint_digest,
        "previous_checkpoint_sha256": previous,
        "event_count": len(normalized),
        "events": normalized,
        "algorithm": algorithm,
        "post_quantum_signature_protection": algorithm == "ML-DSA-65",
        "key_id": public["key_id"],
        "key_fingerprint_sha256": expected_fingerprint,
    }


def verify_chain(bundles: list[Any], expected_fingerprint: str) -> dict[str, Any]:
    if not isinstance(bundles, list) or not bundles:
        raise EchoCheckpointVerificationError("at least one checkpoint bundle is required")
    verified: list[dict[str, Any]] = []
    previous: dict[str, Any] | None = None
    pq_anchor_sequence: int | None = None
    for bundle in bundles:
        current = verify_bundle(bundle, expected_fingerprint)
        if previous is None:
            if current["sequence"] != 1 or current["previous_checkpoint_sha256"] is not None:
                raise EchoCheckpointVerificationError("checkpoint chain must begin at sequence 1")
        else:
            if current["sequence"] != previous["sequence"] + 1:
                raise EchoCheckpointVerificationError("checkpoint sequence is not contiguous")
            if current["previous_checkpoint_sha256"] != previous["checkpoint_sha256"]:
                raise EchoCheckpointVerificationError("checkpoint predecessor digest mismatch")
            if previous["post_quantum_signature_protection"] and not current["post_quantum_signature_protection"]:
                raise EchoCheckpointVerificationError(
                    "checkpoint chain attempts post-quantum to classical signature downgrade"
                )
            prior = {item["event_id"]: item["semantic_sha256"] for item in previous["events"]}
            now = {item["event_id"]: item["semantic_sha256"] for item in current["events"]}
            for event_id, digest in prior.items():
                if now.get(event_id) != digest:
                    raise EchoCheckpointVerificationError(
                        "checkpoint chain deletes or substitutes previously checkpointed provenance"
                    )
        if current["post_quantum_signature_protection"] and pq_anchor_sequence is None:
            pq_anchor_sequence = current["sequence"]
        verified.append(current)
        previous = current
    assert previous is not None
    return {
        "schema": "WS-ECHO-CHECKPOINT-VERIFICATION-V2",
        "status": "PASS",
        "checkpoint_count": len(verified),
        "first_sequence": verified[0]["sequence"],
        "last_sequence": previous["sequence"],
        "last_checkpoint_sha256": previous["checkpoint_sha256"],
        "latest_algorithm": previous["algorithm"],
        "post_quantum_signature_protection": previous["post_quantum_signature_protection"],
        "pq_anchor_sequence": pq_anchor_sequence,
        "expected_key_fingerprint_sha256": previous["key_fingerprint_sha256"],
        "claims_boundary": (
            "Cryptographic verification of the supplied checkpoint chain. An ML-DSA-65 latest "
            "checkpoint establishes post-quantum signature protection for the checkpoint layer "
            "from its PQ anchor forward; immutable/WORM retention, transport PQ security, external "
            "anchoring, third-party attestation, and privileged rollback resistance are separate."
        ),
    }

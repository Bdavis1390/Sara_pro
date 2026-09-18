from __future__ import annotations

import base64
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from .registry_checkpoint import RegistryCheckpointIntegrityError


WITNESS_RECEIPT_SCHEMA = "WS-SARA-REGISTRY-MONOTONIC-WITNESS-RECEIPT-V1"
WITNESS_VERIFICATION_SCHEMA = "WS-SARA-REGISTRY-MONOTONIC-WITNESS-VERIFICATION-V1"
WITNESS_PURPOSE = "REGISTRY_CHECKPOINT_MONOTONIC_WITNESS"
TEST_WITNESS_MODE = "TEST_ONLY_IN_PROCESS"
REMOTE_WITNESS_MODE = "REMOTE_WITNESS"
ZERO_HASH = "0" * 64

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SAFE_ID = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
_NAMESPACE = re.compile(r"^[A-Za-z0-9._:/-]{1,256}$")


class RegistryWitnessError(RuntimeError):
    pass


class RegistryWitnessConfigError(RegistryWitnessError):
    pass


class RegistryWitnessSignatureError(RegistryWitnessError):
    pass


class RegistryWitnessMonotonicityError(RegistryWitnessError):
    pass


class RegistryWitnessRollbackDetected(RegistryWitnessMonotonicityError):
    pass


class RegistryWitnessConflict(RegistryWitnessMonotonicityError):
    pass


class RegistryWitnessUnavailable(RegistryWitnessError):
    pass


@dataclass(frozen=True)
class RegistryWitnessCoordinates:
    generation: int
    state_root_sha256: str
    commit_hash: str


class RegistryWitnessTransport(Protocol):
    """Transport contract for a witness service.

    Production independence is a deployment property. Implementations must not
    infer it from this interface or from a receipt field.
    """

    witness_mode: str

    def read_head(self, namespace: str) -> dict[str, Any] | None:
        ...

    def witness(self, namespace: str, coordinates: RegistryWitnessCoordinates) -> dict[str, Any]:
        ...


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _decode_b64url(value: Any, *, label: str) -> bytes:
    if not isinstance(value, str) or not value:
        raise RegistryWitnessSignatureError(f"{label} must be non-empty base64url text")
    if any(character.isspace() for character in value):
        raise RegistryWitnessSignatureError(f"{label} must not contain whitespace")
    try:
        padding = "=" * ((4 - len(value) % 4) % 4)
        return base64.urlsafe_b64decode(value + padding)
    except Exception as exc:
        raise RegistryWitnessSignatureError(f"{label} is not valid base64url") from exc


def _safe_id(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or not _SAFE_ID.fullmatch(value):
        raise RegistryWitnessError(f"{label} is invalid")
    return value


def _namespace(value: Any) -> str:
    if not isinstance(value, str) or not _NAMESPACE.fullmatch(value):
        raise RegistryWitnessError("witness namespace is invalid")
    return value


def _sha256(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise RegistryWitnessError(f"{label} must be a lowercase SHA-256 digest")
    return value


def _generation(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise RegistryWitnessError("witness generation must be a non-negative integer")
    return value


def coordinates_from_checkpoint_status(status: Any) -> RegistryWitnessCoordinates:
    if not isinstance(status, dict):
        raise RegistryWitnessError("checkpoint status must be an object")
    return RegistryWitnessCoordinates(
        generation=_generation(status.get("generation")),
        state_root_sha256=_sha256(
            status.get("state_root_sha256"),
            label="checkpoint state root",
        ),
        commit_hash=_sha256(status.get("commit_hash"), label="checkpoint commit hash"),
    )


def _receipt_core(receipt: dict[str, Any]) -> dict[str, Any]:
    core = dict(receipt)
    core.pop("signature_b64url", None)
    core.pop("receipt_sha256", None)
    return core


def canonical_witness_message(core: dict[str, Any]) -> bytes:
    return b"WS-SARA-REGISTRY-MONOTONIC-WITNESS-V1\0" + _canonical(core)


def _validate_receipt_core(core: Any) -> dict[str, Any]:
    if not isinstance(core, dict):
        raise RegistryWitnessError("witness receipt core must be an object")
    if core.get("schema") != WITNESS_RECEIPT_SCHEMA:
        raise RegistryWitnessError("witness receipt schema mismatch")
    if core.get("purpose") != WITNESS_PURPOSE:
        raise RegistryWitnessError("witness receipt purpose mismatch")
    _safe_id(core.get("witness_id"), label="witness id")
    _safe_id(core.get("key_id"), label="witness key id")
    _namespace(core.get("namespace"))
    _generation(core.get("generation"))
    _sha256(core.get("state_root_sha256"), label="witness state root")
    _sha256(core.get("commit_hash"), label="witness commit hash")
    _sha256(core.get("previous_receipt_sha256"), label="previous witness receipt digest")
    issued_at = core.get("issued_at")
    if not isinstance(issued_at, str) or not issued_at or len(issued_at) > 128:
        raise RegistryWitnessError("witness issued_at is invalid")
    mode = core.get("witness_mode")
    if mode not in {TEST_WITNESS_MODE, REMOTE_WITNESS_MODE}:
        raise RegistryWitnessError("unsupported witness mode")
    if core.get("algorithm") != "Ed25519":
        raise RegistryWitnessError("unsupported witness signing algorithm")
    claims = core.get("claims_boundary")
    if not isinstance(claims, str) or not claims:
        raise RegistryWitnessError("witness claims boundary is required")
    return core


def build_signed_witness_receipt(
    *,
    private_key: Ed25519PrivateKey,
    witness_id: str,
    key_id: str,
    namespace: str,
    coordinates: RegistryWitnessCoordinates,
    previous_receipt_sha256: str = ZERO_HASH,
    issued_at: str | None = None,
    witness_mode: str = TEST_WITNESS_MODE,
) -> dict[str, Any]:
    _safe_id(witness_id, label="witness id")
    _safe_id(key_id, label="witness key id")
    _namespace(namespace)
    _generation(coordinates.generation)
    _sha256(coordinates.state_root_sha256, label="witness state root")
    _sha256(coordinates.commit_hash, label="witness commit hash")
    _sha256(previous_receipt_sha256, label="previous witness receipt digest")
    if witness_mode not in {TEST_WITNESS_MODE, REMOTE_WITNESS_MODE}:
        raise RegistryWitnessError("unsupported witness mode")
    timestamp = issued_at or datetime.now(timezone.utc).isoformat()
    if not isinstance(timestamp, str) or not timestamp or len(timestamp) > 128:
        raise RegistryWitnessError("witness issued_at is invalid")

    claims_boundary = (
        "Cryptographic receipt only. Signature and monotonicity do not by themselves prove "
        "independent administration, independent storage, WORM retention, remote transport "
        "provenance, legal chain of custody, availability, or protection from compromise of "
        "the witness signing authority."
    )
    if witness_mode == TEST_WITNESS_MODE:
        claims_boundary = (
            "TEST_ONLY in-process witness. This receipt can validate protocol behavior and "
            "rollback comparisons but MUST NOT be represented as an independent or external witness."
        )

    core = {
        "schema": WITNESS_RECEIPT_SCHEMA,
        "purpose": WITNESS_PURPOSE,
        "witness_id": witness_id,
        "witness_mode": witness_mode,
        "namespace": namespace,
        "generation": coordinates.generation,
        "state_root_sha256": coordinates.state_root_sha256,
        "commit_hash": coordinates.commit_hash,
        "previous_receipt_sha256": previous_receipt_sha256,
        "issued_at": timestamp,
        "algorithm": "Ed25519",
        "key_id": key_id,
        "claims_boundary": claims_boundary,
    }
    _validate_receipt_core(core)
    signature = private_key.sign(canonical_witness_message(core))
    receipt = dict(core)
    receipt["signature_b64url"] = _b64url(signature)
    receipt["receipt_sha256"] = hashlib.sha256(_canonical(receipt)).hexdigest()
    return receipt


class RegistryMonotonicWitnessVerifier:
    def __init__(
        self,
        *,
        public_keys_b64url: dict[str, str],
        expected_witness_id: str,
        expected_namespace: str,
    ) -> None:
        self.expected_witness_id = _safe_id(expected_witness_id, label="expected witness id")
        self.expected_namespace = _namespace(expected_namespace)
        if not public_keys_b64url:
            raise RegistryWitnessConfigError("at least one pinned witness public key is required")
        keys: dict[str, Ed25519PublicKey] = {}
        for key_id, encoded in public_keys_b64url.items():
            safe_key_id = _safe_id(key_id, label="witness key id")
            raw = _decode_b64url(encoded, label=f"witness public key {safe_key_id}")
            if len(raw) != 32:
                raise RegistryWitnessConfigError("Ed25519 witness public key must be 32 bytes")
            try:
                keys[safe_key_id] = Ed25519PublicKey.from_public_bytes(raw)
            except ValueError as exc:
                raise RegistryWitnessConfigError("invalid Ed25519 witness public key") from exc
        self._keys = keys

    def verify_receipt(self, receipt: Any) -> dict[str, Any]:
        if not isinstance(receipt, dict):
            raise RegistryWitnessError("witness receipt must be an object")
        core = _validate_receipt_core(_receipt_core(receipt))
        if core["witness_id"] != self.expected_witness_id:
            raise RegistryWitnessError("witness id mismatch")
        if core["namespace"] != self.expected_namespace:
            raise RegistryWitnessError("witness namespace mismatch")
        key_id = core["key_id"]
        key = self._keys.get(key_id)
        if key is None:
            raise RegistryWitnessSignatureError("witness receipt key is not pinned")

        signature = _decode_b64url(receipt.get("signature_b64url"), label="witness signature")
        if len(signature) != 64:
            raise RegistryWitnessSignatureError("Ed25519 witness signature must be 64 bytes")
        try:
            key.verify(signature, canonical_witness_message(core))
        except InvalidSignature as exc:
            raise RegistryWitnessSignatureError("witness receipt signature verification failed") from exc

        supplied_digest = _sha256(receipt.get("receipt_sha256"), label="witness receipt digest")
        digest_input = dict(receipt)
        digest_input.pop("receipt_sha256", None)
        expected_digest = hashlib.sha256(_canonical(digest_input)).hexdigest()
        if supplied_digest != expected_digest:
            raise RegistryWitnessSignatureError("witness receipt digest mismatch")
        return dict(receipt)

    def assess_local_checkpoint(
        self,
        local_status: Any,
        witness_receipt: Any,
    ) -> dict[str, Any]:
        local = coordinates_from_checkpoint_status(local_status)
        receipt = self.verify_receipt(witness_receipt)
        remote = RegistryWitnessCoordinates(
            generation=_generation(receipt["generation"]),
            state_root_sha256=_sha256(receipt["state_root_sha256"], label="witness state root"),
            commit_hash=_sha256(receipt["commit_hash"], label="witness commit hash"),
        )

        if remote.generation > local.generation:
            raise RegistryWitnessRollbackDetected(
                "local registry generation is older than signed monotonic witness head"
            )
        if remote.generation == local.generation:
            if (
                remote.state_root_sha256 != local.state_root_sha256
                or remote.commit_hash != local.commit_hash
            ):
                raise RegistryWitnessConflict(
                    "local registry checkpoint conflicts with signed witness at the same generation"
                )
            return {
                "schema": WITNESS_VERIFICATION_SCHEMA,
                "status": "PASS",
                "generation": local.generation,
                "state_root_sha256": local.state_root_sha256,
                "commit_hash": local.commit_hash,
                "witness_id": receipt["witness_id"],
                "witness_mode": receipt["witness_mode"],
                "witness_receipt_sha256": receipt["receipt_sha256"],
                "signature_verified": True,
                "monotonic_match": True,
                "external_witnessed": False,
                "independence_verified": False,
                "claims_boundary": (
                    "PASS proves that the local checkpoint exactly matches a valid pinned-key witness "
                    "receipt. Deployment independence is not inferred from a signed receipt and requires "
                    "separate evidence."
                ),
            }

        return {
            "schema": WITNESS_VERIFICATION_SCHEMA,
            "status": "NEEDS_WITNESS_ADVANCE",
            "generation": local.generation,
            "witness_generation": remote.generation,
            "witness_id": receipt["witness_id"],
            "witness_mode": receipt["witness_mode"],
            "witness_receipt_sha256": receipt["receipt_sha256"],
            "signature_verified": True,
            "monotonic_match": False,
            "external_witnessed": False,
            "independence_verified": False,
            "claims_boundary": (
                "The signed witness is older than local state. No rollback is established, but the "
                "local generation is not yet covered by this witness receipt."
            ),
        }


class InMemoryMonotonicWitness:
    """TEST_ONLY witness transport for deterministic qualification.

    This class is intentionally in-process. It cannot close the local privileged
    rollback threat in production and always emits TEST_ONLY_IN_PROCESS receipts.
    """

    witness_mode = TEST_WITNESS_MODE

    def __init__(
        self,
        *,
        private_key: Ed25519PrivateKey,
        witness_id: str,
        key_id: str,
        issued_at: str = "2026-09-17T00:00:00+00:00",
    ) -> None:
        self._private_key = private_key
        self.witness_id = _safe_id(witness_id, label="witness id")
        self.key_id = _safe_id(key_id, label="witness key id")
        self.issued_at = issued_at
        self._heads: dict[str, dict[str, Any]] = {}

    def read_head(self, namespace: str) -> dict[str, Any] | None:
        name = _namespace(namespace)
        head = self._heads.get(name)
        return None if head is None else dict(head)

    def witness(self, namespace: str, coordinates: RegistryWitnessCoordinates) -> dict[str, Any]:
        name = _namespace(namespace)
        _generation(coordinates.generation)
        _sha256(coordinates.state_root_sha256, label="witness state root")
        _sha256(coordinates.commit_hash, label="witness commit hash")
        head = self._heads.get(name)
        if head is not None:
            head_generation = _generation(head["generation"])
            if coordinates.generation < head_generation:
                raise RegistryWitnessRollbackDetected(
                    "witness refuses a generation lower than its monotonic head"
                )
            if coordinates.generation == head_generation:
                if (
                    coordinates.state_root_sha256 != head["state_root_sha256"]
                    or coordinates.commit_hash != head["commit_hash"]
                ):
                    raise RegistryWitnessConflict(
                        "witness refuses conflicting checkpoint coordinates at the same generation"
                    )
                return dict(head)
            previous = _sha256(head["receipt_sha256"], label="previous witness receipt digest")
        else:
            previous = ZERO_HASH

        receipt = build_signed_witness_receipt(
            private_key=self._private_key,
            witness_id=self.witness_id,
            key_id=self.key_id,
            namespace=name,
            coordinates=coordinates,
            previous_receipt_sha256=previous,
            issued_at=self.issued_at,
            witness_mode=TEST_WITNESS_MODE,
        )
        self._heads[name] = receipt
        return dict(receipt)


class RegistryMonotonicWitnessClient:
    def __init__(
        self,
        *,
        transport: RegistryWitnessTransport,
        verifier: RegistryMonotonicWitnessVerifier,
    ) -> None:
        self.transport = transport
        self.verifier = verifier

    def check(self, local_status: Any, *, require_head: bool = True) -> dict[str, Any]:
        try:
            head = self.transport.read_head(self.verifier.expected_namespace)
        except Exception as exc:
            raise RegistryWitnessUnavailable("unable to read registry witness head") from exc
        if head is None:
            if require_head:
                raise RegistryWitnessUnavailable("registry witness has no head for this namespace")
            local = coordinates_from_checkpoint_status(local_status)
            return {
                "schema": WITNESS_VERIFICATION_SCHEMA,
                "status": "NO_WITNESS",
                "generation": local.generation,
                "signature_verified": False,
                "external_witnessed": False,
                "independence_verified": False,
            }
        return self.verifier.assess_local_checkpoint(local_status, head)

    def advance_and_verify(self, local_status: Any) -> dict[str, Any]:
        coordinates = coordinates_from_checkpoint_status(local_status)
        try:
            receipt = self.transport.witness(
                self.verifier.expected_namespace,
                coordinates,
            )
        except RegistryWitnessError:
            raise
        except Exception as exc:
            raise RegistryWitnessUnavailable("unable to advance registry witness") from exc
        assessment = self.verifier.assess_local_checkpoint(local_status, receipt)
        if assessment["status"] != "PASS":
            raise RegistryCheckpointIntegrityError(
                "witness did not advance to the exact local checkpoint"
            )
        return assessment

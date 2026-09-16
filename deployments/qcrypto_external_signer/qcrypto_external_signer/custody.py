"""Separately controlled QCRYPTO custody-release signer.

This package is deliberately outside the SARA runtime.  It independently verifies
one frozen execution handoff, consumes the human approval once, and produces an
ML-DSA-65 *custody-release attestation*.  It does not create a Bitcoin/Ethereum
native transaction signature and contains no transaction-broadcast client.

The durable state machine is intentionally conservative:

    VERIFIED -> INVOKING -> SIGNED
                     \
                      -> INDETERMINATE

INVOKING is persisted before the signer is called.  A request observed in INVOKING
after restart is moved to INDETERMINATE and cannot be retried automatically.
"""
from __future__ import annotations

import base64
import binascii
import fcntl
import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Protocol

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.mldsa import MLDSA65PrivateKey, MLDSA65PublicKey

REQUEST_SCHEMA = "WS-QCRYPTO-EXTERNAL-CUSTODY-REQUEST-V1"
RECEIPT_SCHEMA = "WS-QCRYPTO-EXTERNAL-CUSTODY-SIGNING-RECEIPT-V1"
LEDGER_SCHEMA = "WS-QCRYPTO-EXTERNAL-CUSTODY-LEDGER-V1"
INTENT_SCHEMA = "WS-LIVE-VALUE-EXECUTION-INTENT-V1"
APPROVAL_SCHEMA = "WS-LIVE-VALUE-HUMAN-APPROVAL-V1"
HANDOFF_SCHEMA = "WS-LIVE-VALUE-EXECUTION-HANDOFF-V1"
APPROVAL_CONTEXT = b"WS-LIVE-VALUE-HUMAN-APPROVAL-V1"
RELEASE_CONTEXT = b"WS-QCRYPTO-EXTERNAL-CUSTODY-RELEASE-V1"
READY_HANDOFF_STATE = "READY_FOR_EXTERNAL_SIGNER_VALUE_EXECUTION_HANDOFF"
MAX_APPROVAL_LIFETIME = timedelta(minutes=15)
MAX_FUTURE_SKEW = timedelta(seconds=60)
MAX_UNSIGNED_PAYLOAD_BYTES = 2 * 1024 * 1024


class CustodyError(ValueError):
    pass


class CustodyConflict(CustodyError):
    pass


class CustodyIndeterminate(CustodyError):
    pass


class ReleaseSigner(Protocol):
    @property
    def algorithm(self) -> str: ...

    @property
    def context(self) -> bytes: ...

    @property
    def fingerprint_sha256(self) -> str: ...

    @property
    def public_key_bytes(self) -> bytes: ...

    def sign_release(self, payload: bytes) -> bytes: ...


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise CustodyError("timestamp must be timezone-aware")
    return value.astimezone(timezone.utc)


def _utc_text(value: datetime) -> str:
    return _utc(value).isoformat().replace("+00:00", "Z")


def _parse_time(value: Any, label: str) -> datetime:
    if not isinstance(value, str):
        raise CustodyError(f"{label} must be an ISO-8601 string")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CustodyError(f"{label} is not valid ISO-8601") from exc
    return _utc(result)


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise CustodyError("value is not canonical JSON") from exc


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _hex64(value: Any, label: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise CustodyError(f"{label} must be lowercase SHA-256 hex")
    return value


def _b64decode(value: Any, *, label: str, maximum: int) -> bytes:
    if not isinstance(value, str) or not value:
        raise CustodyError(f"{label} must be non-empty base64url text")
    try:
        raw = value.encode("ascii")
        decoded = base64.b64decode(raw + b"=" * (-len(raw) % 4), altchars=b"-_", validate=True)
    except (UnicodeEncodeError, binascii.Error, ValueError) as exc:
        raise CustodyError(f"invalid {label} encoding") from exc
    if not decoded or len(decoded) > maximum:
        raise CustodyError(f"{label} length is invalid")
    return decoded


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _require_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise CustodyError(f"{label} must be a JSON object")
    return dict(value)


def _require_false(mapping: dict[str, Any], field: str, label: str) -> None:
    if mapping.get(field) is not False:
        raise CustodyError(f"{label}.{field} must remain false")


def canonical_intent(intent: dict[str, Any]) -> dict[str, Any]:
    if intent.get("schema") != INTENT_SCHEMA:
        raise CustodyError("unsupported execution intent schema")
    required = (
        "chain", "network", "asset", "amount_atomic", "fee_ceiling_atomic",
        "source_custody_ref", "destination_commitment_sha256",
        "unsigned_transaction_digest_sha256", "review_package_sha256",
        "production_revision", "change_ticket_id", "intent_nonce", "valid_until",
    )
    if any(key not in intent for key in required):
        raise CustodyError("execution intent is incomplete")
    amount = intent["amount_atomic"]
    fee = intent["fee_ceiling_atomic"]
    if not isinstance(amount, int) or isinstance(amount, bool) or amount <= 0:
        raise CustodyError("amount_atomic must be a positive integer")
    if not isinstance(fee, int) or isinstance(fee, bool) or fee < 0:
        raise CustodyError("fee_ceiling_atomic must be a non-negative integer")
    for field in ("destination_commitment_sha256", "unsigned_transaction_digest_sha256", "review_package_sha256"):
        _hex64(intent[field], field)
    valid_until = _parse_time(intent["valid_until"], "intent.valid_until")
    return {
        "schema": INTENT_SCHEMA,
        "chain": str(intent["chain"]),
        "network": str(intent["network"]),
        "asset": str(intent["asset"]),
        "amount_atomic": amount,
        "fee_ceiling_atomic": fee,
        "source_custody_ref": str(intent["source_custody_ref"]),
        "destination_commitment_sha256": intent["destination_commitment_sha256"],
        "unsigned_transaction_digest_sha256": intent["unsigned_transaction_digest_sha256"],
        "review_package_sha256": intent["review_package_sha256"],
        "production_revision": str(intent["production_revision"]),
        "change_ticket_id": str(intent["change_ticket_id"]),
        "intent_nonce": str(intent["intent_nonce"]),
        "valid_until": _utc_text(valid_until),
    }


def intent_sha256(intent: dict[str, Any]) -> str:
    return _sha(canonical_intent(intent))


def canonical_approval_message(approval: dict[str, Any]) -> bytes:
    if approval.get("schema") != APPROVAL_SCHEMA or approval.get("issuer") != "HUMAN_CHANGE_CONTROL":
        raise CustodyError("unsupported human approval schema or issuer")
    fields = (
        "schema", "issuer", "approver_id", "approval_id", "key_id", "intent_sha256",
        "review_package_sha256", "destination_commitment_sha256",
        "external_signer_fingerprint_sha256", "network_identity_sha256",
        "maximum_amount_atomic", "maximum_fee_atomic", "change_ticket_id",
        "production_revision", "issued_at", "expires_at", "nonce",
    )
    if any(field not in approval for field in fields):
        raise CustodyError("human approval is incomplete")
    payload = {field: approval[field] for field in fields}
    payload["issued_at"] = _utc_text(_parse_time(approval["issued_at"], "approval.issued_at"))
    payload["expires_at"] = _utc_text(_parse_time(approval["expires_at"], "approval.expires_at"))
    return _canonical(payload)


@dataclass(frozen=True)
class CustodyPolicy:
    allowed_chain_networks: frozenset[tuple[str, str]]
    require_broadcast_false: bool = True
    require_chain_native_signing_false: bool = True

    @classmethod
    def testnet_reference(cls) -> "CustodyPolicy":
        return cls(frozenset({("BITCOIN", "SIGNET"), ("ETHEREUM", "HOODI"), ("SYNTHETIC", "CI")}))


class EphemeralMlDsa65ReleaseSigner:
    """CI/reference signer.  The private key never leaves this object."""

    def __init__(self, private_key: MLDSA65PrivateKey | None = None) -> None:
        self._private = private_key or MLDSA65PrivateKey.generate()
        self._public = self._private.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        self.invocation_count = 0

    @property
    def algorithm(self) -> str:
        return "ML-DSA-65"

    @property
    def context(self) -> bytes:
        return RELEASE_CONTEXT

    @property
    def fingerprint_sha256(self) -> str:
        return hashlib.sha256(self._public).hexdigest()

    @property
    def public_key_bytes(self) -> bytes:
        return self._public

    def sign_release(self, payload: bytes) -> bytes:
        self.invocation_count += 1
        return self._private.sign(payload, self.context)


class FailingAfterInvocationSigner(EphemeralMlDsa65ReleaseSigner):
    """Test backend representing an ambiguous HSM/provider outcome."""

    def sign_release(self, payload: bytes) -> bytes:
        self.invocation_count += 1
        _ = self._private.sign(payload, self.context)
        raise RuntimeError("simulated ambiguous signer outcome")


def _verify_human_approval(
    approval: dict[str, Any],
    intent: dict[str, Any],
    *,
    trusted_public_keys: dict[str, bytes],
    now: datetime,
) -> dict[str, Any]:
    key_id = approval.get("key_id")
    if not isinstance(key_id, str) or key_id not in trusted_public_keys:
        raise CustodyError("human approval key is not independently trusted by custody")
    key = trusted_public_keys[key_id]
    if len(key) != 1952:
        raise CustodyError("trusted human approval ML-DSA-65 public key has invalid length")
    issued = _parse_time(approval.get("issued_at"), "approval.issued_at")
    expires = _parse_time(approval.get("expires_at"), "approval.expires_at")
    if expires <= issued or expires - issued > MAX_APPROVAL_LIFETIME:
        raise CustodyError("human approval lifetime is invalid")
    current = _utc(now)
    if issued > current + MAX_FUTURE_SKEW or current >= expires:
        raise CustodyError("human approval is not currently valid")
    intent_expiry = _parse_time(intent.get("valid_until"), "intent.valid_until")
    if current >= intent_expiry:
        raise CustodyError("execution intent is expired")

    expected_intent = intent_sha256(intent)
    exact = {
        "intent_sha256": expected_intent,
        "review_package_sha256": intent["review_package_sha256"],
        "destination_commitment_sha256": intent["destination_commitment_sha256"],
        "change_ticket_id": intent["change_ticket_id"],
        "production_revision": intent["production_revision"],
    }
    for field, expected in exact.items():
        if approval.get(field) != expected:
            raise CustodyError(f"human approval {field} mismatch")
    amount_cap = approval.get("maximum_amount_atomic")
    fee_cap = approval.get("maximum_fee_atomic")
    if not isinstance(amount_cap, int) or isinstance(amount_cap, bool) or intent["amount_atomic"] > amount_cap:
        raise CustodyError("execution amount exceeds independently verified human cap")
    if not isinstance(fee_cap, int) or isinstance(fee_cap, bool) or intent["fee_ceiling_atomic"] > fee_cap:
        raise CustodyError("execution fee ceiling exceeds independently verified human cap")

    signature = _b64decode(approval.get("signature_b64url"), label="human approval signature", maximum=4096)
    if len(signature) != 3309:
        raise CustodyError("human approval signature must be an ML-DSA-65 signature")
    try:
        MLDSA65PublicKey.from_public_bytes(key).verify(signature, canonical_approval_message(approval), APPROVAL_CONTEXT)
    except (InvalidSignature, ValueError) as exc:
        raise CustodyError("human approval signature did not verify in custody trust domain") from exc
    return {
        "approval_id": approval["approval_id"],
        "approver_id": approval["approver_id"],
        "key_fingerprint_sha256": hashlib.sha256(key).hexdigest(),
        "intent_sha256": expected_intent,
        "external_signer_fingerprint_sha256": _hex64(approval.get("external_signer_fingerprint_sha256"), "external signer fingerprint"),
        "network_identity_sha256": _hex64(approval.get("network_identity_sha256"), "network identity"),
        "expires_at": _utc_text(expires),
    }


def _reconstruct_handoff(
    handoff: dict[str, Any], intent: dict[str, Any], approval_verified: dict[str, Any], preflight: dict[str, Any]
) -> str:
    if handoff.get("schema") != HANDOFF_SCHEMA or handoff.get("state") != READY_HANDOFF_STATE:
        raise CustodyError("QCRYPTO handoff is not ready for external signer custody")
    if handoff.get("external_signer_handoff_ready") is not True or handoff.get("point_of_value_moving_execution_reached") is not True:
        raise CustodyError("QCRYPTO handoff readiness markers are incomplete")
    for field in (
        "qcrypto_execution_authority", "qcrypto_live_value_authorized",
        "qcrypto_private_key_operations_permitted", "qcrypto_broadcast_permitted",
    ):
        _require_false(handoff, field, "handoff")
    intent_digest = intent_sha256(intent)
    if handoff.get("intent_sha256") != intent_digest or handoff.get("approval_id") != approval_verified["approval_id"]:
        raise CustodyError("QCRYPTO handoff identity mismatch")
    observed_fee = preflight.get("observed_fee_atomic")
    if not isinstance(observed_fee, int) or isinstance(observed_fee, bool) or observed_fee < 0 or observed_fee > intent["fee_ceiling_atomic"]:
        raise CustodyError("external preflight fee is invalid")
    binding = {
        "schema": HANDOFF_SCHEMA,
        "intent_sha256": intent_digest,
        "approval_id": approval_verified["approval_id"],
        "approver_id": approval_verified["approver_id"],
        "approval_key_fingerprint_sha256": approval_verified["key_fingerprint_sha256"],
        "external_signer_fingerprint_sha256": approval_verified["external_signer_fingerprint_sha256"],
        "network_identity_sha256": approval_verified["network_identity_sha256"],
        "destination_commitment_sha256": intent["destination_commitment_sha256"],
        "unsigned_transaction_digest_sha256": intent["unsigned_transaction_digest_sha256"],
        "review_package_sha256": intent["review_package_sha256"],
        "production_revision": intent["production_revision"],
        "change_ticket_id": intent["change_ticket_id"],
        "amount_atomic": intent["amount_atomic"],
        "fee_ceiling_atomic": intent["fee_ceiling_atomic"],
        "observed_fee_atomic": observed_fee,
        "qcrypto_execution_authority": False,
        "qcrypto_broadcast_permitted": False,
    }
    reconstructed = _sha(binding)
    if handoff.get("handoff_package_sha256") != reconstructed:
        raise CustodyError("QCRYPTO handoff package digest does not independently reconstruct")
    return reconstructed


def _validate_preflight(preflight: dict[str, Any], intent: dict[str, Any], approval_verified: dict[str, Any]) -> None:
    expected_intent = intent_sha256(intent)
    exact = {
        "intent_sha256": expected_intent,
        "approval_id": approval_verified["approval_id"],
        "external_signer_fingerprint_sha256": approval_verified["external_signer_fingerprint_sha256"],
        "network_identity_sha256": approval_verified["network_identity_sha256"],
        "destination_commitment_sha256": intent["destination_commitment_sha256"],
    }
    for field, expected in exact.items():
        if preflight.get(field) != expected:
            raise CustodyError(f"external preflight {field} mismatch")
    for field in (
        "destination_allowlist_match", "balance_or_utxo_sufficient", "nonce_or_outpoint_reserved",
        "simulation_or_policy_check_passed", "monitoring_ready", "pause_ready", "rollback_ready",
    ):
        if preflight.get(field) is not True:
            raise CustodyError(f"external preflight requires {field}=true")
    for field in ("approval_consumed", "signed_payload_present", "private_key_material_present", "broadcast_requested"):
        if preflight.get(field, False) is not False:
            raise CustodyError(f"external preflight requires {field}=false")


def _validate_request(
    request: dict[str, Any], *, policy: CustodyPolicy, signer: ReleaseSigner,
    trusted_human_keys: dict[str, bytes], now: datetime,
) -> tuple[str, dict[str, Any], dict[str, Any], bytes, str]:
    if request.get("schema") != REQUEST_SCHEMA:
        raise CustodyError("unsupported external custody request schema")
    if request.get("broadcast_requested") is not False:
        raise CustodyError("custody release service has no broadcast authority")
    if request.get("chain_native_signing_requested") is not False:
        raise CustodyError("first-tranche custody service does not create native chain transaction signatures")
    request_id = request.get("request_id")
    if not isinstance(request_id, str) or not request_id or len(request_id) > 128:
        raise CustodyError("request_id is invalid")
    intent = canonical_intent(_require_object(request.get("intent"), "intent"))
    approval = _require_object(request.get("human_approval"), "human_approval")
    handoff = _require_object(request.get("handoff"), "handoff")
    preflight = _require_object(request.get("preflight"), "preflight")
    approval_verified = _verify_human_approval(approval, intent, trusted_public_keys=trusted_human_keys, now=now)
    _validate_preflight(preflight, intent, approval_verified)
    handoff_digest = _reconstruct_handoff(handoff, intent, approval_verified, preflight)
    if signer.fingerprint_sha256 != approval_verified["external_signer_fingerprint_sha256"]:
        raise CustodyError("custody signer is not the signer fingerprint approved by the human authority")
    observed_network = _hex64(request.get("observed_network_identity_sha256"), "observed network identity")
    if observed_network != approval_verified["network_identity_sha256"]:
        raise CustodyError("custody observed network identity does not match human approval")
    chain_network = (intent["chain"].upper(), intent["network"].upper())
    if chain_network not in policy.allowed_chain_networks:
        raise CustodyError("chain/network is not in the custody allowlist")
    if "MAINNET" in chain_network[1]:
        raise CustodyError("mainnet is not permitted by this custody tranche")
    unsigned_payload = _b64decode(request.get("unsigned_payload_b64url"), label="unsigned payload", maximum=MAX_UNSIGNED_PAYLOAD_BYTES)
    if hashlib.sha256(unsigned_payload).hexdigest() != intent["unsigned_transaction_digest_sha256"]:
        raise CustodyError("unsigned payload digest does not match frozen execution intent")
    semantic = {
        "schema": REQUEST_SCHEMA,
        "request_id": request_id,
        "intent": intent,
        "human_approval": approval,
        "handoff": handoff,
        "preflight": preflight,
        "unsigned_payload_sha256": hashlib.sha256(unsigned_payload).hexdigest(),
        "observed_network_identity_sha256": observed_network,
        "broadcast_requested": False,
        "chain_native_signing_requested": False,
    }
    return request_id, approval_verified, semantic, unsigned_payload, handoff_digest


class CustodyLedger:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock_path = self.path.with_suffix(self.path.suffix + ".lock")
        self.lock_path.touch(mode=0o600, exist_ok=True)

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"schema": LEDGER_SCHEMA, "requests": {}, "used_approvals": {}}
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CustodyError("custody ledger is unreadable") from exc
        if not isinstance(value, dict) or value.get("schema") != LEDGER_SCHEMA:
            raise CustodyError("custody ledger schema is invalid")
        if not isinstance(value.get("requests"), dict) or not isinstance(value.get("used_approvals"), dict):
            raise CustodyError("custody ledger structure is invalid")
        return value

    def _save(self, value: dict[str, Any]) -> None:
        encoded = json.dumps(value, sort_keys=True, indent=2) + "\n"
        fd, temporary = tempfile.mkstemp(prefix=".custody-ledger-", dir=str(self.path.parent), text=True)
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.path)
            directory_fd = os.open(self.path.parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def locked(self):
        return _LedgerLock(self)


class _LedgerLock:
    def __init__(self, ledger: CustodyLedger) -> None:
        self.ledger = ledger
        self.handle = None
        self.value: dict[str, Any] | None = None

    def __enter__(self) -> "_LedgerLock":
        self.handle = self.ledger.lock_path.open("r+")
        fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX)
        self.value = self.ledger._load()
        return self

    def commit(self) -> None:
        assert self.value is not None
        self.ledger._save(self.value)

    def __exit__(self, exc_type, exc, tb) -> None:
        assert self.handle is not None
        fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
        self.handle.close()


def _release_binding(
    *, request_digest: str, handoff_digest: str, intent_digest: str, unsigned_payload_sha256: str,
    approval_id: str, signer: ReleaseSigner, network_identity_sha256: str, destination_commitment_sha256: str,
    signed_at: datetime,
) -> dict[str, Any]:
    return {
        "schema": RECEIPT_SCHEMA,
        "request_sha256": request_digest,
        "handoff_package_sha256": handoff_digest,
        "intent_sha256": intent_digest,
        "unsigned_payload_sha256": unsigned_payload_sha256,
        "approval_id": approval_id,
        "signer_fingerprint_sha256": signer.fingerprint_sha256,
        "signing_algorithm": signer.algorithm,
        "signature_context": signer.context.decode("ascii"),
        "network_identity_sha256": network_identity_sha256,
        "destination_commitment_sha256": destination_commitment_sha256,
        "signed_at": _utc_text(signed_at),
        "chain_native_transaction_signature": False,
        "transaction_broadcast": False,
        "real_value_moved": False,
        "mainnet": False,
        "production_hsm_integrated": False,
    }


def verify_release_receipt(receipt: dict[str, Any], public_key_bytes: bytes) -> bool:
    try:
        signature = _b64decode(receipt.get("signature_b64url"), label="custody release signature", maximum=4096)
        receipt_digest = receipt.get("receipt_sha256")
        base = dict(receipt)
        base.pop("receipt_sha256", None)
        if receipt_digest != _sha(base):
            return False
        binding = {key: value for key, value in receipt.items() if key not in {"signature_b64url", "receipt_sha256", "state", "claims_boundary"}}
        MLDSA65PublicKey.from_public_bytes(public_key_bytes).verify(signature, _canonical(binding), RELEASE_CONTEXT)
        return True
    except (CustodyError, InvalidSignature, ValueError):
        return False


class ExternalCustodyService:
    def __init__(
        self, *, ledger: CustodyLedger, signer: ReleaseSigner, policy: CustodyPolicy,
        trusted_human_keys: dict[str, bytes],
    ) -> None:
        self.ledger = ledger
        self.signer = signer
        self.policy = policy
        self.trusted_human_keys = dict(trusted_human_keys)

    def execute_release(self, request: dict[str, Any], *, now: datetime | None = None) -> dict[str, Any]:
        current = _utc(now or datetime.now(timezone.utc))
        request_id, approval, semantic, unsigned_payload, handoff_digest = _validate_request(
            request, policy=self.policy, signer=self.signer,
            trusted_human_keys=self.trusted_human_keys, now=current,
        )
        request_digest = _sha(semantic)
        approval_id = approval["approval_id"]

        with self.ledger.locked() as locked:
            assert locked.value is not None
            requests = locked.value["requests"]
            used = locked.value["used_approvals"]
            prior = requests.get(request_id)
            if isinstance(prior, dict):
                if prior.get("request_sha256") != request_digest:
                    raise CustodyConflict("request_id was reused with changed semantic content")
                state = prior.get("state")
                if state == "SIGNED":
                    return dict(prior["receipt"])
                if state == "INVOKING":
                    prior["state"] = "INDETERMINATE"
                    prior["indeterminate_reason"] = "restart_or_retry_observed_after_invocation_fence"
                    locked.commit()
                    raise CustodyIndeterminate("signer outcome is indeterminate; automatic retry is forbidden")
                if state == "INDETERMINATE":
                    raise CustodyIndeterminate("signer outcome is indeterminate; human reconciliation is required")
                raise CustodyConflict("request is in an unsupported custody state")
            used_by = used.get(approval_id)
            if used_by is not None and used_by != request_id:
                raise CustodyConflict("human approval_id has already been consumed by another custody request")
            requests[request_id] = {
                "state": "INVOKING",
                "request_sha256": request_digest,
                "approval_id": approval_id,
                "handoff_package_sha256": handoff_digest,
                "intent_sha256": approval["intent_sha256"],
                "invoking_at": _utc_text(current),
            }
            used[approval_id] = request_id
            locked.commit()

        signed_at = datetime.now(timezone.utc)
        binding = _release_binding(
            request_digest=request_digest,
            handoff_digest=handoff_digest,
            intent_digest=approval["intent_sha256"],
            unsigned_payload_sha256=hashlib.sha256(unsigned_payload).hexdigest(),
            approval_id=approval_id,
            signer=self.signer,
            network_identity_sha256=approval["network_identity_sha256"],
            destination_commitment_sha256=semantic["intent"]["destination_commitment_sha256"],
            signed_at=signed_at,
        )
        try:
            signature = self.signer.sign_release(_canonical(binding))
        except Exception as exc:
            with self.ledger.locked() as locked:
                assert locked.value is not None
                entry = locked.value["requests"].get(request_id)
                if isinstance(entry, dict) and entry.get("state") == "INVOKING":
                    entry["state"] = "INDETERMINATE"
                    entry["indeterminate_reason"] = "signer_invocation_returned_without_confirmed_receipt"
                    locked.commit()
            raise CustodyIndeterminate("signer invocation outcome is indeterminate; automatic retry is forbidden") from exc

        receipt = {
            **binding,
            "state": "SIGNED_CUSTODY_RELEASE_ATTESTATION",
            "signature_b64url": _b64encode(signature),
            "claims_boundary": (
                "External custody release attestation only. This is not a Bitcoin/Ethereum native transaction signature, "
                "does not broadcast a transaction, does not move value, does not enable mainnet, and does not establish "
                "production HSM integration or end-to-end post-quantum chain security."
            ),
        }
        receipt["receipt_sha256"] = _sha(receipt)

        with self.ledger.locked() as locked:
            assert locked.value is not None
            entry = locked.value["requests"].get(request_id)
            if not isinstance(entry, dict) or entry.get("state") != "INVOKING" or entry.get("request_sha256") != request_digest:
                raise CustodyIndeterminate("custody ledger changed after signer invocation; receipt requires human reconciliation")
            entry["state"] = "SIGNED"
            entry["signed_at"] = _utc_text(signed_at)
            entry["receipt"] = receipt
            locked.commit()
        return receipt

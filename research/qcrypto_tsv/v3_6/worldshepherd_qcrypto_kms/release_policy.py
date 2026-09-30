"""Fail-closed Bitcoin release-intent and post-quantum attestation policy.

This is an application/custody policy layer, not a Bitcoin consensus rule. It binds
an unsigned transaction and its input/output sets to a policy epoch and, when
required, to a separate ML-DSA authorization. Mainnet and unknown networks remain
disabled in this recovery candidate.
"""
from __future__ import annotations

import base64
import datetime as dt
import hashlib
import json
import re
from dataclasses import asdict, dataclass
from typing import Any, Callable

from .bitcoin_quantum_policy import CryptoPolicyState

_HEX32_RE = re.compile(r"^[0-9a-fA-F]{64}$")
_PROVIDER_OP_RE = re.compile(r"^QCRYPTO-AWS-KMS-[0-9a-f]{64}$")
_ALLOWED_NETWORKS = {"SIGNET", "TESTNET4", "REGTEST"}
RELEASE_ATTESTATION_CONTEXT = b"WS-BITCOIN-RELEASE-AUTHORIZATION-V1"


class ReleasePolicyError(RuntimeError):
    pass


def _require_hex32(name: str, value: str) -> str:
    if not isinstance(value, str) or _HEX32_RE.fullmatch(value) is None:
        raise ReleasePolicyError(f"{name} must be 32-byte hex")
    return value.lower()


def _decode_b64url_nonempty(value: str) -> bytes:
    if not isinstance(value, str) or not value:
        raise ReleasePolicyError("PQ signature is missing")
    try:
        raw = value.encode("ascii")
        decoded = base64.b64decode(raw + b"=" * (-len(raw) % 4), altchars=b"-_", validate=True)
    except Exception as exc:
        raise ReleasePolicyError("PQ signature must be valid base64url") from exc
    if not decoded:
        raise ReleasePolicyError("PQ signature is empty")
    return decoded


@dataclass(frozen=True)
class BitcoinReleaseIntent:
    network: str
    unsigned_tx_sha256: str
    input_set_sha256: str
    output_set_sha256: str
    fee_sat: int
    policy_epoch: str
    signing_policy_sha256: str = ""
    authorization_nonce: str = ""
    expires_at: str = ""

    def canonical_bytes(self) -> bytes:
        network = self.network.strip().upper()
        if network not in _ALLOWED_NETWORKS:
            raise ReleasePolicyError("release intent network is not explicitly allowed; mainnet and unknown networks fail closed")
        unsigned_tx = _require_hex32("unsigned_tx_sha256", self.unsigned_tx_sha256)
        input_set = _require_hex32("input_set_sha256", self.input_set_sha256)
        output_set = _require_hex32("output_set_sha256", self.output_set_sha256)
        if not isinstance(self.fee_sat, int) or isinstance(self.fee_sat, bool) or self.fee_sat < 0:
            raise ReleasePolicyError("fee_sat must be a non-negative integer")
        epoch = self.policy_epoch.strip()
        if not epoch or len(epoch) > 128:
            raise ReleasePolicyError("policy_epoch must be non-empty and at most 128 characters")
        signing_policy = _require_hex32("signing_policy_sha256", self.signing_policy_sha256)
        nonce = self.authorization_nonce.strip()
        if len(nonce) < 16 or len(nonce) > 128:
            raise ReleasePolicyError("authorization_nonce must be 16..128 characters")
        try:
            expiry = dt.datetime.fromisoformat(self.expires_at.replace("Z", "+00:00"))
        except Exception as exc:
            raise ReleasePolicyError("expires_at must be an offset-aware ISO-8601 timestamp") from exc
        if expiry.tzinfo is None:
            raise ReleasePolicyError("expires_at must include a timezone offset")
        expiry_text = expiry.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")
        payload = {
            "schema": "WS-BITCOIN-RELEASE-INTENT-V2",
            "network": network,
            "unsigned_tx_sha256": unsigned_tx,
            "input_set_sha256": input_set,
            "output_set_sha256": output_set,
            "fee_sat": self.fee_sat,
            "policy_epoch": epoch,
            "signing_policy_sha256": signing_policy,
            "authorization_nonce": nonce,
            "expires_at": expiry_text,
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")

    @property
    def intent_sha256(self) -> str:
        return hashlib.sha256(self.canonical_bytes()).hexdigest()


@dataclass(frozen=True)
class PqReleaseAttestation:
    intent_sha256: str
    pq_algorithm: str
    pq_key_fingerprint_sha256: str
    pq_signature_b64url: str
    provider_operation_id: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_pq_release_attestation_from_provider_result(*, intent: BitcoinReleaseIntent, descriptor: Any, result: Any) -> PqReleaseAttestation:
    """Construct an attestation only from a result bound to this exact intent/context.

    ``descriptor`` and ``result`` are intentionally duck-typed to avoid coupling the
    policy module to one provider implementation while still enforcing the fields
    exposed by the Worldshepherd AWS KMS provider.
    """
    try:
        from .aws_kms_provider import ProviderState, provider_operation_id
        key_arn = descriptor.key_arn
        key_fp = descriptor.public_key_der_sha256
        algorithm = result.algorithm
        signature = result.signature_b64url
        state = result.state
        operation_id = result.operation_id
        result_key_arn = result.key_arn
        result_message_sha256 = result.message_sha256
        result_context_sha256 = result.context_sha256
    except Exception as exc:
        raise ReleasePolicyError("provider descriptor/result is missing required binding fields") from exc
    if state != ProviderState.SIGNED:
        raise ReleasePolicyError("provider result is not in SIGNED state")
    if algorithm != "ML_DSA_SHAKE_256" or not signature:
        raise ReleasePolicyError("provider result does not contain an ML-DSA signature")
    _require_hex32("pq_key_fingerprint_sha256", key_fp)
    intent_bytes = intent.canonical_bytes()
    if result_key_arn != key_arn:
        raise ReleasePolicyError("provider result key ARN does not match descriptor")
    if result_message_sha256 != hashlib.sha256(intent_bytes).hexdigest():
        raise ReleasePolicyError("provider result message hash does not match release intent")
    if result_context_sha256 != hashlib.sha256(RELEASE_ATTESTATION_CONTEXT).hexdigest():
        raise ReleasePolicyError("provider result context hash does not match release authorization context")
    expected_op = provider_operation_id(
        key_arn=key_arn,
        message=intent_bytes,
        context=RELEASE_ATTESTATION_CONTEXT,
    )
    if operation_id != expected_op:
        raise ReleasePolicyError("provider operation ID is not bound to this release intent/context")
    return PqReleaseAttestation(
        intent_sha256=intent.intent_sha256,
        pq_algorithm=algorithm,
        pq_key_fingerprint_sha256=key_fp,
        pq_signature_b64url=signature,
        provider_operation_id=operation_id,
    )


def authorize_release(
    *,
    intent: BitcoinReleaseIntent,
    policy_state: CryptoPolicyState,
    pq_attestation: PqReleaseAttestation | None,
    pq_signature_verifier: Callable[[bytes, bytes, bytes], bool] | None = None,
    pq_quorum_report: dict[str, Any] | None = None,
    now: dt.datetime | None = None,
) -> dict[str, Any]:
    digest = intent.intent_sha256
    try:
        expiry = dt.datetime.fromisoformat(intent.expires_at.replace("Z", "+00:00"))
    except Exception as exc:  # canonical_bytes already validates, retained defensively
        raise ReleasePolicyError("release intent expiry is invalid") from exc
    current = (now or dt.datetime.now(dt.timezone.utc)).astimezone(dt.timezone.utc)
    if current >= expiry.astimezone(dt.timezone.utc):
        raise ReleasePolicyError("release intent has expired")
    requires_pq = policy_state in {
        CryptoPolicyState.HYBRID_REQUIRED,
        CryptoPolicyState.PQ_REQUIRED,
        CryptoPolicyState.CLASSICAL_REJECTED,
    }
    if policy_state == CryptoPolicyState.CLASSICAL_REJECTED:
        raise ReleasePolicyError("classical Bitcoin release is disabled in CLASSICAL_REJECTED state")
    if policy_state == CryptoPolicyState.PQ_REQUIRED:
        # A detached PQ authorization does not make a Bitcoin consensus spend PQ-safe.
        raise ReleasePolicyError("PQ_REQUIRED cannot authorize a Bitcoin spend until an activated PQ consensus signature/output path exists")
    quorum_verified = False
    if pq_quorum_report is not None:
        if pq_quorum_report.get("satisfied") is not True:
            raise ReleasePolicyError("PQ provider quorum report is not satisfied")
        if str(pq_quorum_report.get("intent_sha256", "")).lower() != digest:
            raise ReleasePolicyError("PQ provider quorum report is bound to a different release intent")
        if int(pq_quorum_report.get("verified_count", 0)) < 1:
            raise ReleasePolicyError("PQ provider quorum report contains no verified provider")
        quorum_verified = True
    if requires_pq and pq_attestation is None and not quorum_verified:
        raise ReleasePolicyError("verified PQ release authorization is required by current policy")
    pq_signature_verified = False
    if pq_attestation is not None:
        if _require_hex32("intent_sha256", pq_attestation.intent_sha256) != digest:
            raise ReleasePolicyError("PQ attestation is not bound to the exact release intent")
        if pq_attestation.pq_algorithm != "ML_DSA_SHAKE_256":
            raise ReleasePolicyError("unexpected PQ attestation algorithm")
        _require_hex32("pq_key_fingerprint_sha256", pq_attestation.pq_key_fingerprint_sha256)
        signature = _decode_b64url_nonempty(pq_attestation.pq_signature_b64url)
        if _PROVIDER_OP_RE.fullmatch(pq_attestation.provider_operation_id) is None:
            raise ReleasePolicyError("invalid provider operation ID")
        if pq_signature_verifier is None:
            raise ReleasePolicyError("PQ attestation signature must be cryptographically verified before release authorization")
        try:
            pq_signature_verified = bool(pq_signature_verifier(intent.canonical_bytes(), RELEASE_ATTESTATION_CONTEXT, signature))
        except Exception as exc:
            raise ReleasePolicyError("PQ attestation verifier failed") from exc
        if not pq_signature_verified:
            raise ReleasePolicyError("PQ attestation signature verification failed")
    return {
        "schema": "WS-BITCOIN-RELEASE-AUTHORIZATION-V2",
        "policy_state": policy_state.value,
        "intent_sha256": digest,
        "pq_attestation_present": pq_attestation is not None,
        "pq_signature_verified": pq_signature_verified,
        "pq_provider_quorum_present": pq_quorum_report is not None,
        "pq_provider_quorum_verified": quorum_verified,
        "pq_provider_quorum_sha256": None if pq_quorum_report is None else pq_quorum_report.get("quorum_sha256"),
        "authorized_for_local_signing_workflow": True,
        "bitcoin_consensus_pq_security_established": False,
        "transaction_broadcast_authorized": False,
        "mainnet_authority": False,
    }

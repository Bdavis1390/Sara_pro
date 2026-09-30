"""Externally verified runtime/TEE attestation binding.

This module intentionally does not claim to parse or validate a vendor's native TEE
attestation document.  Instead it verifies an Ed25519-signed verdict from a trusted
attestation verifier and binds that verdict to a provider, key, measurement, nonce,
and validity window.  Deployments can place the vendor-specific verifier on the other
side of this interface without teaching the signing process to trust opaque strings.
"""
from __future__ import annotations

import base64
import datetime as dt
import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Mapping, Sequence

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives import serialization


class RuntimeAttestationError(RuntimeError):
    pass


def _b64u(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _unb64(text: str) -> bytes:
    try:
        b = text.encode("ascii")
        return base64.b64decode(b + b"=" * (-len(b) % 4), altchars=b"-_", validate=True)
    except Exception as exc:
        raise RuntimeAttestationError("invalid base64url runtime-attestation field") from exc


def _parse_time(value: str) -> dt.datetime:
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception as exc:
        raise RuntimeAttestationError("runtime-attestation timestamp must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise RuntimeAttestationError("runtime-attestation timestamp requires timezone offset")
    return parsed.astimezone(dt.timezone.utc)


def _hex32(name: str, value: str) -> str:
    text = value.lower()
    if len(text) != 64 or any(c not in "0123456789abcdef" for c in text):
        raise RuntimeAttestationError(f"{name} must be 32-byte hex")
    return text


@dataclass(frozen=True)
class RuntimeAttestationStatement:
    verifier_id: str
    provider_id: str
    key_fingerprint_sha256: str
    runtime_type: str
    measurement_sha256: str
    nonce: str
    issued_at: str
    expires_at: str
    verdict: str = "PASS"

    def canonical_bytes(self) -> bytes:
        if not self.verifier_id or not self.provider_id or not self.runtime_type:
            raise RuntimeAttestationError("verifier_id, provider_id and runtime_type are required")
        if len(self.nonce) < 16 or len(self.nonce) > 128:
            raise RuntimeAttestationError("runtime-attestation nonce must be 16..128 characters")
        if self.verdict != "PASS":
            raise RuntimeAttestationError("only an explicit PASS verifier verdict is accepted")
        issued, expires = _parse_time(self.issued_at), _parse_time(self.expires_at)
        if expires <= issued:
            raise RuntimeAttestationError("runtime-attestation expiry must follow issue time")
        payload = {
            "schema": "WS-QCRYPTO-RUNTIME-ATTESTATION-V1",
            "verifier_id": self.verifier_id,
            "provider_id": self.provider_id,
            "key_fingerprint_sha256": _hex32("key_fingerprint_sha256", self.key_fingerprint_sha256),
            "runtime_type": self.runtime_type,
            "measurement_sha256": _hex32("measurement_sha256", self.measurement_sha256),
            "nonce": self.nonce,
            "issued_at": issued.isoformat().replace("+00:00", "Z"),
            "expires_at": expires.isoformat().replace("+00:00", "Z"),
            "verdict": self.verdict,
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()

    @property
    def statement_sha256(self) -> str:
        return hashlib.sha256(self.canonical_bytes()).hexdigest()


@dataclass(frozen=True)
class SignedRuntimeAttestation:
    statement: RuntimeAttestationStatement
    verifier_public_key_b64url: str
    signature_b64url: str

    def to_dict(self) -> dict:
        return {"statement": asdict(self.statement), "verifier_public_key_b64url": self.verifier_public_key_b64url, "signature_b64url": self.signature_b64url}


def sign_runtime_attestation(statement: RuntimeAttestationStatement, private_key: Ed25519PrivateKey) -> SignedRuntimeAttestation:
    pub = private_key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return SignedRuntimeAttestation(statement, _b64u(pub), _b64u(private_key.sign(statement.canonical_bytes())))


def verify_runtime_attestation(
    attestation: SignedRuntimeAttestation,
    *,
    trusted_verifiers: Mapping[str, bytes],
    allowed_measurements: Mapping[str, Sequence[str]],
    expected_provider_id: str,
    expected_key_fingerprint_sha256: str,
    expected_nonce: str,
    now: dt.datetime | None = None,
) -> dict:
    st = attestation.statement
    if st.provider_id != expected_provider_id:
        raise RuntimeAttestationError("runtime attestation is bound to a different provider")
    if _hex32("key_fingerprint_sha256", st.key_fingerprint_sha256) != _hex32("expected key fingerprint", expected_key_fingerprint_sha256):
        raise RuntimeAttestationError("runtime attestation is bound to a different key")
    if st.nonce != expected_nonce:
        raise RuntimeAttestationError("runtime-attestation nonce does not match the release workflow")
    current = (now or dt.datetime.now(dt.timezone.utc)).astimezone(dt.timezone.utc)
    issued, expires = _parse_time(st.issued_at), _parse_time(st.expires_at)
    if current < issued or current >= expires:
        raise RuntimeAttestationError("runtime attestation is outside its validity window")
    trusted = trusted_verifiers.get(st.verifier_id)
    if trusted is None:
        raise RuntimeAttestationError("runtime-attestation verifier is not trusted")
    supplied = _unb64(attestation.verifier_public_key_b64url)
    if supplied != bytes(trusted):
        raise RuntimeAttestationError("runtime-attestation verifier key does not match registry")
    try:
        Ed25519PublicKey.from_public_bytes(supplied).verify(_unb64(attestation.signature_b64url), st.canonical_bytes())
    except (ValueError, InvalidSignature) as exc:
        raise RuntimeAttestationError("runtime-attestation verifier signature is invalid") from exc
    allowed = {_hex32("allowed measurement", x) for x in allowed_measurements.get(st.runtime_type, ())}
    measurement = _hex32("measurement_sha256", st.measurement_sha256)
    if measurement not in allowed:
        raise RuntimeAttestationError("runtime measurement is not approved for this runtime type")
    return {
        "schema": "WS-QCRYPTO-RUNTIME-ATTESTATION-VERIFICATION-V1",
        "verifier_id": st.verifier_id,
        "provider_id": st.provider_id,
        "key_fingerprint_sha256": st.key_fingerprint_sha256.lower(),
        "runtime_type": st.runtime_type,
        "measurement_sha256": measurement,
        "statement_sha256": st.statement_sha256,
        "verified": True,
        "native_vendor_attestation_claim": False,
    }

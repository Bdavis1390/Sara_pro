"""WS-QPOS-2 standards-backed post-quantum signature interoperability probes.

This module exercises ephemeral, zero-value validator-authorization envelopes with
NIST-standardized post-quantum signature families through the pinned pqcrypto
backend used by CI. It is deliberately not a wallet, validator client, remote
signer, custody system, or production consensus implementation.

A PASS establishes only that the tested backend can generate, sign and verify the
canonical WS-QPOS authorization envelope and rejects modified/wrong-key cases in
this environment. It does not prove the cryptographic primitive, backend audit
status, side-channel resistance, production consensus safety, or chain readiness.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import importlib
import json
from typing import Any


SCHEMES: dict[str, str] = {
    "ML-DSA-65": "pqcrypto.sign.ml_dsa_65",
    "SLH-DSA-SHA2-128s": "pqcrypto.sign.slh_dsa_sha2_128s",
}

CONTEXT = b"WS-QPOS-2"


@dataclass(frozen=True)
class ValidatorAuthorizationEnvelope:
    validator_id: str
    chain_family: str
    migration_epoch: int
    purpose: str
    economic_state_digest: str
    previous_credential_fingerprint: str

    def canonical_bytes(self) -> bytes:
        return json.dumps(
            asdict(self),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")


@dataclass(frozen=True)
class InteropResult:
    scheme: str
    backend_module: str
    public_key_bytes: int
    signature_bytes: int
    message_sha256: str
    public_key_fingerprint: str
    valid_signature_verified: bool
    tampered_message_rejected: bool
    wrong_key_rejected: bool
    secret_material_retained: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _module_for(scheme: str):
    try:
        module_name = SCHEMES[scheme]
    except KeyError as exc:
        raise ValueError(f"unsupported WS-QPOS-2 scheme: {scheme}") from exc
    return module_name, importlib.import_module(module_name)


def _verify_rejects(module, public_key: bytes, message: bytes, signature: bytes) -> bool:
    try:
        module.verify(public_key, message, signature, CONTEXT)
    except Exception:
        return True
    return False


def run_interop_probe(scheme: str, envelope: ValidatorAuthorizationEnvelope) -> InteropResult:
    """Run an ephemeral sign/verify/tamper/wrong-key probe for one PQ scheme."""

    module_name, module = _module_for(scheme)
    message = envelope.canonical_bytes()

    public_key, secret_key = module.keygen()
    signature = module.sign(secret_key, message, CONTEXT)
    module.verify(public_key, message, signature, CONTEXT)

    tampered = message + b"\x00"
    tampered_rejected = _verify_rejects(module, public_key, tampered, signature)

    wrong_public_key, _wrong_secret_key = module.keygen()
    wrong_key_rejected = _verify_rejects(module, wrong_public_key, message, signature)

    # Never return, serialize, log or retain secret-key bytes. Local references are
    # dropped before returning the evidence object.
    secret_key = None
    _wrong_secret_key = None

    return InteropResult(
        scheme=scheme,
        backend_module=module_name,
        public_key_bytes=len(public_key),
        signature_bytes=len(signature),
        message_sha256=sha256(message).hexdigest(),
        public_key_fingerprint=sha256(public_key).hexdigest(),
        valid_signature_verified=True,
        tampered_message_rejected=tampered_rejected,
        wrong_key_rejected=wrong_key_rejected,
        secret_material_retained=False,
    )


def run_all_interop_probes() -> tuple[InteropResult, ...]:
    envelope = ValidatorAuthorizationEnvelope(
        validator_id="ws-qpos-zero-value-validator",
        chain_family="GENERIC_POS",
        migration_epoch=1,
        purpose="POST_QUANTUM_CREDENTIAL_REGISTRATION_TEST_ONLY",
        economic_state_digest=sha256(b"zero-value-economic-state").hexdigest(),
        previous_credential_fingerprint=sha256(b"classical-test-credential").hexdigest(),
    )
    results = tuple(run_interop_probe(scheme, envelope) for scheme in SCHEMES)
    for result in results:
        if not (
            result.valid_signature_verified
            and result.tampered_message_rejected
            and result.wrong_key_rejected
            and not result.secret_material_retained
        ):
            raise AssertionError(f"PQ interoperability probe failed for {result.scheme}")
    return results

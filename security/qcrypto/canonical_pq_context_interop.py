"""Ephemeral PQ signature interoperability for the canonical authority context.

This module proves that a canonical Worldshepherd QCRYPTO context commitment can
be signed and verified with the pinned PQ backend used by CI, while signatures
fail under message tampering, wrong-key verification, and cross-context replay.

The probe uses ephemeral test keys only.  It is not a wallet, transaction signer,
remote signer, custody service, validator client, or live-value authorization
path.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import importlib
from typing import Any

from security.qcrypto.canonical_pq_signing_context import CanonicalSigningContextDecision
from security.qcrypto.pq_signature_interop import SCHEMES


SIGNATURE_CONTEXT = b"WS-QCRYPTO-CANONICAL-V1"


@dataclass(frozen=True)
class CanonicalPQInteropResult:
    scheme: str
    backend_module: str
    canonical_context_digest: str
    public_key_bytes: int
    signature_bytes: int
    public_key_fingerprint: str
    valid_signature_verified: bool
    tampered_context_rejected: bool
    cross_context_replay_rejected: bool
    wrong_key_rejected: bool
    test_signature_generated: bool
    secret_material_retained: bool
    live_transaction_signed: bool = False
    live_value_authorized: bool = False
    execution_authority: bool = False
    claim_boundary: str = (
        "Ephemeral canonical-context signature interoperability only; this does not "
        "authorize or sign a live transaction, establish custody, prove production "
        "protocol integration, or establish end-to-end post-quantum security."
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _module_for(scheme: str):
    try:
        module_name = SCHEMES[scheme]
    except KeyError as exc:
        raise ValueError(f"unsupported canonical PQ interop scheme: {scheme}") from exc
    return module_name, importlib.import_module(module_name)


def _context_message(decision: CanonicalSigningContextDecision) -> bytes:
    if not decision.ready or not decision.context_digest:
        raise ValueError("canonical signing context must be ready before PQ interop")
    if len(decision.context_digest) != 64:
        raise ValueError("canonical context digest must be SHA-256 hexadecimal text")
    try:
        return bytes.fromhex(decision.context_digest)
    except ValueError as exc:
        raise ValueError("canonical context digest is not hexadecimal") from exc


def _verify_rejects(module, public_key: bytes, message: bytes, signature: bytes) -> bool:
    try:
        module.verify(public_key, message, signature, SIGNATURE_CONTEXT)
    except Exception:
        return True
    return False


def run_canonical_context_probe(
    scheme: str,
    decision: CanonicalSigningContextDecision,
    alternate_decision: CanonicalSigningContextDecision,
) -> CanonicalPQInteropResult:
    """Sign one canonical commitment and prove fail-closed verification boundaries."""

    message = _context_message(decision)
    alternate_message = _context_message(alternate_decision)
    if alternate_message == message:
        raise ValueError("alternate canonical context must produce a distinct commitment")

    module_name, module = _module_for(scheme)
    public_key, secret_key = module.keygen()
    signature = module.sign(secret_key, message, SIGNATURE_CONTEXT)
    module.verify(public_key, message, signature, SIGNATURE_CONTEXT)

    tampered = bytearray(message)
    tampered[-1] ^= 0x01
    tampered_rejected = _verify_rejects(module, public_key, bytes(tampered), signature)
    cross_context_rejected = _verify_rejects(module, public_key, alternate_message, signature)

    wrong_public_key, wrong_secret_key = module.keygen()
    wrong_key_rejected = _verify_rejects(module, wrong_public_key, message, signature)

    public_key_fingerprint = sha256(public_key).hexdigest()
    public_key_bytes = len(public_key)
    signature_bytes = len(signature)

    # Drop all secret-key references before producing evidence.  No secret-key bytes
    # are returned, serialized, logged, or persisted by this module.
    secret_key = None
    wrong_secret_key = None

    return CanonicalPQInteropResult(
        scheme=scheme,
        backend_module=module_name,
        canonical_context_digest=decision.context_digest,
        public_key_bytes=public_key_bytes,
        signature_bytes=signature_bytes,
        public_key_fingerprint=public_key_fingerprint,
        valid_signature_verified=True,
        tampered_context_rejected=tampered_rejected,
        cross_context_replay_rejected=cross_context_rejected,
        wrong_key_rejected=wrong_key_rejected,
        test_signature_generated=True,
        secret_material_retained=False,
    )


def assert_probe(result: CanonicalPQInteropResult) -> None:
    if not (
        result.valid_signature_verified
        and result.tampered_context_rejected
        and result.cross_context_replay_rejected
        and result.wrong_key_rejected
        and result.test_signature_generated
        and not result.secret_material_retained
        and not result.live_transaction_signed
        and not result.live_value_authorized
        and not result.execution_authority
    ):
        raise AssertionError(f"canonical PQ context interop failed for {result.scheme}")


def run_all_canonical_context_probes(
    decision: CanonicalSigningContextDecision,
    alternate_decision: CanonicalSigningContextDecision,
) -> tuple[CanonicalPQInteropResult, ...]:
    results = tuple(
        run_canonical_context_probe(scheme, decision, alternate_decision)
        for scheme in SCHEMES
    )
    for result in results:
        assert_probe(result)
    return results

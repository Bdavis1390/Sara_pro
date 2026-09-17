"""Opaque-key signer provider abstraction for the external custody domain.

The custody process receives only an opaque key handle, public key/fingerprint, stable
provider operation ID, and reconciliation state. Private-key bytes are never part of
this interface.

The reference provider is CI software only. Production providers may use a different
FIPS 204 transport profile (for example, a cloud KMS API that exposes pure ML-DSA but
not the optional ML-DSA context parameter). The verification mode is therefore an
explicit, signed provider property instead of an implicit implementation detail.
"""
from __future__ import annotations

import base64
import hashlib
from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.mldsa import MLDSA65PrivateKey, MLDSA65PublicKey


PROVIDER_CONTEXT = b"WS-QCRYPTO-OPAQUE-PROVIDER-V1"
_RAW_FRAME_PREFIX = b"WS-QCRYPTO-MLDSA-RAW-FRAMED-CONTEXT-V1\x00"


class ProviderError(RuntimeError):
    pass


class ProviderConflict(ProviderError):
    pass


class ProviderAmbiguousOutcome(ProviderError):
    def __init__(self, operation_id: str, message: str = "provider signing outcome is ambiguous") -> None:
        super().__init__(message)
        self.operation_id = operation_id


class ProviderState(str, Enum):
    SIGNED = "SIGNED"
    PENDING = "PENDING"
    NOT_FOUND_SAFE_TO_RETRY = "NOT_FOUND_SAFE_TO_RETRY"
    INDETERMINATE = "INDETERMINATE"


class ProviderVerificationMode(str, Enum):
    """How the provider cryptographically binds the Worldshepherd domain context."""

    FIPS204_CONTEXT = "FIPS204_CONTEXT"
    RAW_FRAMED_CONTEXT = "RAW_FRAMED_CONTEXT"


@dataclass(frozen=True)
class ProviderResult:
    operation_id: str
    state: ProviderState
    key_handle: str
    algorithm: str
    message_sha256: str
    context_sha256: str
    signature_b64url: str | None = None
    safe_to_retry: bool = False
    verification_mode: str = ProviderVerificationMode.FIPS204_CONTEXT.value

    def to_dict(self) -> dict[str, object]:
        return {
            "operation_id": self.operation_id,
            "state": self.state.value,
            "key_handle": self.key_handle,
            "algorithm": self.algorithm,
            "message_sha256": self.message_sha256,
            "context_sha256": self.context_sha256,
            "signature_b64url": self.signature_b64url,
            "safe_to_retry": self.safe_to_retry,
            "verification_mode": self.verification_mode,
        }


class OpaqueSignerProvider(Protocol):
    @property
    def algorithm(self) -> str: ...

    @property
    def key_handle(self) -> str: ...

    @property
    def public_key_bytes(self) -> bytes: ...

    @property
    def fingerprint_sha256(self) -> str: ...

    @property
    def verification_mode(self) -> str: ...

    def begin_sign(self, operation_id: str, message: bytes, context: bytes) -> ProviderResult: ...

    def reconcile(self, operation_id: str) -> ProviderResult: ...


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _unb64(value: str) -> bytes:
    raw = value.encode("ascii")
    return base64.b64decode(raw + b"=" * (-len(raw) % 4), altchars=b"-_", validate=True)


def provider_raw_framed_message(message: bytes, context: bytes) -> bytes:
    """Encode a context-bound message for providers without FIPS 204 ctx input.

    The provider signs this exact byte string using pure ML-DSA with an empty FIPS
    context. The original Worldshepherd context and payload remain unambiguously
    length-delimited inside the signed data, preserving domain separation without
    pretending the remote API supports the FIPS 204 context parameter.
    """
    if not isinstance(message, bytes) or not isinstance(context, bytes):
        raise ProviderError("provider message and context must be bytes")
    if len(context) > 65535:
        raise ProviderError("provider context is too large")
    if len(message) > (2**64 - 1):
        raise ProviderError("provider message is too large")
    return (
        _RAW_FRAME_PREFIX
        + len(context).to_bytes(2, "big")
        + context
        + len(message).to_bytes(8, "big")
        + message
    )


def provider_operation_id(*, key_handle: str, message: bytes, context: bytes) -> str:
    if not key_handle or not isinstance(key_handle, str):
        raise ProviderError("opaque key handle is required")
    binding = (
        b"WS-QCRYPTO-PROVIDER-OP-V1\x00"
        + key_handle.encode("utf-8")
        + b"\x00"
        + hashlib.sha256(context).digest()
        + hashlib.sha256(message).digest()
    )
    return "QCRYPTO-PROVIDER-" + hashlib.sha256(binding).hexdigest()


def verify_provider_result(
    result: ProviderResult,
    *,
    public_key_bytes: bytes,
    message: bytes,
    context: bytes,
) -> bool:
    if result.state is not ProviderState.SIGNED or not result.signature_b64url:
        return False
    if result.algorithm != "ML-DSA-65":
        return False
    if result.message_sha256 != hashlib.sha256(message).hexdigest():
        return False
    if result.context_sha256 != hashlib.sha256(context).hexdigest():
        return False
    try:
        mode = ProviderVerificationMode(result.verification_mode)
        signature = _unb64(result.signature_b64url)
        public = MLDSA65PublicKey.from_public_bytes(public_key_bytes)
        if mode is ProviderVerificationMode.FIPS204_CONTEXT:
            public.verify(signature, message, context)
        elif mode is ProviderVerificationMode.RAW_FRAMED_CONTEXT:
            public.verify(signature, provider_raw_framed_message(message, context), b"")
        else:  # pragma: no cover - enum exhaustiveness guard
            return False
    except (InvalidSignature, ValueError, TypeError, ProviderError):
        return False
    return True


class ReferenceOpaqueMlDsa65Provider:
    """CI provider that never exposes its private key through the provider API.

    ``ack_loss_once=True`` models the important case where the provider commits a
    valid signature but the caller loses the acknowledgement. Reconciliation then
    returns the committed SIGNED result using the same stable operation ID.
    """

    def __init__(
        self,
        *,
        key_handle: str = "ref-hsm://qcrypto/ml-dsa-65/ci-key-1",
        ack_loss_once: bool = False,
    ) -> None:
        if not key_handle or "private" in key_handle.lower():
            raise ProviderError("reference opaque key handle is invalid")
        self._key_handle = key_handle
        self._private = MLDSA65PrivateKey.generate()
        self._public = self._private.public_key().public_bytes(
            serialization.Encoding.Raw,
            serialization.PublicFormat.Raw,
        )
        self._operations: dict[str, ProviderResult] = {}
        self._semantic: dict[str, tuple[str, str]] = {}
        self._ack_loss_once = ack_loss_once
        self._ack_loss_used = False
        self.invocation_count = 0

    @property
    def algorithm(self) -> str:
        return "ML-DSA-65"

    @property
    def key_handle(self) -> str:
        return self._key_handle

    @property
    def public_key_bytes(self) -> bytes:
        return self._public

    @property
    def fingerprint_sha256(self) -> str:
        return hashlib.sha256(self._public).hexdigest()

    @property
    def verification_mode(self) -> str:
        return ProviderVerificationMode.FIPS204_CONTEXT.value

    def begin_sign(self, operation_id: str, message: bytes, context: bytes) -> ProviderResult:
        expected = provider_operation_id(key_handle=self.key_handle, message=message, context=context)
        if operation_id != expected:
            raise ProviderConflict("provider operation ID does not match key/message/context binding")
        message_digest = hashlib.sha256(message).hexdigest()
        context_digest = hashlib.sha256(context).hexdigest()
        prior_semantic = self._semantic.get(operation_id)
        if prior_semantic is not None and prior_semantic != (message_digest, context_digest):
            raise ProviderConflict("provider operation ID was reused with changed semantics")
        prior = self._operations.get(operation_id)
        if prior is not None:
            return prior

        self.invocation_count += 1
        signature = self._private.sign(message, context)
        result = ProviderResult(
            operation_id=operation_id,
            state=ProviderState.SIGNED,
            key_handle=self.key_handle,
            algorithm=self.algorithm,
            message_sha256=message_digest,
            context_sha256=context_digest,
            signature_b64url=_b64(signature),
            safe_to_retry=False,
            verification_mode=self.verification_mode,
        )
        self._semantic[operation_id] = (message_digest, context_digest)
        self._operations[operation_id] = result
        if self._ack_loss_once and not self._ack_loss_used:
            self._ack_loss_used = True
            raise ProviderAmbiguousOutcome(
                operation_id,
                "simulated provider acknowledgement loss after signature commit",
            )
        return result

    def reconcile(self, operation_id: str) -> ProviderResult:
        prior = self._operations.get(operation_id)
        if prior is not None:
            return prior
        return ProviderResult(
            operation_id=operation_id,
            state=ProviderState.NOT_FOUND_SAFE_TO_RETRY,
            key_handle=self.key_handle,
            algorithm=self.algorithm,
            message_sha256="",
            context_sha256="",
            signature_b64url=None,
            safe_to_retry=True,
            verification_mode=self.verification_mode,
        )


class OpaqueProviderReleaseSigner:
    """ReleaseSigner-compatible adapter backed by an opaque provider.

    A provider acknowledgement loss is surfaced as ``ProviderAmbiguousOutcome`` so
    the custody ledger can enter INDETERMINATE. The adapter exposes reconciliation
    separately; it never auto-retries a provider operation.
    """

    def __init__(self, provider: OpaqueSignerProvider) -> None:
        self.provider = provider
        self.last_operation_id: str | None = None

    @property
    def algorithm(self) -> str:
        return self.provider.algorithm

    @property
    def context(self) -> bytes:
        return PROVIDER_CONTEXT

    @property
    def fingerprint_sha256(self) -> str:
        return self.provider.fingerprint_sha256

    @property
    def public_key_bytes(self) -> bytes:
        return self.provider.public_key_bytes

    def sign_release(self, payload: bytes) -> bytes:
        operation_id = provider_operation_id(
            key_handle=self.provider.key_handle,
            message=payload,
            context=self.context,
        )
        self.last_operation_id = operation_id
        result = self.provider.begin_sign(operation_id, payload, self.context)
        if result.state is not ProviderState.SIGNED or not verify_provider_result(
            result,
            public_key_bytes=self.public_key_bytes,
            message=payload,
            context=self.context,
        ):
            raise ProviderError("provider did not return a valid signed release")
        return _unb64(result.signature_b64url or "")

    def reconcile_last(self, *, payload: bytes) -> ProviderResult:
        if self.last_operation_id is None:
            raise ProviderError("no provider operation has been attempted")
        result = self.provider.reconcile(self.last_operation_id)
        if result.state is ProviderState.SIGNED and not verify_provider_result(
            result,
            public_key_bytes=self.public_key_bytes,
            message=payload,
            context=self.context,
        ):
            raise ProviderError("reconciled provider signature failed verification")
        return result

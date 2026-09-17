"""AWS KMS ML-DSA-65 opaque signer provider.

This adapter targets a real AWS KMS asymmetric ML_DSA_65 SIGN_VERIFY key while
preserving the Worldshepherd FIPS-204 non-empty signature context. AWS KMS does
not expose a context parameter on Sign/Verify, so the adapter computes the
FIPS-204 64-byte message representative mu and uses MessageType=EXTERNAL_MU.

A returned signature is first verified by AWS KMS using the same key and mu, keeping
the security-relevant provider verification inside the KMS boundary. It is then
verified locally as an additional consistency check against the original message
and context. Neither fact makes Worldshepherd itself a FIPS-validated module.

Important recovery boundary: AWS KMS Sign does not provide caller-supplied
idempotency tokens or a signature-retrieval API keyed by a Worldshepherd operation
ID. Therefore an exception after the Sign request is issued is treated as an
ambiguous outcome. reconcile() never calls Sign again and returns INDETERMINATE.
This deliberately sacrifices automatic recovery rather than risking a second
provider signing operation under a consumed human authorization.
"""
from __future__ import annotations

import base64
import hashlib
from typing import Any, Protocol

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.mldsa import MLDSA65PublicKey

from .opaque_provider import (
    ProviderAmbiguousOutcome,
    ProviderError,
    ProviderResult,
    ProviderState,
    provider_operation_id,
    verify_provider_result,
)

_AWS_KMS_ALGORITHM = "ML_DSA_SHAKE_256"
_KEY_SPEC = "ML_DSA_65"
_KEY_USAGE = "SIGN_VERIFY"
_MAX_CONTEXT = 255


class KmsClient(Protocol):
    def describe_key(self, **kwargs: Any) -> dict[str, Any]: ...
    def get_public_key(self, **kwargs: Any) -> dict[str, Any]: ...
    def sign(self, **kwargs: Any) -> dict[str, Any]: ...
    def verify(self, **kwargs: Any) -> dict[str, Any]: ...


def fips204_external_mu(public_key_raw: bytes, message: bytes, context: bytes) -> bytes:
    """Compute the FIPS-204 pure-ML-DSA message representative for EXTERNAL_MU."""
    if len(public_key_raw) != 1952:
        raise ProviderError("ML-DSA-65 public key must be 1952 raw bytes")
    if len(context) > _MAX_CONTEXT:
        raise ProviderError("ML-DSA context exceeds the FIPS-204 255-byte limit")
    tr = hashlib.shake_256(public_key_raw).digest(64)
    formatted = b"\x00" + bytes((len(context),)) + context + message
    return hashlib.shake_256(tr + formatted).digest(64)


def _raw_mldsa65_public_key(der: bytes) -> bytes:
    try:
        public = serialization.load_der_public_key(der)
    except (TypeError, ValueError) as exc:
        raise ProviderError("AWS KMS returned an invalid DER public key") from exc
    if not isinstance(public, MLDSA65PublicKey):
        raise ProviderError("AWS KMS key is not ML-DSA-65")
    return public.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)


def _require_metadata(metadata: dict[str, Any], public: dict[str, Any]) -> tuple[str, bytes]:
    if metadata.get("KeySpec") != _KEY_SPEC:
        raise ProviderError("AWS KMS key spec must be ML_DSA_65")
    if metadata.get("KeyUsage") != _KEY_USAGE:
        raise ProviderError("AWS KMS key usage must be SIGN_VERIFY")
    if metadata.get("Enabled") is not True or metadata.get("KeyState") != "Enabled":
        raise ProviderError("AWS KMS key must be enabled")

    public_spec = public.get("KeySpec", public.get("CustomerMasterKeySpec"))
    if public_spec != _KEY_SPEC:
        raise ProviderError("AWS KMS public-key response is not ML_DSA_65")
    if public.get("KeyUsage") != _KEY_USAGE:
        raise ProviderError("AWS KMS public-key response is not SIGN_VERIFY")
    algorithms = public.get("SigningAlgorithms")
    if not isinstance(algorithms, list) or _AWS_KMS_ALGORITHM not in algorithms:
        raise ProviderError("AWS KMS key does not advertise ML_DSA_SHAKE_256")

    arn = metadata.get("Arn")
    der = public.get("PublicKey")
    if not isinstance(arn, str) or not arn.startswith("arn:"):
        raise ProviderError("AWS KMS key ARN is missing")
    if not isinstance(der, (bytes, bytearray)):
        raise ProviderError("AWS KMS public key bytes are missing")
    return arn, _raw_mldsa65_public_key(bytes(der))


class AwsKmsMlDsa65Provider:
    """OpaqueSignerProvider backed by an injected boto3-compatible AWS KMS client.

    No AWS credentials are accepted or stored by this object. Credential sourcing,
    IAM policy, VPC endpoints, region restrictions, and account controls remain the
    responsibility of the process that constructs the KMS client.
    """

    def __init__(self, *, kms_client: KmsClient, key_id: str) -> None:
        if not isinstance(key_id, str) or not key_id.strip():
            raise ProviderError("AWS KMS key_id is required")
        self._client = kms_client
        self._requested_key_id = key_id
        try:
            described = kms_client.describe_key(KeyId=key_id)
            metadata = described.get("KeyMetadata")
            public = kms_client.get_public_key(KeyId=key_id)
        except Exception as exc:
            raise ProviderError("AWS KMS key capability discovery failed") from exc
        if not isinstance(metadata, dict) or not isinstance(public, dict):
            raise ProviderError("AWS KMS capability response is invalid")
        self._key_handle, self._public = _require_metadata(metadata, public)
        self._fingerprint = hashlib.sha256(self._public).hexdigest()
        self._attempted_operations: set[str] = set()
        self.provider_verify_count = 0

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
        return self._fingerprint

    @property
    def provider_profile(self) -> dict[str, Any]:
        return {
            "provider": "AWS_KMS",
            "key_spec": _KEY_SPEC,
            "key_usage": _KEY_USAGE,
            "signing_algorithm": _AWS_KMS_ALGORITHM,
            "message_type": "EXTERNAL_MU",
            "key_handle": self.key_handle,
            "fips204_context_preserved_via_external_mu": True,
            "provider_side_verify_required": True,
            "provider_documentation_states_fips_140_3_level_3_hsm": True,
            "worldshepherd_fips_validation_established": False,
            "live_integration_established_by_this_profile": False,
        }

    def begin_sign(self, operation_id: str, message: bytes, context: bytes) -> ProviderResult:
        expected = provider_operation_id(
            key_handle=self.key_handle,
            message=message,
            context=context,
        )
        if operation_id != expected:
            raise ProviderError("AWS KMS operation ID does not match key/message/context binding")
        if operation_id in self._attempted_operations:
            raise ProviderAmbiguousOutcome(
                operation_id,
                "AWS KMS operation has already crossed the non-idempotent signing fence",
            )

        mu = fips204_external_mu(self.public_key_bytes, message, context)
        self._attempted_operations.add(operation_id)
        try:
            response = self._client.sign(
                KeyId=self.key_handle,
                Message=mu,
                MessageType="EXTERNAL_MU",
                SigningAlgorithm=_AWS_KMS_ALGORITHM,
            )
        except Exception as exc:
            raise ProviderAmbiguousOutcome(
                operation_id,
                "AWS KMS Sign outcome is ambiguous; automatic retry is forbidden",
            ) from exc

        if not isinstance(response, dict):
            raise ProviderAmbiguousOutcome(operation_id, "AWS KMS returned an invalid Sign response")
        signature = response.get("Signature")
        returned_key = response.get("KeyId")
        returned_algorithm = response.get("SigningAlgorithm")
        if not isinstance(signature, (bytes, bytearray)):
            raise ProviderAmbiguousOutcome(operation_id, "AWS KMS Sign response omitted signature bytes")
        if returned_key != self.key_handle or returned_algorithm != _AWS_KMS_ALGORITHM:
            raise ProviderAmbiguousOutcome(operation_id, "AWS KMS Sign response identity changed")
        signature_bytes = bytes(signature)

        # The authoritative production-provider verification remains within KMS.
        try:
            verification = self._client.verify(
                KeyId=self.key_handle,
                Message=mu,
                MessageType="EXTERNAL_MU",
                Signature=signature_bytes,
                SigningAlgorithm=_AWS_KMS_ALGORITHM,
            )
            self.provider_verify_count += 1
        except Exception as exc:
            raise ProviderAmbiguousOutcome(
                operation_id,
                "AWS KMS Verify failed after signing; custody remains indeterminate",
            ) from exc
        if not isinstance(verification, dict):
            raise ProviderAmbiguousOutcome(operation_id, "AWS KMS returned an invalid Verify response")
        if (
            verification.get("SignatureValid") is not True
            or verification.get("KeyId") != self.key_handle
            or verification.get("SigningAlgorithm") != _AWS_KMS_ALGORITHM
        ):
            raise ProviderAmbiguousOutcome(
                operation_id,
                "AWS KMS did not affirm the context-bound signature",
            )

        result = ProviderResult(
            operation_id=operation_id,
            state=ProviderState.SIGNED,
            key_handle=self.key_handle,
            algorithm=self.algorithm,
            message_sha256=hashlib.sha256(message).hexdigest(),
            context_sha256=hashlib.sha256(context).hexdigest(),
            signature_b64url=base64.urlsafe_b64encode(signature_bytes).rstrip(b"=").decode("ascii"),
            safe_to_retry=False,
        )
        # Defense-in-depth consistency check; KMS Verify above is the provider-side
        # acceptance condition for the production adapter.
        if not verify_provider_result(
            result,
            public_key_bytes=self.public_key_bytes,
            message=message,
            context=context,
        ):
            raise ProviderAmbiguousOutcome(
                operation_id,
                "AWS KMS signature failed local context-bound consistency verification",
            )
        return result

    def reconcile(self, operation_id: str) -> ProviderResult:
        # AWS KMS exposes no signature retrieval API keyed by our operation ID.
        # Critically, this method never calls Sign again.
        return ProviderResult(
            operation_id=operation_id,
            state=ProviderState.INDETERMINATE,
            key_handle=self.key_handle,
            algorithm=self.algorithm,
            message_sha256="",
            context_sha256="",
            signature_b64url=None,
            safe_to_retry=False,
        )

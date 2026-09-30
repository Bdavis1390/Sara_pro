"""AWS KMS ML-DSA-65 provider candidate for Worldshepherd QCRYPTO.

Security properties enforced by this version:
- AWS KMS owns the private key; there is no export operation.
- Production requires an HTTPS AWS KMS FIPS endpoint for the configured region.
- ML-DSA-65 / SIGN_VERIFY / Enabled and key/public-key identity are fail-closed.
- The exact KMS key ARN is pinned after descriptor load; aliases cannot retarget a sign.
- A durable operation journal is required in production and claimed before Sign.
- Each new signing operation makes at most one application-level KMS Sign call.
- Any ambiguous Sign outcome becomes durable INDETERMINATE and is never retried.
- Bitcoin/Ethereum transaction serialization, broadcast and mainnet authority remain absent.
"""
from __future__ import annotations

import base64
import hashlib
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol
from urllib.parse import urlparse

from .operation_journal import FileOperationJournal, OperationJournalConflict, OperationJournalError

DOMAIN = b"WS-QCRYPTO-AWS-KMS-MLDSA65-V1\x00"
SIGNING_ALGORITHM = "ML_DSA_SHAKE_256"
KEY_SPEC = "ML_DSA_65"
KEY_USAGE = "SIGN_VERIFY"
_MAX_RAW = 4096
_ACCOUNT_RE = re.compile(r"^[0-9]{12}$")


class AwsKmsProviderError(RuntimeError):
    pass


class AwsKmsProviderConflict(AwsKmsProviderError):
    pass


class ProviderAmbiguousOutcome(AwsKmsProviderError):
    def __init__(self, operation_id: str, message: str) -> None:
        super().__init__(message)
        self.operation_id = operation_id


class ProviderState(str, Enum):
    SIGNED = "SIGNED"
    INDETERMINATE = "INDETERMINATE"


@dataclass(frozen=True)
class ProviderResult:
    operation_id: str
    state: ProviderState
    key_arn: str
    algorithm: str
    message_sha256: str
    context_sha256: str
    signature_b64url: str | None
    aws_request_id: str | None
    safe_to_retry: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation_id": self.operation_id,
            "state": self.state.value,
            "key_arn": self.key_arn,
            "algorithm": self.algorithm,
            "message_sha256": self.message_sha256,
            "context_sha256": self.context_sha256,
            "signature_b64url": self.signature_b64url,
            "aws_request_id": self.aws_request_id,
            "safe_to_retry": self.safe_to_retry,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "ProviderResult":
        try:
            return cls(
                operation_id=str(raw["operation_id"]),
                state=ProviderState(str(raw["state"])),
                key_arn=str(raw["key_arn"]),
                algorithm=str(raw["algorithm"]),
                message_sha256=str(raw["message_sha256"]),
                context_sha256=str(raw["context_sha256"]),
                signature_b64url=None if raw.get("signature_b64url") is None else str(raw["signature_b64url"]),
                aws_request_id=None if raw.get("aws_request_id") is None else str(raw["aws_request_id"]),
                safe_to_retry=bool(raw.get("safe_to_retry", False)),
            )
        except Exception as exc:
            raise AwsKmsProviderError("durable journal contains invalid provider result") from exc


@dataclass(frozen=True)
class AwsKmsDescriptor:
    key_id: str
    key_arn: str
    aws_account_id: str
    region: str
    key_spec: str
    key_usage: str
    key_state: str
    enabled: bool
    signing_algorithm: str
    public_key_der_sha256: str
    public_key_der_b64url: str
    fips_endpoint_requested: bool
    endpoint_url: str
    private_key_export_supported: bool = False
    chain_native_signing_supported: bool = False
    transaction_broadcast_supported: bool = False
    mainnet_authority: bool = False

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


class KmsClient(Protocol):
    def describe_key(self, **kwargs: Any) -> dict[str, Any]: ...
    def get_public_key(self, **kwargs: Any) -> dict[str, Any]: ...
    def sign(self, **kwargs: Any) -> dict[str, Any]: ...
    def verify(self, **kwargs: Any) -> dict[str, Any]: ...


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _domain_message(message: bytes, context: bytes) -> bytes:
    if not isinstance(message, (bytes, bytearray)) or not isinstance(context, (bytes, bytearray)):
        raise AwsKmsProviderError("message and context must be bytes")
    if len(context) > 65535:
        raise AwsKmsProviderError("context is too long")
    payload = DOMAIN + len(context).to_bytes(2, "big") + bytes(context) + bytes(message)
    if len(payload) > _MAX_RAW:
        raise AwsKmsProviderError(
            "domain-separated RAW payload exceeds AWS KMS 4 KiB ML-DSA limit; "
            "EXTERNAL_MU support is intentionally not enabled in this candidate"
        )
    return payload


def provider_operation_id(*, key_arn: str, message: bytes, context: bytes) -> str:
    if not isinstance(key_arn, str) or not key_arn.startswith("arn:"):
        raise AwsKmsProviderError("validated AWS KMS key ARN is required")
    payload = (
        b"WS-QCRYPTO-AWS-KMS-OP-V1\x00"
        + key_arn.encode("utf-8")
        + b"\x00"
        + hashlib.sha256(context).digest()
        + hashlib.sha256(message).digest()
    )
    return "QCRYPTO-AWS-KMS-" + hashlib.sha256(payload).hexdigest()


def _validate_fips_endpoint(endpoint_url: str, region: str) -> None:
    parsed = urlparse(endpoint_url)
    if parsed.scheme != "https" or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise AwsKmsProviderError("production KMS endpoint must be a clean HTTPS FIPS origin")
    host = (parsed.hostname or "").lower()
    expected = {
        f"kms-fips.{region}.amazonaws.com",
        f"kms-fips.{region}.api.aws",
    }
    if host not in expected:
        raise AwsKmsProviderError("production KMS client is not resolved to the configured region's AWS KMS FIPS endpoint")
    if parsed.port not in (None, 443):
        raise AwsKmsProviderError("production KMS FIPS endpoint must use the default TLS port")
    if parsed.path not in ("", "/"):
        raise AwsKmsProviderError("production KMS FIPS endpoint must not contain a path")


def _parse_kms_key_arn(arn: str) -> tuple[str, str, str, str]:
    parts = arn.split(":", 5)
    if len(parts) != 6 or parts[0] != "arn" or parts[2] != "kms":
        raise AwsKmsProviderError("KMS key ARN is invalid")
    partition, region, account, resource = parts[1], parts[3], parts[4], parts[5]
    # This recovery candidate intentionally supports the commercial AWS partition
    # only. Cross-partition endpoint rules must be implemented and tested before
    # aws-us-gov/aws-cn ARNs are accepted.
    if partition != "aws" or not region or not _ACCOUNT_RE.match(account) or not resource.startswith("key/"):
        raise AwsKmsProviderError("KMS key ARN fields are invalid or use an unsupported AWS partition")
    return partition, region, account, resource


class AwsKmsMlDsa65Provider:
    """Fail-closed AWS KMS ML-DSA-65 signer provider."""

    def __init__(
        self,
        *,
        kms_client: KmsClient,
        key_id: str,
        region: str,
        fips_endpoint_requested: bool,
        production_profile: bool = True,
        operation_journal: FileOperationJournal | None = None,
        refresh_descriptor_before_sign: bool = True,
    ) -> None:
        if production_profile and not fips_endpoint_requested:
            raise AwsKmsProviderError("production profile requires AWS KMS FIPS endpoint")
        if production_profile and operation_journal is None:
            raise AwsKmsProviderError("production profile requires a durable operation journal")
        if not key_id or not region:
            raise AwsKmsProviderError("key_id and region are required")
        self._client = kms_client
        self._key_id = key_id
        self._region = region
        self._fips_endpoint_requested = bool(fips_endpoint_requested)
        self._production_profile = bool(production_profile)
        self._journal = operation_journal
        self._refresh_descriptor_before_sign = bool(refresh_descriptor_before_sign)
        endpoint = getattr(getattr(kms_client, "meta", None), "endpoint_url", "")
        self._endpoint_url = str(endpoint or "")
        if production_profile:
            _validate_fips_endpoint(self._endpoint_url, region)
        self._descriptor = self._load_descriptor()
        self._completed: dict[str, ProviderResult] = {}

    @property
    def descriptor(self) -> AwsKmsDescriptor:
        return self._descriptor

    @property
    def algorithm(self) -> str:
        return SIGNING_ALGORITHM

    @property
    def key_handle(self) -> str:
        return self._descriptor.key_arn

    @property
    def public_key_der(self) -> bytes:
        raw = self._descriptor.public_key_der_b64url.encode("ascii")
        return base64.urlsafe_b64decode(raw + b"=" * (-len(raw) % 4))

    @property
    def fingerprint_sha256(self) -> str:
        return self._descriptor.public_key_der_sha256

    def _descriptor_components(self, key_reference: str) -> tuple[dict[str, Any], bytes, list[Any]]:
        metadata = self._client.describe_key(KeyId=key_reference).get("KeyMetadata")
        if not isinstance(metadata, dict):
            raise AwsKmsProviderError("DescribeKey omitted KeyMetadata")
        if metadata.get("KeySpec") != KEY_SPEC:
            raise AwsKmsProviderError("KMS key must use ML_DSA_65")
        if metadata.get("KeyUsage") != KEY_USAGE:
            raise AwsKmsProviderError("KMS key must use SIGN_VERIFY")
        if metadata.get("Enabled") is not True or metadata.get("KeyState") != "Enabled":
            raise AwsKmsProviderError("KMS key must be enabled")
        arn = metadata.get("Arn")
        if not isinstance(arn, str):
            raise AwsKmsProviderError("KMS key ARN is invalid")
        _, arn_region, arn_account, _ = _parse_kms_key_arn(arn)
        if arn_region != self._region:
            raise AwsKmsProviderError("KMS key ARN region does not match configured region")
        if str(metadata.get("AWSAccountId", "")) != arn_account:
            raise AwsKmsProviderError("KMS account metadata does not match key ARN")
        public = self._client.get_public_key(KeyId=arn)
        public_key = public.get("PublicKey")
        if not isinstance(public_key, (bytes, bytearray)) or not public_key:
            raise AwsKmsProviderError("GetPublicKey omitted public key bytes")
        algorithms = public.get("SigningAlgorithms")
        if not isinstance(algorithms, list) or SIGNING_ALGORITHM not in algorithms:
            raise AwsKmsProviderError("KMS key does not advertise ML_DSA_SHAKE_256")
        return metadata, bytes(public_key), algorithms

    def _load_descriptor(self) -> AwsKmsDescriptor:
        metadata, public_key, _ = self._descriptor_components(self._key_id)
        arn = str(metadata["Arn"])
        return AwsKmsDescriptor(
            key_id=str(metadata.get("KeyId", self._key_id)),
            key_arn=arn,
            aws_account_id=str(metadata.get("AWSAccountId", "")),
            region=self._region,
            key_spec=KEY_SPEC,
            key_usage=KEY_USAGE,
            key_state="Enabled",
            enabled=True,
            signing_algorithm=SIGNING_ALGORITHM,
            public_key_der_sha256=hashlib.sha256(public_key).hexdigest(),
            public_key_der_b64url=_b64(public_key),
            fips_endpoint_requested=self._fips_endpoint_requested,
            endpoint_url=self._endpoint_url,
        )

    def _assert_descriptor_unchanged(self) -> None:
        metadata, public_key, _ = self._descriptor_components(self._descriptor.key_arn)
        if metadata.get("Arn") != self._descriptor.key_arn:
            raise AwsKmsProviderConflict("KMS key ARN changed after provider initialization")
        if hashlib.sha256(public_key).hexdigest() != self._descriptor.public_key_der_sha256:
            raise AwsKmsProviderConflict("KMS public key changed after provider initialization")

    def _binding(self, message: bytes, context: bytes) -> dict[str, str]:
        return {
            "key_arn": self._descriptor.key_arn,
            "algorithm": SIGNING_ALGORITHM,
            "message_sha256": hashlib.sha256(message).hexdigest(),
            "context_sha256": hashlib.sha256(context).hexdigest(),
        }

    def begin_sign(self, operation_id: str, message: bytes, context: bytes) -> ProviderResult:
        expected = provider_operation_id(
            key_arn=self._descriptor.key_arn,
            message=message,
            context=context,
        )
        if operation_id != expected:
            raise AwsKmsProviderConflict("operation ID does not match KMS key/message/context binding")
        prior = self._completed.get(operation_id)
        if prior is not None:
            return prior
        payload = _domain_message(message, context)
        binding = self._binding(message, context)

        # Descriptor/public-key checks are read-only preflight operations. Perform
        # them before claiming the one-shot Sign operation so a transient DescribeKey
        # failure cannot poison the durable operation ID despite no Sign request ever
        # being sent. The actual Sign remains pinned to the immutable key ARN.
        if self._refresh_descriptor_before_sign:
            self._assert_descriptor_unchanged()

        created = True
        if self._journal is not None:
            try:
                record, created = self._journal.claim_for_sign(operation_id, binding)
            except (OperationJournalError, OperationJournalConflict) as exc:
                raise AwsKmsProviderConflict("durable operation journal rejected signing claim") from exc
            if not created:
                if record.state == "SIGNED" and record.result is not None:
                    result = ProviderResult.from_dict(record.result)
                    if (
                        result.operation_id != operation_id
                        or result.key_arn != self._descriptor.key_arn
                        or result.algorithm != SIGNING_ALGORITHM
                        or result.message_sha256 != binding["message_sha256"]
                        or result.context_sha256 != binding["context_sha256"]
                        or result.state != ProviderState.SIGNED
                        or not result.signature_b64url
                    ):
                        raise AwsKmsProviderConflict("durable signed result does not match the claimed signing binding")
                    self._completed[operation_id] = result
                    return result
                raise ProviderAmbiguousOutcome(
                    operation_id,
                    f"durable journal state {record.state} forbids a second KMS Sign call",
                )

        try:
            response = self._client.sign(
                KeyId=self._descriptor.key_arn,
                Message=payload,
                MessageType="RAW",
                SigningAlgorithm=SIGNING_ALGORITHM,
            )
        except Exception as exc:
            if self._journal is not None and created:
                self._journal.mark_indeterminate(operation_id, binding)
            raise ProviderAmbiguousOutcome(
                operation_id,
                "AWS KMS Sign outcome is ambiguous; automatic retry is forbidden",
            ) from exc
        response_key_id = response.get("KeyId")
        response_algorithm = response.get("SigningAlgorithm")
        if response_key_id != self._descriptor.key_arn or response_algorithm != SIGNING_ALGORITHM:
            if self._journal is not None and created:
                self._journal.mark_indeterminate(operation_id, binding)
            raise ProviderAmbiguousOutcome(
                operation_id,
                "AWS KMS Sign response identity/algorithm did not match the pinned request; retry is forbidden",
            )
        signature = response.get("Signature")
        if not isinstance(signature, (bytes, bytearray)) or not signature:
            if self._journal is not None and created:
                self._journal.mark_indeterminate(operation_id, binding)
            raise ProviderAmbiguousOutcome(
                operation_id,
                "AWS KMS Sign returned without a usable signature; automatic retry is forbidden",
            )
        request_id = None
        response_meta = response.get("ResponseMetadata")
        if isinstance(response_meta, dict) and isinstance(response_meta.get("RequestId"), str):
            request_id = response_meta["RequestId"]
        result = ProviderResult(
            operation_id=operation_id,
            state=ProviderState.SIGNED,
            key_arn=self._descriptor.key_arn,
            algorithm=SIGNING_ALGORITHM,
            message_sha256=binding["message_sha256"],
            context_sha256=binding["context_sha256"],
            signature_b64url=_b64(bytes(signature)),
            aws_request_id=request_id,
            safe_to_retry=False,
        )
        if self._journal is not None:
            try:
                self._journal.mark_signed(operation_id, binding, result.to_dict())
            except (OperationJournalError, OperationJournalConflict) as exc:
                # A signature may already exist remotely. If durable commit fails, never
                # imply the caller can simply sign again.
                raise ProviderAmbiguousOutcome(
                    operation_id,
                    "KMS signature succeeded but durable result commit failed; retry is forbidden",
                ) from exc
        self._completed[operation_id] = result
        return result

    def verify_with_kms(self, *, message: bytes, context: bytes, signature: bytes) -> bool:
        payload = _domain_message(message, context)
        response = self._client.verify(
            KeyId=self._descriptor.key_arn,
            Message=payload,
            MessageType="RAW",
            Signature=signature,
            SigningAlgorithm=SIGNING_ALGORITHM,
        )
        return response.get("SignatureValid") is True

    def reconcile(self, operation_id: str) -> ProviderResult:
        prior = self._completed.get(operation_id)
        if prior is not None:
            return prior
        if self._journal is not None:
            try:
                record = self._journal.get(operation_id)
            except OperationJournalError as exc:
                raise AwsKmsProviderError("unable to read durable operation journal") from exc
            if record is not None and record.state == "SIGNED" and record.result is not None:
                result = ProviderResult.from_dict(record.result)
                self._completed[operation_id] = result
                return result
        return ProviderResult(
            operation_id=operation_id,
            state=ProviderState.INDETERMINATE,
            key_arn=self._descriptor.key_arn,
            algorithm=SIGNING_ALGORITHM,
            message_sha256="",
            context_sha256="",
            signature_b64url=None,
            aws_request_id=None,
            safe_to_retry=False,
        )

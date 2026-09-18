from __future__ import annotations

import re
from typing import Any, Protocol

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .echo_checkpoint_signer import SIGNER_ALGORITHM, EchoCheckpointSignerError


AWS_KMS_ED25519_KEY_SPEC = "ECC_NIST_EDWARDS25519"
AWS_KMS_SIGNING_ALGORITHM = "ED25519_SHA_512"
AWS_KMS_KEY_USAGE = "SIGN_VERIFY"
_EVIDENCE_KEY_ID = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


class AwsKmsClient(Protocol):
    def get_public_key(self, **kwargs: Any) -> dict[str, Any]: ...

    def sign(self, **kwargs: Any) -> dict[str, Any]: ...


class AwsKmsCheckpointSignerError(EchoCheckpointSignerError):
    pass


class AwsKmsEd25519CheckpointSigner:
    """AWS KMS Ed25519 signer adapter without SDK ownership.

    The caller supplies a KMS-compatible client (for example a boto3 KMS client).
    This module intentionally does not load AWS credentials and does not add boto3
    as a mandatory SARA runtime dependency.
    """

    algorithm = SIGNER_ALGORITHM

    def __init__(
        self,
        *,
        client: AwsKmsClient,
        kms_key_id: str,
        evidence_key_id: str,
    ) -> None:
        if not isinstance(kms_key_id, str) or not kms_key_id.strip():
            raise AwsKmsCheckpointSignerError("AWS KMS key ID is required")
        if not isinstance(evidence_key_id, str) or not _EVIDENCE_KEY_ID.fullmatch(
            evidence_key_id
        ):
            raise AwsKmsCheckpointSignerError(
                "ECHO evidence key ID must be 1-128 safe identifier characters"
            )
        self._client = client
        self._requested_kms_key_id = kms_key_id.strip()
        self.key_id = evidence_key_id

        try:
            response = client.get_public_key(KeyId=self._requested_kms_key_id)
        except Exception as exc:
            raise AwsKmsCheckpointSignerError(
                "unable to read AWS KMS signing public key"
            ) from exc
        if response.get("KeySpec") != AWS_KMS_ED25519_KEY_SPEC:
            raise AwsKmsCheckpointSignerError(
                "AWS KMS key must use ECC_NIST_EDWARDS25519"
            )
        if response.get("KeyUsage") != AWS_KMS_KEY_USAGE:
            raise AwsKmsCheckpointSignerError(
                "AWS KMS key must use SIGN_VERIFY"
            )
        algorithms = response.get("SigningAlgorithms")
        if (
            not isinstance(algorithms, list)
            or AWS_KMS_SIGNING_ALGORITHM not in algorithms
        ):
            raise AwsKmsCheckpointSignerError(
                "AWS KMS key does not advertise ED25519_SHA_512 signing"
            )
        resolved = response.get("KeyId")
        if not isinstance(resolved, str) or not resolved:
            raise AwsKmsCheckpointSignerError(
                "AWS KMS public-key response is missing resolved KeyId"
            )
        public_der = response.get("PublicKey")
        if not isinstance(public_der, bytes) or not public_der:
            raise AwsKmsCheckpointSignerError(
                "AWS KMS public-key response is missing DER key material"
            )
        try:
            public = serialization.load_der_public_key(public_der)
        except (TypeError, ValueError) as exc:
            raise AwsKmsCheckpointSignerError(
                "AWS KMS public key is not valid DER SubjectPublicKeyInfo"
            ) from exc
        if not isinstance(public, Ed25519PublicKey):
            raise AwsKmsCheckpointSignerError(
                "AWS KMS public key is not Ed25519"
            )

        self._resolved_kms_key_id = resolved
        self._public_key_bytes = public.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )

    def public_key_bytes(self) -> bytes:
        return self._public_key_bytes

    def sign(self, message: bytes) -> bytes:
        if not isinstance(message, bytes) or not message:
            raise AwsKmsCheckpointSignerError(
                "AWS KMS signer requires non-empty canonical bytes"
            )
        try:
            response = self._client.sign(
                KeyId=self._resolved_kms_key_id,
                Message=message,
                MessageType="RAW",
                SigningAlgorithm=AWS_KMS_SIGNING_ALGORITHM,
            )
        except Exception as exc:
            raise AwsKmsCheckpointSignerError(
                "AWS KMS signing request failed"
            ) from exc
        resolved = response.get("KeyId")
        if resolved != self._resolved_kms_key_id:
            raise AwsKmsCheckpointSignerError(
                "AWS KMS signing response key identity changed"
            )
        algorithm = response.get("SigningAlgorithm")
        if algorithm != AWS_KMS_SIGNING_ALGORITHM:
            raise AwsKmsCheckpointSignerError(
                "AWS KMS signing response algorithm changed"
            )
        signature = response.get("Signature")
        if not isinstance(signature, bytes) or len(signature) != 64:
            raise AwsKmsCheckpointSignerError(
                "AWS KMS returned an invalid Ed25519 signature"
            )
        return signature

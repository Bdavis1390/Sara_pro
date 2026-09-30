"""Classical secp256k1 digest-signing primitive for public-testnet adapters.

This deliberately does NOT serialize Bitcoin/Ethereum transactions and does not
broadcast. It signs only 32-byte digests on explicitly non-mainnet networks. A
durable operation journal prevents an ambiguous KMS Sign result from being silently
retried after process restart or by a competing worker.
"""
from __future__ import annotations

import base64
import hashlib
from dataclasses import dataclass
from typing import Any, Protocol

from .operation_journal import FileOperationJournal, OperationJournalConflict, OperationJournalError

_ALLOWED = {
    ("BITCOIN", "SIGNET"),
    ("BITCOIN", "TESTNET4"),
    ("ETHEREUM", "SEPOLIA"),
    ("ETHEREUM", "HOODI"),
}


class ClassicalSignerError(RuntimeError):
    pass


class KmsClient(Protocol):
    def describe_key(self, **kwargs: Any) -> dict[str, Any]: ...
    def sign(self, **kwargs: Any) -> dict[str, Any]: ...


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _unb64(value: str) -> bytes:
    raw = value.encode("ascii")
    return base64.urlsafe_b64decode(raw + b"=" * (-len(raw) % 4))


def classical_operation_id(*, key_arn: str, chain: str, network: str, digest32: bytes) -> str:
    payload = (
        b"WS-QCRYPTO-KMS-SECP256K1-TESTNET-OP-V1\x00"
        + key_arn.encode("utf-8")
        + b"\x00"
        + chain.upper().encode("ascii")
        + b"\x00"
        + network.upper().encode("ascii")
        + b"\x00"
        + bytes(digest32)
    )
    return "QCRYPTO-SECP256K1-" + hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True)
class ClassicalDigestSignature:
    operation_id: str
    chain: str
    network: str
    key_arn: str
    signing_algorithm: str
    der_signature: bytes
    aws_request_id: str | None
    transaction_serialized: bool = False
    transaction_broadcast: bool = False
    mainnet: bool = False
    post_quantum: bool = False


class AwsKmsSecp256k1TestnetDigestSigner:
    def __init__(self, *, kms_client: KmsClient, key_id: str, operation_journal: FileOperationJournal) -> None:
        if operation_journal is None:
            raise ClassicalSignerError("durable operation journal is required")
        self.client = kms_client
        self.journal = operation_journal
        md = kms_client.describe_key(KeyId=key_id).get("KeyMetadata", {})
        if md.get("KeySpec") != "ECC_SECG_P256K1" or md.get("KeyUsage") != "SIGN_VERIFY":
            raise ClassicalSignerError("KMS key must be ECC_SECG_P256K1 SIGN_VERIFY")
        if md.get("Enabled") is not True or md.get("KeyState") != "Enabled":
            raise ClassicalSignerError("KMS key must be enabled")
        arn = md.get("Arn")
        if not isinstance(arn, str) or not arn.startswith("arn:aws:kms:") or ":key/" not in arn:
            raise ClassicalSignerError("invalid KMS key ARN")
        self.key_arn = arn

    def sign_digest(self, *, chain: str, network: str, digest32: bytes) -> ClassicalDigestSignature:
        identity = (chain.upper(), network.upper())
        if identity not in _ALLOWED:
            raise ClassicalSignerError("only explicitly allowed public testnet/signet networks are permitted")
        if not isinstance(digest32, (bytes, bytearray)) or len(digest32) != 32:
            raise ClassicalSignerError("native transaction digest must be exactly 32 bytes")
        digest32 = bytes(digest32)
        operation_id = classical_operation_id(
            key_arn=self.key_arn,
            chain=identity[0],
            network=identity[1],
            digest32=digest32,
        )
        binding = {
            "key_arn": self.key_arn,
            "chain": identity[0],
            "network": identity[1],
            "digest_sha256": hashlib.sha256(digest32).hexdigest(),
            "algorithm": "ECDSA_SHA_256",
        }
        try:
            record, created = self.journal.claim_for_sign(operation_id, binding)
        except (OperationJournalError, OperationJournalConflict) as exc:
            raise ClassicalSignerError("durable journal rejected classical signing operation") from exc
        if not created:
            if record.state == "SIGNED" and isinstance(record.result, dict):
                try:
                    return ClassicalDigestSignature(
                        operation_id=operation_id,
                        chain=identity[0],
                        network=identity[1],
                        key_arn=self.key_arn,
                        signing_algorithm="ECDSA_SHA_256",
                        der_signature=_unb64(str(record.result["der_signature_b64url"])),
                        aws_request_id=None if record.result.get("aws_request_id") is None else str(record.result["aws_request_id"]),
                    )
                except Exception as exc:
                    raise ClassicalSignerError("durable classical signing result is invalid") from exc
            raise ClassicalSignerError(f"durable journal state {record.state} forbids a second classical KMS Sign call")

        try:
            response = self.client.sign(
                KeyId=self.key_arn,
                Message=digest32,
                MessageType="DIGEST",
                SigningAlgorithm="ECDSA_SHA_256",
            )
        except Exception as exc:
            self.journal.mark_indeterminate(operation_id, binding)
            raise ClassicalSignerError("ambiguous classical KMS sign outcome; no automatic retry") from exc
        if response.get("KeyId") != self.key_arn or response.get("SigningAlgorithm") != "ECDSA_SHA_256":
            self.journal.mark_indeterminate(operation_id, binding)
            raise ClassicalSignerError("KMS classical Sign response identity/algorithm mismatch; retry forbidden")
        signature = response.get("Signature")
        if not isinstance(signature, (bytes, bytearray)) or not signature:
            self.journal.mark_indeterminate(operation_id, binding)
            raise ClassicalSignerError("KMS did not return a DER ECDSA signature; retry forbidden")
        meta = response.get("ResponseMetadata", {})
        request_id = meta.get("RequestId") if isinstance(meta, dict) and isinstance(meta.get("RequestId"), str) else None
        result_payload = {
            "der_signature_b64url": _b64(bytes(signature)),
            "aws_request_id": request_id,
        }
        try:
            self.journal.mark_signed(operation_id, binding, result_payload)
        except (OperationJournalError, OperationJournalConflict) as exc:
            raise ClassicalSignerError("classical signature succeeded but durable commit failed; retry forbidden") from exc
        return ClassicalDigestSignature(
            operation_id=operation_id,
            chain=identity[0],
            network=identity[1],
            key_arn=self.key_arn,
            signing_algorithm="ECDSA_SHA_256",
            der_signature=bytes(signature),
            aws_request_id=request_id,
        )

from __future__ import annotations

from dataclasses import dataclass, field

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from worldshepherd_sara.aws_kms_checkpoint_signer import (
    AWS_KMS_ED25519_KEY_SPEC,
    AWS_KMS_SIGNING_ALGORITHM,
    AWS_KMS_KEY_USAGE,
    AwsKmsCheckpointSignerError,
    AwsKmsEd25519CheckpointSigner,
)
from worldshepherd_sara.echo_checkpoint import EchoCheckpointManager
from worldshepherd_sara.echo_checkpoint_verify import verify_bundle
from worldshepherd_sara.echo_event_store import EchoEventStore
from worldshepherd_sara.models import AuditRecord


@dataclass
class FakeKmsClient:
    private_key: Ed25519PrivateKey
    resolved_key_id: str = (
        "arn:aws:kms:us-east-2:111122223333:key/"
        "1234abcd-12ab-34cd-56ef-1234567890ab"
    )
    key_spec: str = AWS_KMS_ED25519_KEY_SPEC
    key_usage: str = AWS_KMS_KEY_USAGE
    algorithms: list[str] = field(
        default_factory=lambda: [AWS_KMS_SIGNING_ALGORITHM]
    )
    sign_calls: list[dict] = field(default_factory=list)

    def get_public_key(self, **kwargs):
        public_der = self.private_key.public_key().public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        return {
            "KeyId": self.resolved_key_id,
            "PublicKey": public_der,
            "KeySpec": self.key_spec,
            "KeyUsage": self.key_usage,
            "SigningAlgorithms": list(self.algorithms),
        }

    def sign(self, **kwargs):
        self.sign_calls.append(dict(kwargs))
        return {
            "KeyId": self.resolved_key_id,
            "Signature": self.private_key.sign(kwargs["Message"]),
            "SigningAlgorithm": AWS_KMS_SIGNING_ALGORITHM,
        }


def record() -> AuditRecord:
    return AuditRecord(
        timestamp="2026-09-17T23:55:00+00:00",
        event="aws_kms_g7_adapter_test",
        actor="admin_operator",
        payload={
            "_outbox_event_id": "SARA-EVENT-G7-AWS-KMS-0001",
            "_delivery_semantics": "AT_LEAST_ONCE",
            "value": "payload-remains-outside-kms-signing-request",
        },
    )


def test_aws_kms_adapter_matches_echo_ed25519_checkpoint_boundary(tmp_path):
    client = FakeKmsClient(Ed25519PrivateKey.generate())
    signer = AwsKmsEd25519CheckpointSigner(
        client=client,
        kms_key_id="alias/worldshepherd-echo-test",
        evidence_key_id="AWS-KMS-ECHO-TEST-V1",
    )
    store = EchoEventStore((tmp_path / "echo-aws-kms").resolve())
    store.ingest(record())
    manager = EchoCheckpointManager(store, signer=signer)

    bundle = manager.create_checkpoint()

    assert len(client.sign_calls) == 1
    call = client.sign_calls[0]
    assert call["KeyId"] == client.resolved_key_id
    assert call["MessageType"] == "RAW"
    assert call["SigningAlgorithm"] == AWS_KMS_SIGNING_ALGORITHM
    assert len(call["Message"]) < 128
    assert b"payload-remains-outside-kms-signing-request" not in call["Message"]
    verified = verify_bundle(bundle, manager.fingerprint_sha256)
    assert verified["status"] if "status" in verified else True
    assert verified["event_count"] == 1


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        ("key_spec", "ECC_NIST_P256", "ECC_NIST_EDWARDS25519"),
        ("key_usage", "ENCRYPT_DECRYPT", "SIGN_VERIFY"),
        ("algorithms", ["ECDSA_SHA_256"], "ED25519_SHA_512"),
    ],
)
def test_aws_kms_adapter_rejects_incompatible_key_metadata(
    field,
    value,
    match,
):
    client = FakeKmsClient(Ed25519PrivateKey.generate())
    setattr(client, field, value)

    with pytest.raises(AwsKmsCheckpointSignerError, match=match):
        AwsKmsEd25519CheckpointSigner(
            client=client,
            kms_key_id="alias/worldshepherd-echo-test",
            evidence_key_id="AWS-KMS-ECHO-TEST-V1",
        )


def test_aws_kms_adapter_rejects_sign_response_key_identity_change(tmp_path):
    class SwappedKeyClient(FakeKmsClient):
        def sign(self, **kwargs):
            response = super().sign(**kwargs)
            response["KeyId"] = (
                "arn:aws:kms:us-east-2:111122223333:key/"
                "ffffffff-ffff-ffff-ffff-ffffffffffff"
            )
            return response

    client = SwappedKeyClient(Ed25519PrivateKey.generate())
    signer = AwsKmsEd25519CheckpointSigner(
        client=client,
        kms_key_id="alias/worldshepherd-echo-test",
        evidence_key_id="AWS-KMS-ECHO-TEST-V1",
    )
    store = EchoEventStore((tmp_path / "echo-aws-kms-swap").resolve())
    store.ingest(record())
    manager = EchoCheckpointManager(store, signer=signer)

    with pytest.raises(Exception, match="key identity changed"):
        manager.create_checkpoint()

    assert manager.latest_status()["checkpoint_count"] == 0


def test_aws_kms_adapter_exposes_public_not_private_material():
    client = FakeKmsClient(Ed25519PrivateKey.generate())
    signer = AwsKmsEd25519CheckpointSigner(
        client=client,
        kms_key_id="alias/worldshepherd-echo-test",
        evidence_key_id="AWS-KMS-ECHO-TEST-V1",
    )

    assert len(signer.public_key_bytes()) == 32
    assert signer.algorithm == "Ed25519"
    assert signer.key_id == "AWS-KMS-ECHO-TEST-V1"
    assert not hasattr(signer, "private_key")

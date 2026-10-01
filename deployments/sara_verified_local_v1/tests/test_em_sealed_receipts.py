import hashlib

import pytest

from worldshepherd_sara.em_d5 import (
    D5EvidencePackage,
    D5InteractionEffect,
    D5_CONTRACT_VERSION,
)
from worldshepherd_sara.em_recovery import RecoveryReceipt, RECOVERY_CONTRACT_VERSION
from worldshepherd_sara.em_sealed_receipts import (
    SealedEvidenceKind,
    VerifiedD5Evidence,
    VerifiedRecoveryEvidence,
    verify_sealed_receipt_bytes,
)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _d5_package(path: str, digest: str) -> D5EvidencePackage:
    effects = []
    names = [
        "STATE",
        "POLARIZATION",
        "ANGLE",
        "STATE_X_POLARIZATION",
        "STATE_X_ANGLE",
        "POLARIZATION_X_ANGLE",
        "STATE_X_POLARIZATION_X_ANGLE",
    ]
    for pc in (1, 2, 3):
        for name in names:
            effects.append(
                D5InteractionEffect(
                    principal_component=pc,
                    effect=name,
                    fraction_of_pc_variance=1.0 / 7.0,
                )
            )
    return D5EvidencePackage(
        source_receipt=path,
        source_receipt_sha256=digest,
        interaction_effects=effects,
        claims_boundary=["DIAGNOSTIC_ONLY"],
    )


def _recovery_package(path: str, digest: str) -> RecoveryReceipt:
    return RecoveryReceipt(
        source_receipt=path,
        source_receipt_sha256=digest,
        completed_job_count=28,
        exit_zero_count=28,
        nonzero_exit_count=0,
        durable_checkpoint_count=28,
        replacement_a027_fresh_output=True,
        direct_mpi_binary_topology=True,
        mpi_stdin_none=True,
        palace_stdin_dev_null=True,
        sleep_inhibitor_used=True,
    )


def test_receipt_verifier_hashes_actual_bytes():
    data = b"sealed-d5-receipt\n"
    binding = verify_sealed_receipt_bytes(
        evidence_kind=SealedEvidenceKind.D5_DIAGNOSTIC,
        evidence_contract_version=D5_CONTRACT_VERSION,
        source_receipt="/sealed/d5.txt",
        expected_sha256=_sha(data),
        receipt_bytes=data,
    )
    assert binding.sha256_match is True
    assert binding.byte_length == len(data)
    assert binding.expected_sha256 == binding.observed_sha256
    assert binding.hardware_action_authorized is False


def test_receipt_verifier_rejects_digest_mismatch():
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        verify_sealed_receipt_bytes(
            evidence_kind=SealedEvidenceKind.D5_DIAGNOSTIC,
            evidence_contract_version=D5_CONTRACT_VERSION,
            source_receipt="/sealed/d5.txt",
            expected_sha256="0" * 64,
            receipt_bytes=b"different bytes",
        )


def test_receipt_verifier_rejects_empty_bytes():
    with pytest.raises(ValueError, match="must not be empty"):
        verify_sealed_receipt_bytes(
            evidence_kind=SealedEvidenceKind.D5_DIAGNOSTIC,
            evidence_contract_version=D5_CONTRACT_VERSION,
            source_receipt="/sealed/d5.txt",
            expected_sha256="0" * 64,
            receipt_bytes=b"",
        )


def test_verified_d5_requires_receipt_path_and_digest_identity():
    data = b"sealed-d5-receipt\n"
    path = "/sealed/d5.txt"
    digest = _sha(data)
    binding = verify_sealed_receipt_bytes(
        evidence_kind=SealedEvidenceKind.D5_DIAGNOSTIC,
        evidence_contract_version=D5_CONTRACT_VERSION,
        source_receipt=path,
        expected_sha256=digest,
        receipt_bytes=data,
    )
    verified = VerifiedD5Evidence(receipt=binding, package=_d5_package(path, digest))
    assert verified.package.source_receipt_sha256 == digest


def test_verified_d5_rejects_wrong_receipt_path():
    data = b"sealed-d5-receipt\n"
    digest = _sha(data)
    binding = verify_sealed_receipt_bytes(
        evidence_kind=SealedEvidenceKind.D5_DIAGNOSTIC,
        evidence_contract_version=D5_CONTRACT_VERSION,
        source_receipt="/sealed/a.txt",
        expected_sha256=digest,
        receipt_bytes=data,
    )
    with pytest.raises(ValueError, match="path mismatch"):
        VerifiedD5Evidence(receipt=binding, package=_d5_package("/sealed/b.txt", digest))


def test_verified_recovery_binds_actual_receipt_bytes():
    data = b"sealed-recovery-receipt\n"
    path = "/sealed/recovery.txt"
    digest = _sha(data)
    binding = verify_sealed_receipt_bytes(
        evidence_kind=SealedEvidenceKind.POWER_RECOVERY,
        evidence_contract_version=RECOVERY_CONTRACT_VERSION,
        source_receipt=path,
        expected_sha256=digest,
        receipt_bytes=data,
    )
    verified = VerifiedRecoveryEvidence(
        receipt=binding,
        package=_recovery_package(path, digest),
    )
    assert verified.receipt.sha256_match is True


def test_verified_recovery_rejects_wrong_contract_kind():
    data = b"sealed-recovery-receipt\n"
    path = "/sealed/recovery.txt"
    digest = _sha(data)
    binding = verify_sealed_receipt_bytes(
        evidence_kind=SealedEvidenceKind.D5_DIAGNOSTIC,
        evidence_contract_version=D5_CONTRACT_VERSION,
        source_receipt=path,
        expected_sha256=digest,
        receipt_bytes=data,
    )
    with pytest.raises(ValueError, match="POWER_RECOVERY"):
        VerifiedRecoveryEvidence(
            receipt=binding,
            package=_recovery_package(path, digest),
        )

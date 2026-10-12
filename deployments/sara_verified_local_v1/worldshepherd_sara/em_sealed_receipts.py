"""Cryptographic bindings between local sealed receipts and typed UC06 evidence.

A typed package that merely contains a SHA-256 string is not proof that the imported
receipt bytes match that digest. This module hashes the actual bytes and creates a
verified binding only on an exact match. It performs no network, solver, or hardware
action and does not upgrade any scientific claim by itself.
"""

from __future__ import annotations

import hashlib
import re
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .em_convergence_evidence import (
    CONVERGENCE_EVIDENCE_SCHEMA_VERSION,
    ConvergenceEvidencePackage,
)
from .em_d5 import D5EvidencePackage, D5_CONTRACT_VERSION
from .em_recovery import RecoveryReceipt, RECOVERY_CONTRACT_VERSION


SEALED_RECEIPT_SCHEMA_VERSION = "worldshepherd.uc06-p1.sealed-receipt.v0.1"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class SealedEvidenceKind(str, Enum):
    D5_DIAGNOSTIC = "D5_DIAGNOSTIC"
    POWER_RECOVERY = "POWER_RECOVERY"
    FROZEN_CONVERGENCE = "FROZEN_CONVERGENCE"


class VerifiedSealedReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[SEALED_RECEIPT_SCHEMA_VERSION] = SEALED_RECEIPT_SCHEMA_VERSION
    evidence_kind: SealedEvidenceKind
    evidence_contract_version: str = Field(min_length=1, max_length=128)
    source_receipt: str = Field(min_length=1, max_length=512)
    expected_sha256: str
    observed_sha256: str
    byte_length: int = Field(gt=0)
    sha256_match: Literal[True] = True
    read_only_import: Literal[True] = True
    scientific_gate_change: Literal[False] = False
    hardware_action_authorized: Literal[False] = False

    @model_validator(mode="after")
    def validate_hashes(self) -> "VerifiedSealedReceipt":
        for name, value in (
            ("expected_sha256", self.expected_sha256),
            ("observed_sha256", self.observed_sha256),
        ):
            if not _SHA256_RE.fullmatch(value):
                raise ValueError(f"{name} must be lowercase SHA-256 hex")
        if self.expected_sha256 != self.observed_sha256:
            raise ValueError("verified receipt digests must match exactly")
        return self


def verify_sealed_receipt_bytes(
    *,
    evidence_kind: SealedEvidenceKind,
    evidence_contract_version: str,
    source_receipt: str,
    expected_sha256: str,
    receipt_bytes: bytes,
) -> VerifiedSealedReceipt:
    """Hash actual receipt bytes and fail closed on mismatch or empty input."""

    if not receipt_bytes:
        raise ValueError("sealed receipt bytes must not be empty")
    if not _SHA256_RE.fullmatch(expected_sha256):
        raise ValueError("expected_sha256 must be lowercase SHA-256 hex")

    observed = hashlib.sha256(receipt_bytes).hexdigest()
    if observed != expected_sha256:
        raise ValueError("sealed receipt SHA-256 mismatch")

    return VerifiedSealedReceipt(
        evidence_kind=evidence_kind,
        evidence_contract_version=evidence_contract_version,
        source_receipt=source_receipt,
        expected_sha256=expected_sha256,
        observed_sha256=observed,
        byte_length=len(receipt_bytes),
    )


class VerifiedD5Evidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    receipt: VerifiedSealedReceipt
    package: D5EvidencePackage

    @model_validator(mode="after")
    def validate_binding(self) -> "VerifiedD5Evidence":
        if self.receipt.evidence_kind != SealedEvidenceKind.D5_DIAGNOSTIC:
            raise ValueError("D5 evidence requires D5_DIAGNOSTIC receipt kind")
        if self.receipt.evidence_contract_version != D5_CONTRACT_VERSION:
            raise ValueError("D5 receipt contract version mismatch")
        if self.receipt.source_receipt != self.package.source_receipt:
            raise ValueError("D5 source receipt path mismatch")
        if self.receipt.expected_sha256 != self.package.source_receipt_sha256:
            raise ValueError("D5 source receipt SHA mismatch")
        return self


class VerifiedRecoveryEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    receipt: VerifiedSealedReceipt
    package: RecoveryReceipt

    @model_validator(mode="after")
    def validate_binding(self) -> "VerifiedRecoveryEvidence":
        if self.receipt.evidence_kind != SealedEvidenceKind.POWER_RECOVERY:
            raise ValueError("recovery evidence requires POWER_RECOVERY receipt kind")
        if self.receipt.evidence_contract_version != RECOVERY_CONTRACT_VERSION:
            raise ValueError("recovery receipt contract version mismatch")
        if self.receipt.source_receipt != self.package.source_receipt:
            raise ValueError("recovery source receipt path mismatch")
        if self.receipt.expected_sha256 != self.package.source_receipt_sha256:
            raise ValueError("recovery source receipt SHA mismatch")
        return self


class VerifiedConvergenceEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    receipt: VerifiedSealedReceipt
    package: ConvergenceEvidencePackage

    @model_validator(mode="after")
    def validate_binding(self) -> "VerifiedConvergenceEvidence":
        if self.receipt.evidence_kind != SealedEvidenceKind.FROZEN_CONVERGENCE:
            raise ValueError("convergence evidence requires FROZEN_CONVERGENCE receipt kind")
        if self.receipt.evidence_contract_version != CONVERGENCE_EVIDENCE_SCHEMA_VERSION:
            raise ValueError("convergence receipt contract version mismatch")
        if self.receipt.source_receipt != self.package.source_receipt:
            raise ValueError("convergence source receipt path mismatch")
        if self.receipt.expected_sha256 != self.package.source_receipt_sha256:
            raise ValueError("convergence source receipt SHA mismatch")
        return self

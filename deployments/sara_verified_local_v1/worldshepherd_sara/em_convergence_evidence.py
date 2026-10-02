"""Sealed evidence package for frozen UC06-P1 D6-E convergence adjudication.

The package carries typed evidence only. It deliberately does not accept a
caller-supplied PASS/FAIL decision; the frozen evaluator computes that decision from
the evidence under the preregistered thresholds. Provenance binds source receipt SHA,
registered parser identity, and a canonical digest of the typed evidence payload.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .em_convergence import D6E_CONTRACT_ID, FrozenConvergenceInput


CONVERGENCE_EVIDENCE_SCHEMA_VERSION = "worldshepherd.uc06-p1.convergence-evidence.v0.2"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _canonical_evidence_sha256(evidence: FrozenConvergenceInput) -> str:
    payload = json.dumps(
        evidence.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


class ConvergenceEvidencePackage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[CONVERGENCE_EVIDENCE_SCHEMA_VERSION] = (
        CONVERGENCE_EVIDENCE_SCHEMA_VERSION
    )
    analysis_contract_id: Literal[D6E_CONTRACT_ID] = D6E_CONTRACT_ID
    source_receipt: str = Field(min_length=1, max_length=512)
    source_receipt_sha256: str
    parser_id: str = Field(min_length=1, max_length=128)
    parser_version: str = Field(min_length=1, max_length=128)
    evidence_payload_sha256: str
    evidence_integrity_pass: Literal[True] = True
    scientific_gate_change: Literal[False] = False
    caller_supplied_decision_allowed: Literal[False] = False
    evidence: FrozenConvergenceInput
    claims_boundary: list[str] = Field(default_factory=list, min_length=1, max_length=64)

    @model_validator(mode="after")
    def validate_package(self) -> "ConvergenceEvidencePackage":
        for name, value in (
            ("source_receipt_sha256", self.source_receipt_sha256),
            ("evidence_payload_sha256", self.evidence_payload_sha256),
        ):
            if not _SHA256_RE.fullmatch(value):
                raise ValueError(f"{name} must be lowercase SHA-256 hex")
        if self.evidence.analysis_contract_id != self.analysis_contract_id:
            raise ValueError("embedded evidence must use the frozen D6-E analysis contract")
        if self.evidence.scientific_gate_change is not False:
            raise ValueError("scientific gate change is forbidden")
        expected_payload_digest = _canonical_evidence_sha256(self.evidence)
        if self.evidence_payload_sha256 != expected_payload_digest:
            raise ValueError("canonical convergence evidence payload SHA mismatch")
        return self


def build_convergence_evidence_package(
    *,
    source_receipt: str,
    source_receipt_sha256: str,
    parser_id: str,
    parser_version: str,
    evidence: FrozenConvergenceInput,
    claims_boundary: list[str],
) -> ConvergenceEvidencePackage:
    """Build a payload-digested package; no adjudication is performed here."""

    return ConvergenceEvidencePackage(
        source_receipt=source_receipt,
        source_receipt_sha256=source_receipt_sha256,
        parser_id=parser_id,
        parser_version=parser_version,
        evidence_payload_sha256=_canonical_evidence_sha256(evidence),
        evidence=evidence,
        claims_boundary=claims_boundary,
    )

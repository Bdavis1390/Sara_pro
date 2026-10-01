"""Sealed evidence package for frozen UC06-P1 D6-E convergence adjudication.

The package carries raw typed evidence only.  It deliberately does not accept a
caller-supplied PASS/FAIL decision; the frozen evaluator computes that decision from
the evidence under the preregistered thresholds.
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .em_convergence import D6E_CONTRACT_ID, FrozenConvergenceInput


CONVERGENCE_EVIDENCE_SCHEMA_VERSION = "worldshepherd.uc06-p1.convergence-evidence.v0.1"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class ConvergenceEvidencePackage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[CONVERGENCE_EVIDENCE_SCHEMA_VERSION] = (
        CONVERGENCE_EVIDENCE_SCHEMA_VERSION
    )
    analysis_contract_id: Literal[D6E_CONTRACT_ID] = D6E_CONTRACT_ID
    source_receipt: str = Field(min_length=1, max_length=512)
    source_receipt_sha256: str
    evidence_integrity_pass: Literal[True] = True
    scientific_gate_change: Literal[False] = False
    caller_supplied_decision_allowed: Literal[False] = False
    evidence: FrozenConvergenceInput
    claims_boundary: list[str] = Field(default_factory=list, min_length=1, max_length=64)

    @model_validator(mode="after")
    def validate_package(self) -> "ConvergenceEvidencePackage":
        if not _SHA256_RE.fullmatch(self.source_receipt_sha256):
            raise ValueError("source_receipt_sha256 must be lowercase SHA-256 hex")
        if self.evidence.analysis_contract_id != self.analysis_contract_id:
            raise ValueError("embedded evidence must use the frozen D6-E analysis contract")
        if self.evidence.scientific_gate_change is not False:
            raise ValueError("scientific gate change is forbidden")
        return self

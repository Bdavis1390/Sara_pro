"""WS-QX EVIDENCE-01: domain-neutral, fail-closed qualification evidence.

This module records evidence and evaluates only structural promotion prerequisites.
It does not perform or imply physical, external, standards, or program validation.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hashlib import sha256
import json
from typing import Any

QUALIFICATION_VERSION = "EVIDENCE-01"
CAPABILITY_STATUS = "IMPLEMENTED_IN_SOFTWARE"


def digest(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    return "sha256:" + sha256(payload).hexdigest()


@dataclass
class EvidenceVector:
    physical_performance: str = "NONE"
    assurance_tevv: str = "NONE"
    replication_external: str = "NONE"


@dataclass
class QualificationEnvelope:
    qualification_id: str
    qualification_version: str
    experiment_id: str
    run_id: str
    claim_state_before: str
    requested_claim_state_after: str
    software_commit: str
    operator_id: str
    authorization_record: str
    test_manifest_digest: str
    hardware_ids: list[str] = field(default_factory=list)
    model_digests: list[str] = field(default_factory=list)
    configuration_digests: list[str] = field(default_factory=list)
    calibration_ids: list[str] = field(default_factory=list)
    raw_evidence: list[dict[str, Any]] = field(default_factory=list)
    normalized_evidence: list[dict[str, Any]] = field(default_factory=list)
    faults: list[dict[str, Any]] = field(default_factory=list)
    uncertainty_budget: dict[str, Any] = field(default_factory=dict)
    dimensions: dict[str, bool] = field(default_factory=dict)
    physical_io_observed: bool = False
    human_safety_controls_verified: bool = False
    run_complete: bool = False
    external_replication_reference: str | None = None
    evidence_vector: EvidenceVector = field(default_factory=EvidenceVector)
    claims: dict[str, bool] = field(default_factory=lambda: {
        "internal_qualification": False,
        "physical_validation": False,
        "external_validation": False,
        "standards_conformance": False,
        "program_qualification": False,
    })

    def evidence_digest(self) -> str:
        value = asdict(self)
        value.pop("claims", None)
        return digest(value)

    def mandatory_dimensions_pass(self) -> bool:
        return bool(self.dimensions) and all(self.dimensions.values())

    def finalize_internal(self) -> dict[str, Any]:
        structural = all((
            self.qualification_id,
            self.qualification_version,
            self.experiment_id,
            self.run_id,
            self.software_commit,
            self.operator_id,
            self.authorization_record,
            self.test_manifest_digest.startswith("sha256:"),
            self.raw_evidence,
            self.run_complete,
            self.mandatory_dimensions_pass(),
        ))
        self.claims["internal_qualification"] = bool(structural)
        # Deliberately do not infer higher claims from internal qualification.
        self.claims["physical_validation"] = False
        self.claims["external_validation"] = False
        self.claims["standards_conformance"] = False
        self.claims["program_qualification"] = False
        return {"qualified": bool(structural), "evidence_digest": self.evidence_digest(), "claims": dict(self.claims)}

    def promote_physical(self) -> bool:
        allowed = all((
            self.claims["internal_qualification"],
            self.hardware_ids,
            self.calibration_ids,
            self.physical_io_observed,
            self.human_safety_controls_verified,
            self.evidence_vector.physical_performance not in {"", "NONE"},
        ))
        self.claims["physical_validation"] = bool(allowed)
        return bool(allowed)

    def promote_external(self) -> bool:
        allowed = all((
            self.claims["physical_validation"],
            self.external_replication_reference,
            self.evidence_vector.replication_external not in {"", "NONE"},
        ))
        self.claims["external_validation"] = bool(allowed)
        return bool(allowed)


def dry_run_envelope(qualification_id: str = "WS-QX-DEMO") -> QualificationEnvelope:
    """Return a deliberately non-promotable envelope for tests/examples."""
    return QualificationEnvelope(
        qualification_id=qualification_id,
        qualification_version=QUALIFICATION_VERSION,
        experiment_id="dry-run",
        run_id="dry-run",
        claim_state_before="IMPLEMENTED_IN_SOFTWARE",
        requested_claim_state_after="INTERNAL_REPRODUCIBLE_TEST",
        software_commit="UNBOUND",
        operator_id="UNBOUND",
        authorization_record="UNBOUND",
        test_manifest_digest="UNBOUND",
    )

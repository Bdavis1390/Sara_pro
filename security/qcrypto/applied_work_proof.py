"""Claims-controlled proof of applied work from executed, reproducible evidence.

Applied-work quantity is derived from passed measurements. It is not monetary
value, legal ownership, consensus weight, or a cryptographic security claim.
Downstream systems may consume a validated receipt, but may not create or
rewrite the upstream applied-work evidence.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Iterable

from security.qcrypto.applied_work_postwork import AppliedWorkReceipt, WorkValidationState

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_GIT_SHA = re.compile(r"^[0-9a-f]{40}$")


class AppliedWorkProofState(str, Enum):
    IMPLEMENTED_IN_SOFTWARE = "IMPLEMENTED_IN_SOFTWARE"
    EXECUTED_IN_LAB = "EXECUTED_IN_LAB"
    PROVEN_INTERNALLY = "PROVEN_INTERNALLY"
    PRESERVED_APPLIED_WORK = "PRESERVED_APPLIED_WORK"
    INDEPENDENTLY_REPRODUCED = "INDEPENDENTLY_REPRODUCED"


@dataclass(frozen=True)
class WorkMeasurement:
    name: str
    units: int
    source_sha256: str
    passed: bool


@dataclass(frozen=True)
class ExecutedWorkEvidence:
    work_id: str
    contributor_id: str
    implementation_commit: str
    implementation_tree: str
    workflow_name: str
    workflow_run_id: int
    artifact_sha256: str
    measurements: tuple[WorkMeasurement, ...]
    negative_tests: tuple[str, ...]
    tamper_tests: tuple[str, ...]
    executed: bool
    evidence_retained: bool
    reproducible: bool
    safety_authorized: bool
    measurement_accessible: bool
    independent_reproduced: bool = False
    revoked: bool = False


@dataclass(frozen=True)
class AppliedWorkCertificate:
    work_id: str
    contributor_id: str
    evidence_digest: str
    measured_work_units: int
    proof_state: AppliedWorkProofState
    workflow_name: str
    workflow_run_id: int
    implementation_commit: str
    implementation_tree: str
    artifact_sha256: str
    negative_test_count: int
    tamper_test_count: int
    retained: bool
    reproducible: bool
    safety_authorized: bool
    measurement_accessible: bool
    independent_reproduced: bool
    revoked: bool
    claims_boundary: tuple[str, ...]

    def to_dict(self) -> dict:
        data = asdict(self)
        data["proof_state"] = self.proof_state.value
        data["claims_boundary"] = list(self.claims_boundary)
        return data


def _require_sha256(value: str, name: str) -> None:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise ValueError(f"{name} must be a lowercase SHA-256 hex digest")


def _require_git_sha(value: str, name: str) -> None:
    if not isinstance(value, str) or not _GIT_SHA.fullmatch(value):
        raise ValueError(f"{name} must be a full lowercase 40-character Git SHA")


def validate_executed_work(evidence: ExecutedWorkEvidence) -> None:
    if not evidence.work_id or not evidence.contributor_id:
        raise ValueError("stable work and contributor identifiers are required")
    _require_git_sha(evidence.implementation_commit, "implementation_commit")
    _require_git_sha(evidence.implementation_tree, "implementation_tree")
    _require_sha256(evidence.artifact_sha256, "artifact_sha256")
    if not evidence.workflow_name or evidence.workflow_run_id <= 0:
        raise ValueError("workflow name and positive workflow_run_id are required")
    if not evidence.measurements:
        raise ValueError("at least one applied-work measurement is required")
    for measurement in evidence.measurements:
        if not measurement.name:
            raise ValueError("measurement name is required")
        if measurement.units <= 0:
            raise ValueError("measurement units must be positive")
        _require_sha256(measurement.source_sha256, "measurement source_sha256")
    if evidence.independent_reproduced and not evidence.reproducible:
        raise ValueError("independent reproduction requires reproducible evidence")


def evidence_digest(evidence: ExecutedWorkEvidence) -> str:
    validate_executed_work(evidence)
    payload = asdict(evidence)
    body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(body).hexdigest()


def measured_work_units(evidence: ExecutedWorkEvidence) -> int:
    """Return applied-work quantity from measurements that actually passed.

    Units are measurement quantities only. This function does not price them or
    convert them into economic, governance, or legal value.
    """
    validate_executed_work(evidence)
    return sum(item.units for item in evidence.measurements if item.passed)


def assess_applied_work(evidence: ExecutedWorkEvidence) -> AppliedWorkCertificate:
    validate_executed_work(evidence)
    units = measured_work_units(evidence)

    if not evidence.executed or units <= 0:
        state = AppliedWorkProofState.IMPLEMENTED_IN_SOFTWARE
    elif not evidence.negative_tests or not evidence.tamper_tests:
        state = AppliedWorkProofState.EXECUTED_IN_LAB
    elif not (
        evidence.safety_authorized
        and evidence.measurement_accessible
        and evidence.reproducible
    ):
        state = AppliedWorkProofState.EXECUTED_IN_LAB
    elif not evidence.evidence_retained:
        state = AppliedWorkProofState.PROVEN_INTERNALLY
    elif evidence.independent_reproduced:
        state = AppliedWorkProofState.INDEPENDENTLY_REPRODUCED
    else:
        state = AppliedWorkProofState.PRESERVED_APPLIED_WORK

    return AppliedWorkCertificate(
        work_id=evidence.work_id,
        contributor_id=evidence.contributor_id,
        evidence_digest=evidence_digest(evidence),
        measured_work_units=units,
        proof_state=state,
        workflow_name=evidence.workflow_name,
        workflow_run_id=evidence.workflow_run_id,
        implementation_commit=evidence.implementation_commit,
        implementation_tree=evidence.implementation_tree,
        artifact_sha256=evidence.artifact_sha256,
        negative_test_count=len(evidence.negative_tests),
        tamper_test_count=len(evidence.tamper_tests),
        retained=evidence.evidence_retained,
        reproducible=evidence.reproducible,
        safety_authorized=evidence.safety_authorized,
        measurement_accessible=evidence.measurement_accessible,
        independent_reproduced=evidence.independent_reproduced,
        revoked=evidence.revoked,
        claims_boundary=(
            "applied-work units are measured quantities, not economic value",
            "certificate does not establish legal ownership or intellectual-property priority",
            "certificate does not establish production consensus adoption",
            "certificate does not establish post-quantum primitive security",
            "independent reproduction is not claimed unless explicitly evidenced",
        ),
    )


def certificate_to_postwork_receipt(certificate: AppliedWorkCertificate) -> AppliedWorkReceipt:
    """Create the existing downstream receipt only from an applied-work certificate."""
    if certificate.measured_work_units <= 0:
        raise ValueError("certificate contains no measured applied work")
    if certificate.revoked:
        validation_state = WorkValidationState.UNVALIDATED
    elif certificate.proof_state == AppliedWorkProofState.INDEPENDENTLY_REPRODUCED:
        validation_state = WorkValidationState.INDEPENDENTLY_REPRODUCED
    elif certificate.proof_state in {
        AppliedWorkProofState.PROVEN_INTERNALLY,
        AppliedWorkProofState.PRESERVED_APPLIED_WORK,
    }:
        validation_state = WorkValidationState.PROVEN_INTERNALLY
    else:
        validation_state = WorkValidationState.IMPLEMENTED_IN_SOFTWARE

    return AppliedWorkReceipt(
        work_id=certificate.work_id,
        contributor_id=certificate.contributor_id,
        evidence_digest=certificate.evidence_digest,
        validated_work_units=certificate.measured_work_units,
        validation_state=validation_state,
        evidence_retained=certificate.retained,
        reproducible=certificate.reproducible,
        safety_authorized=certificate.safety_authorized,
        measurement_accessible=certificate.measurement_accessible,
        revoked=certificate.revoked,
    )


def summarize_certificates(certificates: Iterable[AppliedWorkCertificate]) -> dict:
    values = tuple(certificates)
    return {
        "schema": "WS-APPLIED-WORK-EVIDENCE-SUMMARY-V1",
        "certificate_count": len(values),
        "measured_work_units": sum(item.measured_work_units for item in values),
        "proof_states": sorted({item.proof_state.value for item in values}),
        "independent_reproduction_count": sum(item.independent_reproduced for item in values),
        "economic_value_established": False,
        "legal_ownership_established": False,
        "post_quantum_security_established": False,
    }

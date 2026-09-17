from dataclasses import replace

import pytest

from security.qcrypto.applied_work_postwork import WorkValidationState, stake_eligible
from security.qcrypto.applied_work_proof import (
    AppliedWorkProofState,
    ExecutedWorkEvidence,
    WorkMeasurement,
    assess_applied_work,
    certificate_to_postwork_receipt,
    evidence_digest,
    measured_work_units,
    summarize_certificates,
)


def measurement(name="assertions", units=12, passed=True, digest="11" * 32):
    return WorkMeasurement(name=name, units=units, source_sha256=digest, passed=passed)


def evidence(**overrides):
    values = dict(
        work_id="qcrypto-pq-signature-lab-1",
        contributor_id="worldshepherd",
        implementation_commit="a" * 40,
        implementation_tree="b" * 40,
        workflow_name="QCRYPTO Concrete PQ Interop Gate",
        workflow_run_id=12345,
        artifact_sha256="c" * 64,
        measurements=(
            measurement("positive assertions", 12, True, "11" * 32),
            measurement("rejected invalid cases", 5, True, "22" * 32),
            measurement("non-passing observation", 1000, False, "33" * 32),
        ),
        negative_tests=("wrong public key rejected", "missing signature rejected"),
        tamper_tests=("message mutation rejected", "signature mutation rejected"),
        executed=True,
        evidence_retained=True,
        reproducible=True,
        safety_authorized=True,
        measurement_accessible=True,
        independent_reproduced=False,
        revoked=False,
    )
    values.update(overrides)
    return ExecutedWorkEvidence(**values)


def test_units_come_only_from_passed_measurements_not_declared_value():
    item = evidence()
    assert measured_work_units(item) == 17
    cert = assess_applied_work(item)
    assert cert.measured_work_units == 17
    assert cert.proof_state == AppliedWorkProofState.PRESERVED_APPLIED_WORK
    assert "economic value" in cert.claims_boundary[0]


def test_code_presence_without_execution_cannot_become_proven_work():
    cert = assess_applied_work(evidence(executed=False))
    assert cert.proof_state == AppliedWorkProofState.IMPLEMENTED_IN_SOFTWARE
    receipt = certificate_to_postwork_receipt(cert)
    assert receipt.validation_state == WorkValidationState.IMPLEMENTED_IN_SOFTWARE
    assert stake_eligible(receipt) is False


def test_execution_without_negative_or_tamper_tests_stays_lab_only():
    cert = assess_applied_work(evidence(negative_tests=(), tamper_tests=()))
    assert cert.proof_state == AppliedWorkProofState.EXECUTED_IN_LAB
    assert stake_eligible(certificate_to_postwork_receipt(cert)) is False


def test_internal_proof_without_retention_is_not_preserved_applied_work():
    cert = assess_applied_work(evidence(evidence_retained=False))
    assert cert.proof_state == AppliedWorkProofState.PROVEN_INTERNALLY
    receipt = certificate_to_postwork_receipt(cert)
    assert receipt.validation_state == WorkValidationState.PROVEN_INTERNALLY
    assert receipt.evidence_retained is False
    assert stake_eligible(receipt) is False


def test_preserved_applied_work_can_feed_postwork_without_unit_amplification():
    cert = assess_applied_work(evidence())
    receipt = certificate_to_postwork_receipt(cert)
    assert receipt.validated_work_units == cert.measured_work_units == 17
    assert receipt.evidence_digest == cert.evidence_digest
    assert receipt.validation_state == WorkValidationState.PROVEN_INTERNALLY
    assert stake_eligible(receipt) is True


def test_independent_reproduction_requires_reproducibility_and_is_explicit():
    with pytest.raises(ValueError, match="independent reproduction"):
        assess_applied_work(evidence(independent_reproduced=True, reproducible=False))

    cert = assess_applied_work(evidence(independent_reproduced=True))
    assert cert.proof_state == AppliedWorkProofState.INDEPENDENTLY_REPRODUCED
    receipt = certificate_to_postwork_receipt(cert)
    assert receipt.validation_state == WorkValidationState.INDEPENDENTLY_REPRODUCED


def test_revocation_prevents_downstream_stake_eligibility_without_rewriting_evidence():
    original = assess_applied_work(evidence())
    revoked = assess_applied_work(evidence(revoked=True))
    assert original.evidence_digest != revoked.evidence_digest
    receipt = certificate_to_postwork_receipt(revoked)
    assert receipt.revoked is True
    assert receipt.validation_state == WorkValidationState.UNVALIDATED
    assert stake_eligible(receipt) is False


def test_evidence_digest_binds_commit_tree_run_artifact_measurements_and_tests():
    base = evidence()
    digest = evidence_digest(base)
    assert len(digest) == 64
    assert evidence_digest(replace(base, workflow_run_id=12346)) != digest
    assert evidence_digest(replace(base, implementation_commit="d" * 40)) != digest
    assert evidence_digest(replace(base, artifact_sha256="e" * 64)) != digest
    assert evidence_digest(replace(base, tamper_tests=("different tamper case",))) != digest


def test_invalid_or_unmeasured_provenance_is_rejected():
    with pytest.raises(ValueError, match="implementation_commit"):
        assess_applied_work(evidence(implementation_commit="short"))
    with pytest.raises(ValueError, match="artifact_sha256"):
        assess_applied_work(evidence(artifact_sha256="not-a-digest"))
    with pytest.raises(ValueError, match="measurement units"):
        assess_applied_work(evidence(measurements=(measurement(units=0),)))
    with pytest.raises(ValueError, match="at least one"):
        assess_applied_work(evidence(measurements=()))


def test_failed_measurements_do_not_mint_applied_work_units():
    item = evidence(measurements=(measurement(units=500, passed=False),))
    cert = assess_applied_work(item)
    assert cert.measured_work_units == 0
    assert cert.proof_state == AppliedWorkProofState.IMPLEMENTED_IN_SOFTWARE
    with pytest.raises(ValueError, match="no measured applied work"):
        certificate_to_postwork_receipt(cert)


def test_summary_preserves_nonclaim_boundaries():
    first = assess_applied_work(evidence())
    second = assess_applied_work(evidence(work_id="work-2", independent_reproduced=True))
    summary = summarize_certificates((first, second))
    assert summary["certificate_count"] == 2
    assert summary["measured_work_units"] == 34
    assert summary["independent_reproduction_count"] == 1
    assert summary["economic_value_established"] is False
    assert summary["legal_ownership_established"] is False
    assert summary["post_quantum_security_established"] is False

from dataclasses import replace

import pytest

from security.qcrypto.applied_work_postwork import apply_post_work_stake
from security.qcrypto.applied_work_pos_application import instantiate_validator_application
from security.qcrypto.applied_work_proof import (
    ExecutedWorkEvidence,
    WorkMeasurement,
    assess_applied_work,
    certificate_to_postwork_receipt,
)
from security.qcrypto.applied_work_validation_cycle import (
    PostApplicationMeasurement,
    close_pos_application_cycle,
    open_pos_application_cycle,
)


def preserved_certificate():
    evidence = ExecutedWorkEvidence(
        work_id="cycle-work-1",
        contributor_id="contributor-1",
        implementation_commit="1" * 40,
        implementation_tree="2" * 40,
        workflow_name="measured-work-gate",
        workflow_run_id=123,
        artifact_sha256="3" * 64,
        measurements=(
            WorkMeasurement(
                name="passed-capability-measurement",
                units=100,
                source_sha256="4" * 64,
                passed=True,
            ),
        ),
        negative_tests=("reject-invalid-input",),
        tamper_tests=("reject-mutated-evidence",),
        executed=True,
        evidence_retained=True,
        reproducible=True,
        safety_authorized=True,
        measurement_accessible=True,
    )
    return assess_applied_work(evidence)


def make_application():
    certificate = preserved_certificate()
    receipt = certificate_to_postwork_receipt(certificate)
    position = apply_post_work_stake(
        receipt,
        consensus_domain="WS-QPOS",
        epoch=7,
        requested_stake_units=80,
    )
    application = instantiate_validator_application(
        receipt,
        position,
        validator_id="validator-cycle-1",
        withdrawal_owner="owner-1",
        classical_credential="classical-1",
    )
    return certificate, position, application


def test_pos_cycle_requires_and_preserves_measured_pow():
    certificate, position, application = make_application()
    cycle = open_pos_application_cycle(
        certificate,
        position,
        application,
        cycle_id="cycle-1",
    )
    assert cycle.status == "POS_APPLICATION_OF_MEASURED_POW"
    assert cycle.pow_measured_units == 100
    assert cycle.pos_applied_units == 80
    assert cycle.evidence_digest == certificate.evidence_digest
    assert cycle.pow_state == certificate.proof_state.value


def test_pos_cycle_rejects_rewritten_pow_quantity():
    certificate, position, application = make_application()
    forged = replace(application, measured_work_units=99)
    with pytest.raises(ValueError, match="measured PoW quantity lineage"):
        open_pos_application_cycle(
            certificate,
            position,
            forged,
            cycle_id="cycle-1",
        )


def test_pos_cycle_rejects_non_preserved_pow_state():
    certificate, position, application = make_application()
    downgraded = replace(certificate, retained=False, proof_state=certificate.proof_state.PROVEN_INTERNALLY)
    with pytest.raises(ValueError, match="preserved measured PoW evidence"):
        open_pos_application_cycle(
            downgraded,
            position,
            application,
            cycle_id="cycle-1",
        )


def test_post_application_measurement_can_seed_next_pow_candidate():
    certificate, position, application = make_application()
    cycle = open_pos_application_cycle(certificate, position, application, cycle_id="cycle-1")
    closure = close_pos_application_cycle(
        cycle,
        (
            PostApplicationMeasurement(
                name="application-effectiveness",
                measured_units=75,
                source_sha256="5" * 64,
                passed=True,
            ),
            PostApplicationMeasurement(
                name="application-integrity",
                measured_units=5,
                source_sha256="6" * 64,
                passed=True,
            ),
        ),
    )
    assert closure.status == "POST_APPLICATION_MEASURED_CANDIDATE_FOR_NEXT_POW"
    assert closure.next_pow_candidate is True
    assert closure.measured_outcome_units == 80
    assert closure.failed_measurement_count == 0


def test_failed_application_measurement_blocks_next_pow_promotion():
    certificate, position, application = make_application()
    cycle = open_pos_application_cycle(certificate, position, application, cycle_id="cycle-1")
    closure = close_pos_application_cycle(
        cycle,
        (
            PostApplicationMeasurement(
                name="application-effectiveness",
                measured_units=75,
                source_sha256="5" * 64,
                passed=True,
            ),
            PostApplicationMeasurement(
                name="application-integrity",
                measured_units=5,
                source_sha256="6" * 64,
                passed=False,
            ),
        ),
    )
    assert closure.status == "POST_APPLICATION_MEASURED_NOT_PROMOTABLE"
    assert closure.next_pow_candidate is False
    assert closure.failed_measurement_count == 1
    assert closure.measured_outcome_units == 75


def test_pos_application_cannot_self_certify_without_measurement():
    certificate, position, application = make_application()
    cycle = open_pos_application_cycle(certificate, position, application, cycle_id="cycle-1")
    with pytest.raises(ValueError, match="at least one post-application measurement"):
        close_pos_application_cycle(cycle, ())

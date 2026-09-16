from dataclasses import replace

import pytest

from security.qcrypto.applied_work_postwork import (
    AppliedWorkReceipt,
    WorkValidationState,
    apply_post_work_stake,
    slash_position,
)
from security.qcrypto.applied_work_pos_application import (
    instantiate_validator_application,
    project_to_all_families,
    project_to_family,
    validate_application_registry,
    verify_application_lineage,
)
from security.qcrypto.pos_family_preservation import PROFILES


def validated_receipt(work_id="work-1", contributor="contributor-1"):
    return AppliedWorkReceipt(
        work_id=work_id,
        contributor_id=contributor,
        evidence_digest=("ab" if work_id == "work-1" else "cd") * 32,
        validated_work_units=100,
        validation_state=WorkValidationState.PROVEN_INTERNALLY,
        evidence_retained=True,
        reproducible=True,
        safety_authorized=True,
        measurement_accessible=True,
    )


def test_validator_application_is_downstream_of_measured_validated_work():
    r = validated_receipt()
    p = apply_post_work_stake(r, consensus_domain="WS-QPOS", epoch=1, requested_stake_units=80)
    app = instantiate_validator_application(
        r,
        p,
        validator_id="validator-1",
        withdrawal_owner="owner-1",
        classical_credential="classical-1",
    )
    verify_application_lineage(r, p, app)
    assert app.validator.stake == 80
    assert app.validator.effective_balance == 80
    assert app.evidence_digest == r.evidence_digest
    assert app.measured_work_units == 100
    assert app.source_validation_state == WorkValidationState.PROVEN_INTERNALLY.value
    assert app.application_claim == "WORLDSHEPHERD_POST_POW_APPLIED_WORK_POS_APPLICATION"


def test_pos_application_rejects_unmeasured_or_unvalidated_work():
    r = replace(
        validated_receipt(),
        validation_state=WorkValidationState.IMPLEMENTED_IN_SOFTWARE,
        measurement_accessible=False,
    )
    with pytest.raises(ValueError, match="not eligible"):
        apply_post_work_stake(r, consensus_domain="WS-QPOS", epoch=1, requested_stake_units=50)


def test_slashing_changes_consensus_weight_without_erasing_pow_lineage():
    r = validated_receipt()
    p = apply_post_work_stake(r, consensus_domain="WS-QPOS", epoch=1, requested_stake_units=80)
    p = slash_position(p, 15)
    app = instantiate_validator_application(
        r,
        p,
        validator_id="validator-1",
        withdrawal_owner="owner-1",
        classical_credential="classical-1",
    )
    verify_application_lineage(r, p, app)
    assert app.validator.stake == 80
    assert app.validator.effective_balance == 65
    assert app.validator.slashed is True
    assert app.evidence_digest == r.evidence_digest
    assert app.measured_work_units == r.validated_work_units


def test_application_lineage_rejects_measured_pow_quantity_rewrite():
    r = validated_receipt()
    p = apply_post_work_stake(r, consensus_domain="WS-QPOS", epoch=1, requested_stake_units=80)
    app = instantiate_validator_application(
        r,
        p,
        validator_id="validator-1",
        withdrawal_owner="owner-1",
        classical_credential="classical-1",
    )
    forged = replace(app, measured_work_units=81)
    with pytest.raises(ValueError, match="measured PoW quantity lineage"):
        verify_application_lineage(r, p, forged)


def test_application_lineage_rejects_pow_validation_state_rewrite():
    r = validated_receipt()
    p = apply_post_work_stake(r, consensus_domain="WS-QPOS", epoch=1, requested_stake_units=80)
    app = instantiate_validator_application(
        r,
        p,
        validator_id="validator-1",
        withdrawal_owner="owner-1",
        classical_credential="classical-1",
    )
    forged = replace(app, source_validation_state=WorkValidationState.INDEPENDENTLY_REPRODUCED.value)
    with pytest.raises(ValueError, match="source PoW validation-state lineage"):
        verify_application_lineage(r, p, forged)


def test_all_reviewed_pos_families_receive_reference_projection_only():
    r = validated_receipt()
    p = apply_post_work_stake(r, consensus_domain="WS-QPOS", epoch=1, requested_stake_units=75)
    app = instantiate_validator_application(
        r,
        p,
        validator_id="validator-1",
        withdrawal_owner="owner-1",
        classical_credential="classical-1",
    )
    projections = project_to_all_families(app)
    assert set(projections) == set(PROFILES)
    assert len(projections) == 19
    for projection in projections.values():
        assert projection.normalized_post_work_weight == 75
        assert projection.work_id == r.work_id
        assert projection.evidence_digest == r.evidence_digest
        assert projection.measured_work_units == r.validated_work_units
        assert projection.source_validation_state == r.validation_state.value
        assert projection.application_mode == "WORLDSHEPHERD_REFERENCE_ADAPTER_ONLY"
        assert projection.production_network_adoption_claimed is False


def test_unknown_family_is_rejected():
    r = validated_receipt()
    p = apply_post_work_stake(r, consensus_domain="WS-QPOS", epoch=1, requested_stake_units=50)
    app = instantiate_validator_application(
        r,
        p,
        validator_id="validator-1",
        withdrawal_owner="owner-1",
        classical_credential="classical-1",
    )
    with pytest.raises(ValueError, match="unknown PoS reference profile"):
        project_to_family(app, profile_id="UNKNOWN")


def test_registry_blocks_same_work_receipt_from_multiple_validator_weights_same_epoch():
    r = validated_receipt()
    p = apply_post_work_stake(r, consensus_domain="WS-QPOS", epoch=1, requested_stake_units=50)
    app1 = instantiate_validator_application(
        r,
        p,
        validator_id="validator-1",
        withdrawal_owner="owner-1",
        classical_credential="classical-1",
    )
    app2 = instantiate_validator_application(
        r,
        p,
        validator_id="validator-2",
        withdrawal_owner="owner-1",
        classical_credential="classical-2",
    )
    with pytest.raises(ValueError, match="one applied-work receipt"):
        validate_application_registry((app1, app2))


def test_registry_blocks_pos_weight_beyond_measured_pow():
    r = validated_receipt()
    p = apply_post_work_stake(r, consensus_domain="WS-QPOS", epoch=1, requested_stake_units=50)
    app = instantiate_validator_application(
        r,
        p,
        validator_id="validator-1",
        withdrawal_owner="owner-1",
        classical_credential="classical-1",
    )
    forged = replace(app, measured_work_units=49)
    with pytest.raises(ValueError, match="exceeds measured PoW units"):
        validate_application_registry((forged,))


def test_distinct_work_receipts_can_create_distinct_validator_applications():
    r1 = validated_receipt("work-1", "contributor-1")
    r2 = validated_receipt("work-2", "contributor-2")
    p1 = apply_post_work_stake(r1, consensus_domain="WS-QPOS", epoch=1, requested_stake_units=50)
    p2 = apply_post_work_stake(r2, consensus_domain="WS-QPOS", epoch=1, requested_stake_units=60)
    app1 = instantiate_validator_application(r1, p1, validator_id="validator-1", withdrawal_owner="owner-1", classical_credential="classical-1")
    app2 = instantiate_validator_application(r2, p2, validator_id="validator-2", withdrawal_owner="owner-2", classical_credential="classical-2")
    validate_application_registry((app1, app2))

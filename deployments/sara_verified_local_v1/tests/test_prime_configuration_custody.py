from __future__ import annotations

from worldshepherd_sara.prime_configuration_custody import (
    PrimeActivationDisposition,
    PrimeConfigurationCustodyRecord,
    PrimeCustodyState,
    PrimeEnvironment,
    PrimeMissionPackEvidence,
    REQUALIFICATION_CHECKS,
    apply_post_mission_state,
    evaluate_pack_activation,
    post_mission_state,
    release_from_quarantine,
)


def _space_pack(**overrides):
    values = {
        "pack_id": "SPACE-PACK-1",
        "target_environment": PrimeEnvironment.SPACE,
        "authenticated": True,
        "compatible_with_prime": True,
        "target_environment_qualification_valid": True,
    }
    values.update(overrides)
    return PrimeMissionPackEvidence(**values)


def _authorized_record(**overrides):
    values = {
        "prime_id": "PRIME-001",
        "state": PrimeCustodyState.QUARANTINED_FOR_REQUALIFICATION,
        "last_environment": PrimeEnvironment.SUBTERRA,
        "completed_requalification_checks": list(REQUALIFICATION_CHECKS),
        "requalification_release_authorization_id": "AUTH-2026-0001",
        "requalification_release_target_environment": PrimeEnvironment.SPACE,
        "requalification_release_key_id": "PS-K1",
    }
    values.update(overrides)
    return PrimeConfigurationCustodyRecord(**values)


def test_subterra_and_hadal_missions_enter_requalification_quarantine():
    assert post_mission_state(PrimeEnvironment.SUBTERRA) == PrimeCustodyState.QUARANTINED_FOR_REQUALIFICATION
    assert post_mission_state(PrimeEnvironment.HADAL) == PrimeCustodyState.QUARANTINED_FOR_REQUALIFICATION
    assert post_mission_state(PrimeEnvironment.GROUND) == PrimeCustodyState.READY


def test_post_mission_transition_resets_old_requalification_evidence_and_authorization():
    transitioned = apply_post_mission_state(_authorized_record(), PrimeEnvironment.SUBTERRA)
    assert transitioned.state == PrimeCustodyState.QUARANTINED_FOR_REQUALIFICATION
    assert transitioned.completed_requalification_checks == []
    assert transitioned.requalification_release_authorization_id is None
    assert transitioned.requalification_release_target_environment is None
    assert transitioned.requalification_release_key_id is None


def test_installing_valid_pack_does_not_clear_quarantine_without_evidence():
    record = PrimeConfigurationCustodyRecord(
        prime_id="PRIME-001",
        state=PrimeCustodyState.QUARANTINED_FOR_REQUALIFICATION,
        last_environment=PrimeEnvironment.SUBTERRA,
    )
    disposition, reasons = evaluate_pack_activation(record, _space_pack())
    assert disposition == PrimeActivationDisposition.REQUALIFICATION_REQUIRED
    assert any("TARGET_ENVIRONMENT_ACCEPTANCE" in reason for reason in reasons)


def test_complete_checks_without_authorization_remain_quarantined():
    record = PrimeConfigurationCustodyRecord(
        prime_id="PRIME-001",
        state=PrimeCustodyState.QUARANTINED_FOR_REQUALIFICATION,
        completed_requalification_checks=list(REQUALIFICATION_CHECKS),
    )
    disposition, reasons = evaluate_pack_activation(record, _space_pack())
    assert disposition == PrimeActivationDisposition.REQUALIFICATION_REQUIRED
    assert any("authorization record" in reason for reason in reasons)


def test_target_bound_authorization_and_valid_pack_allow_release_and_clear_one_time_binding():
    record = _authorized_record()
    released, disposition, reasons = release_from_quarantine(record, _space_pack())
    assert disposition == PrimeActivationDisposition.ACTIVATION_ALLOWED
    assert released.state == PrimeCustodyState.READY
    assert released.requalification_release_authorization_id is None
    assert released.requalification_release_target_environment is None
    assert released.requalification_release_key_id is None
    assert reasons


def test_authorization_target_mismatch_fails_closed():
    record = _authorized_record(
        requalification_release_target_environment=PrimeEnvironment.AERO
    )
    disposition, reasons = evaluate_pack_activation(record, _space_pack())
    assert disposition == PrimeActivationDisposition.DENIED
    assert any("target environment" in reason for reason in reasons)


def test_authorization_without_signing_key_binding_fails_closed():
    record = _authorized_record(requalification_release_key_id=None)
    disposition, reasons = evaluate_pack_activation(record, _space_pack())
    assert disposition == PrimeActivationDisposition.DENIED
    assert any("signing key" in reason for reason in reasons)


def test_invalid_target_environment_qualification_fails_closed():
    disposition, reasons = evaluate_pack_activation(
        _authorized_record(),
        _space_pack(target_environment_qualification_valid=False),
    )
    assert disposition == PrimeActivationDisposition.DENIED
    assert any("target-environment qualification" in reason for reason in reasons)


def test_unauthenticated_or_incompatible_pack_fails_closed():
    record = PrimeConfigurationCustodyRecord(prime_id="PRIME-001")
    disposition, reasons = evaluate_pack_activation(
        record,
        _space_pack(authenticated=False, compatible_with_prime=False),
    )
    assert disposition == PrimeActivationDisposition.DENIED
    assert any("not authenticated" in reason for reason in reasons)
    assert any("not compatible" in reason for reason in reasons)

from __future__ import annotations

from worldshepherd_sara.prime_configuration_custody import (
    PrimeActivationDisposition,
    PrimeConfigurationCustodyRecord,
    PrimeCustodyState,
    PrimeEnvironment,
    PrimeMissionPackEvidence,
    REQUALIFICATION_CHECKS,
    evaluate_pack_activation,
    post_mission_state,
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


def test_subterra_and_hadal_missions_enter_requalification_quarantine():
    assert post_mission_state(PrimeEnvironment.SUBTERRA) == PrimeCustodyState.QUARANTINED_FOR_REQUALIFICATION
    assert post_mission_state(PrimeEnvironment.HADAL) == PrimeCustodyState.QUARANTINED_FOR_REQUALIFICATION
    assert post_mission_state(PrimeEnvironment.GROUND) == PrimeCustodyState.READY


def test_installing_a_valid_space_pack_does_not_clear_quarantine_by_itself():
    record = PrimeConfigurationCustodyRecord(
        prime_id="PRIME-001",
        state=PrimeCustodyState.QUARANTINED_FOR_REQUALIFICATION,
        last_environment=PrimeEnvironment.SUBTERRA,
    )
    disposition, reasons = evaluate_pack_activation(record, _space_pack())
    assert disposition == PrimeActivationDisposition.REQUALIFICATION_REQUIRED
    assert any("quarantined" in reason for reason in reasons)
    assert any("TARGET_ENVIRONMENT_ACCEPTANCE" in reason for reason in reasons)


def test_complete_checks_without_release_authorization_remain_quarantined():
    record = PrimeConfigurationCustodyRecord(
        prime_id="PRIME-001",
        state=PrimeCustodyState.QUARANTINED_FOR_REQUALIFICATION,
        last_environment=PrimeEnvironment.SUBTERRA,
        completed_requalification_checks=list(REQUALIFICATION_CHECKS),
    )
    disposition, reasons = evaluate_pack_activation(record, _space_pack())
    assert disposition == PrimeActivationDisposition.REQUALIFICATION_REQUIRED
    assert any("not authorized" in reason for reason in reasons)


def test_complete_requalification_authorization_and_valid_pack_allow_activation():
    record = PrimeConfigurationCustodyRecord(
        prime_id="PRIME-001",
        state=PrimeCustodyState.QUARANTINED_FOR_REQUALIFICATION,
        last_environment=PrimeEnvironment.SUBTERRA,
        completed_requalification_checks=list(REQUALIFICATION_CHECKS),
        requalification_release_authorized=True,
    )
    disposition, reasons = evaluate_pack_activation(record, _space_pack())
    assert disposition == PrimeActivationDisposition.ACTIVATION_ALLOWED
    assert reasons


def test_invalid_target_environment_qualification_fails_closed_even_after_checks():
    record = PrimeConfigurationCustodyRecord(
        prime_id="PRIME-001",
        state=PrimeCustodyState.QUARANTINED_FOR_REQUALIFICATION,
        last_environment=PrimeEnvironment.HADAL,
        completed_requalification_checks=list(REQUALIFICATION_CHECKS),
        requalification_release_authorized=True,
    )
    disposition, reasons = evaluate_pack_activation(
        record,
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

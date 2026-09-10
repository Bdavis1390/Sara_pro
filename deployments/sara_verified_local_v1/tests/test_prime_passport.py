from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from worldshepherd_sara.prime_configuration_custody import (
    REQUALIFICATION_CHECKS,
    PrimeActivationDisposition,
    PrimeCustodyState,
    PrimeEnvironment,
    PrimeMissionPackEvidence,
)
from worldshepherd_sara.prime_passport import (
    PRIME_CUSTODY_PROVENANCE_SCHEMA,
    PrimeMissionCompletionRequest,
    PrimePackActivationRequest,
    PrimeRequalificationEvidenceRequest,
    activate_pack,
    apply_verified_requalification_authorization,
    complete_mission,
    create_passport,
    load_passport,
    passport_registry_patch,
    update_requalification_evidence,
)
from worldshepherd_sara.prime_sentinel_authorization import (
    VerifiedPrimeSentinelAuthorization,
)


def _qualified_space_pack() -> PrimeMissionPackEvidence:
    return PrimeMissionPackEvidence(
        pack_id="SPACE-PACK-001",
        target_environment=PrimeEnvironment.SPACE,
        authenticated=True,
        compatible_with_prime=True,
        target_environment_qualification_valid=True,
    )


def _verified_authorization() -> VerifiedPrimeSentinelAuthorization:
    now = datetime.now(timezone.utc)
    return VerifiedPrimeSentinelAuthorization(
        authorization_id="AUTH-REQUAL-001",
        prime_id="PRIME-001",
        target_environment=PrimeEnvironment.SPACE,
        key_id="PS-K1",
        key_fingerprint_sha256="a" * 64,
        nonce="nonce-0123456789abcdef",
        issued_at=now,
        expires_at=now + timedelta(minutes=5),
    )


def _quarantined_complete_passport():
    passport = create_passport(
        prime_id="PRIME-001",
        hardware_revision="HW-A",
        software_revision="SW-A",
    )
    passport, _ = complete_mission(
        passport,
        PrimeMissionCompletionRequest(environment=PrimeEnvironment.SUBTERRA),
    )
    passport, _ = update_requalification_evidence(
        passport,
        PrimeRequalificationEvidenceRequest(
            completed_checks=list(REQUALIFICATION_CHECKS),
            evidence_refs=["ECHO:REQUAL:002"],
        ),
    )
    return passport


def test_passport_round_trips_through_registry_namespace():
    passport = create_passport(
        prime_id="PRIME-001",
        hardware_revision="HW-A",
        software_revision="SW-A",
        evidence_refs=["ECHO:BUILD:001"],
    )
    registry = passport_registry_patch({}, passport)
    assert load_passport(registry, "PRIME-001") == passport


def test_hazardous_mission_clears_pack_and_enters_quarantine_with_provenance():
    passport = create_passport(
        prime_id="PRIME-001",
        hardware_revision="HW-A",
        software_revision="SW-A",
    ).model_copy(update={"installed_pack": _qualified_space_pack()})
    updated, event = complete_mission(
        passport,
        PrimeMissionCompletionRequest(
            environment=PrimeEnvironment.SUBTERRA,
            evidence_refs=["ECHO:MISSION:SUBTERRA:001"],
        ),
    )
    assert updated.custody.state == PrimeCustodyState.QUARANTINED_FOR_REQUALIFICATION
    assert updated.installed_pack is None
    assert event["schema"] == PRIME_CUSTODY_PROVENANCE_SCHEMA
    assert event["previous_state"] == "READY"
    assert event["new_state"] == "QUARANTINED_FOR_REQUALIFICATION"


def test_complete_evidence_without_authorization_does_not_activate_pack():
    passport = _quarantined_complete_passport()
    updated, disposition, reasons, event = activate_pack(
        passport,
        PrimePackActivationRequest(pack=_qualified_space_pack()),
    )
    assert disposition == PrimeActivationDisposition.REQUALIFICATION_REQUIRED
    assert updated == passport
    assert any("authorization" in reason for reason in reasons)
    assert event["details"]["disposition"] == "REQUALIFICATION_REQUIRED"


def test_verified_authorization_binds_target_and_key_then_allows_release():
    passport = _quarantined_complete_passport()
    passport, authorization_event = apply_verified_requalification_authorization(
        passport, _verified_authorization()
    )
    assert passport.custody.requalification_release_authorization_id == "AUTH-REQUAL-001"
    assert passport.custody.requalification_release_target_environment == PrimeEnvironment.SPACE
    assert passport.custody.requalification_release_key_id == "PS-K1"
    assert authorization_event["details"]["key_id"] == "PS-K1"

    updated, disposition, reasons, activation_event = activate_pack(
        passport,
        PrimePackActivationRequest(
            pack=_qualified_space_pack(),
            evidence_refs=["ECHO:PACK:SPACE:001"],
        ),
    )
    assert disposition == PrimeActivationDisposition.ACTIVATION_ALLOWED
    assert reasons
    assert updated.custody.state == PrimeCustodyState.READY
    assert updated.installed_pack is not None
    assert updated.last_transition_id == activation_event["transition_id"]


def test_requalification_evidence_change_clears_prior_authorization():
    passport = _quarantined_complete_passport()
    passport, _ = apply_verified_requalification_authorization(
        passport, _verified_authorization()
    )
    updated, event = update_requalification_evidence(
        passport,
        PrimeRequalificationEvidenceRequest(
            completed_checks=list(REQUALIFICATION_CHECKS),
            evidence_refs=["ECHO:REQUAL:CHANGED"],
        ),
    )
    assert updated.custody.requalification_release_authorization_id is None
    assert updated.custody.requalification_release_target_environment is None
    assert updated.custody.requalification_release_key_id is None
    assert event["details"]["prior_authorization_cleared"] is True


def test_authorization_cannot_be_applied_before_evidence_is_complete():
    passport = create_passport(
        prime_id="PRIME-001", hardware_revision="HW-A", software_revision="SW-A"
    )
    passport, _ = complete_mission(
        passport, PrimeMissionCompletionRequest(environment=PrimeEnvironment.HADAL)
    )
    with pytest.raises(ValueError, match="incomplete"):
        apply_verified_requalification_authorization(passport, _verified_authorization())


def test_arbitrary_authorization_id_is_not_accepted_as_requalification_evidence():
    with pytest.raises(ValueError):
        PrimeRequalificationEvidenceRequest(
            completed_checks=list(REQUALIFICATION_CHECKS),
            release_authorization_id="UNVERIFIED-BYPASS",
        )


def test_unknown_requalification_check_is_rejected():
    with pytest.raises(ValueError):
        PrimeRequalificationEvidenceRequest(completed_checks=["NOT_A_REAL_GATE"])


def test_corrupt_or_identity_mismatched_registry_passport_fails_closed():
    registry = {
        "PRIME_DIGITAL_PASSPORTS": {
            "PRIME-001": {
                "prime_id": "PRIME-OTHER",
                "hardware_revision": "HW-A",
                "software_revision": "SW-A",
                "custody": {"prime_id": "PRIME-OTHER"},
            }
        }
    }
    with pytest.raises(ValueError, match="identity mismatch"):
        load_passport(registry, "PRIME-001")

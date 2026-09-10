from __future__ import annotations

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
    complete_mission,
    create_passport,
    load_passport,
    passport_registry_patch,
    update_requalification_evidence,
)


def _qualified_space_pack() -> PrimeMissionPackEvidence:
    return PrimeMissionPackEvidence(
        pack_id="SPACE-PACK-001",
        target_environment=PrimeEnvironment.SPACE,
        authenticated=True,
        compatible_with_prime=True,
        target_environment_qualification_valid=True,
    )


def test_passport_round_trips_through_registry_namespace():
    passport = create_passport(
        prime_id="PRIME-001",
        hardware_revision="HW-A",
        software_revision="SW-A",
        evidence_refs=["ECHO:BUILD:001"],
    )
    registry = passport_registry_patch({}, passport)
    restored = load_passport(registry, "PRIME-001")
    assert restored == passport


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
    assert event["provenance_channel"] == "SARA_AUDIT_FOR_ECHO_INGEST"


def test_complete_evidence_without_authorization_does_not_activate_pack():
    passport = create_passport(
        prime_id="PRIME-001",
        hardware_revision="HW-A",
        software_revision="SW-A",
    )
    passport, _ = complete_mission(
        passport,
        PrimeMissionCompletionRequest(environment=PrimeEnvironment.HADAL),
    )
    passport, _ = update_requalification_evidence(
        passport,
        PrimeRequalificationEvidenceRequest(
            completed_checks=list(REQUALIFICATION_CHECKS),
            evidence_refs=["ECHO:REQUAL:001"],
        ),
    )

    updated, disposition, reasons, event = activate_pack(
        passport,
        PrimePackActivationRequest(pack=_qualified_space_pack()),
    )

    assert disposition == PrimeActivationDisposition.REQUALIFICATION_REQUIRED
    assert updated == passport
    assert updated.custody.state == PrimeCustodyState.QUARANTINED_FOR_REQUALIFICATION
    assert updated.installed_pack is None
    assert any("authorization" in reason for reason in reasons)
    assert event["details"]["disposition"] == "REQUALIFICATION_REQUIRED"


def test_authorized_complete_requalification_releases_and_installs_pack():
    passport = create_passport(
        prime_id="PRIME-001",
        hardware_revision="HW-A",
        software_revision="SW-A",
    )
    passport, _ = complete_mission(
        passport,
        PrimeMissionCompletionRequest(environment=PrimeEnvironment.SUBTERRA),
    )
    passport, evidence_event = update_requalification_evidence(
        passport,
        PrimeRequalificationEvidenceRequest(
            completed_checks=list(REQUALIFICATION_CHECKS),
            evidence_refs=["ECHO:REQUAL:002"],
            release_authorization_id="AUTH-REQUAL-001",
        ),
    )
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
    assert updated.installed_pack.pack_id == "SPACE-PACK-001"
    assert updated.last_transition_id == activation_event["transition_id"]
    assert evidence_event["details"]["authorization_id"] == "AUTH-REQUAL-001"
    assert activation_event["details"]["authorization_id"] == "AUTH-REQUAL-001"


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

from worldshepherd_sara.observer_authority import (
    ObserverAuthorityPacket,
    REQUIRED_AUTHORITY_FIELDS,
    missing_authorities,
)


def complete_packet() -> ObserverAuthorityPacket:
    return ObserverAuthorityPacket(
        device="MAST",
        reconstruction_family="external-equilibrium-observer",
        authority_provenance={
            "diagnostic_geometry_and_calibration": "authority:diagnostic-geometry-calibration",
            "passive_structure_model": "authority:passive-structure",
            "response_matrices_or_generation_method": "authority:response-model",
            "reconstruction_settings": "authority:solver-settings",
            "coordinate_conventions": "authority:coordinate-conventions",
        },
        validated_by="authoritative-source-review",
        validation_reference="authority-review:fixture",
    )


def test_complete_authority_packet_passes_completeness_gate():
    packet = complete_packet()
    assert packet.validate() == (True, "ok")
    assert packet.authority_complete is True
    assert missing_authorities(packet) == ()


def test_each_required_authority_fails_closed_when_missing():
    baseline = complete_packet()
    for field in REQUIRED_AUTHORITY_FIELDS:
        authorities = dict(baseline.authority_provenance)
        authorities[field] = ""
        packet = ObserverAuthorityPacket(
            device=baseline.device,
            reconstruction_family=baseline.reconstruction_family,
            authority_provenance=authorities,
            validated_by=baseline.validated_by,
            validation_reference=baseline.validation_reference,
        )
        assert packet.validate() == (False, f"authority_missing:{field}")
        assert field in missing_authorities(packet)


def test_validation_identity_and_reference_are_required():
    baseline = complete_packet()
    missing_validator = ObserverAuthorityPacket(
        device=baseline.device,
        reconstruction_family=baseline.reconstruction_family,
        authority_provenance=baseline.authority_provenance,
        validated_by="",
        validation_reference=baseline.validation_reference,
    )
    assert missing_validator.validate() == (False, "validated_by_missing")

    missing_reference = ObserverAuthorityPacket(
        device=baseline.device,
        reconstruction_family=baseline.reconstruction_family,
        authority_provenance=baseline.authority_provenance,
        validated_by=baseline.validated_by,
        validation_reference="",
    )
    assert missing_reference.validate() == (False, "validation_reference_missing")

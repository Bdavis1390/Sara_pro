from __future__ import annotations

import pytest

from worldshepherd_sara.software_provenance import (
    AttestationState,
    BuildProvenance,
    SoftwareComponent,
)


def test_internal_unsigned_provenance_is_machine_readable_and_claims_bounded():
    provenance = BuildProvenance(
        provenance_id="WS-BUILD-001",
        source_repository="Bdavis1390/Sara_pro",
        source_commit="abc123",
        builder_id="github-actions",
        build_environment_digest="sha256:env",
        output_artifact_digest="sha256:artifact",
        components=[SoftwareComponent(name="fastapi", version="0.141.1", package_type="pypi")],
        sbom_digest="sha256:sbom",
    )
    assert provenance.attestation_state == AttestationState.INTERNAL_UNSIGNED
    assert provenance.digest().startswith("sha256:")
    assert "no external signing" in provenance.claims_boundary().lower()


def test_signed_and_external_states_require_corresponding_evidence():
    with pytest.raises(ValueError):
        BuildProvenance(
            provenance_id="BAD1",
            source_repository="repo",
            source_commit="c",
            builder_id="b",
            build_environment_digest="sha256:e",
            output_artifact_digest="sha256:o",
            attestation_state=AttestationState.INTERNALLY_SIGNED,
        )
    with pytest.raises(ValueError):
        BuildProvenance(
            provenance_id="BAD2",
            source_repository="repo",
            source_commit="c",
            builder_id="b",
            build_environment_digest="sha256:e",
            output_artifact_digest="sha256:o",
            attestation_state=AttestationState.EXTERNALLY_VERIFIED,
            signature_ref="sig://1",
        )

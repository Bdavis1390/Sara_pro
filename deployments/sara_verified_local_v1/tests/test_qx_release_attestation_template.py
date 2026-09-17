from pathlib import Path


def test_release_attestation_requires_evidence_references_for_high_claims():
    text = (Path(__file__).parents[1] / "docs" / "WS_QX_RELEASE_ATTESTATION_TEMPLATE.md").read_text()
    assert "evidence reference if YES" in text
    assert "program evidence reference if YES" in text
    assert "not a substitute for the referenced evidence" in text

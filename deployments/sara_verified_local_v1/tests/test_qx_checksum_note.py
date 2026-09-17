from pathlib import Path


def test_digest_does_not_replace_repository_or_ci_provenance():
    text = (Path(__file__).parents[1] / "docs" / "WS_QX_RELEASE_CANDIDATE_CHECKSUM_NOTE.md").read_text()
    assert "do not replace Git commit identity, CI provenance" in text

from pathlib import Path


def test_release_candidate_requires_exact_head_ci():
    path = Path(__file__).parents[1] / "docs" / "WS_QX_0_1_RELEASE_CANDIDATE.md"
    text = path.read_text()
    assert "Acceptance requires exact-head CI" in text
    assert "Do not merge on historical or earlier-head workflow results" in text

from pathlib import Path


def test_pr_phase_active():
    assert "PR PHASE ACTIVE" in (Path(__file__).parents[1] / "docs" / "WS_QX_PR_ACTIVATE.md").read_text()

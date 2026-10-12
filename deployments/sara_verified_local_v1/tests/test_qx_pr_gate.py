from pathlib import Path


def test_pr_ci_gate_begins():
    assert "PR/CI gate begins" in (Path(__file__).parents[1] / "docs" / "WS_QX_PR_GATE.md").read_text()

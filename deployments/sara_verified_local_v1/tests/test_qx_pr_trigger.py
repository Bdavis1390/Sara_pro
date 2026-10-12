from pathlib import Path


def test_pr_handoff_uses_exact_head_workflows():
    text = (Path(__file__).parents[1] / "docs" / "WS_QX_PR_TRIGGER.md").read_text()
    assert "Exact-head workflow results control publication acceptance" in text

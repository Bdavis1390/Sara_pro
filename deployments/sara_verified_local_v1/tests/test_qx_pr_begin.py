from pathlib import Path


def test_begin_pr_phase():
    assert "BEGIN PR PHASE" in (Path(__file__).parents[1] / "docs" / "WS_QX_PR_BEGIN.md").read_text()

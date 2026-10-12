from pathlib import Path


def test_final_handoff_is_ci_next():
    text = (Path(__file__).parents[1] / "docs" / "WS_QX_PR_HANDOFF_FINAL.md").read_text()
    assert "Observe exact-head CI" in text

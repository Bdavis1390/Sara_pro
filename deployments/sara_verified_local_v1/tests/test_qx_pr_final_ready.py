from pathlib import Path


def test_final_ready_for_pull_request():
    assert "FINAL READY FOR PULL REQUEST" in (Path(__file__).parents[1] / "docs" / "WS_QX_PR_FINAL_READY.md").read_text()

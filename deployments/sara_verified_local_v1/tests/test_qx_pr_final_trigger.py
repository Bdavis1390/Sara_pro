from pathlib import Path


def test_final_trigger_stops_content_commits():
    assert "no more content commits" in (Path(__file__).parents[1] / "docs" / "WS_QX_PR_FINAL_TRIGGER.md").read_text()

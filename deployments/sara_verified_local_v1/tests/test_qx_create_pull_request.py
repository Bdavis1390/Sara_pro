from pathlib import Path


def test_create_pull_request_marker():
    assert "CREATE PULL REQUEST" in (Path(__file__).parents[1] / "docs" / "WS_QX_CREATE_PULL_REQUEST.md").read_text()

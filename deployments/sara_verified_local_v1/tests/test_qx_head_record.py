from pathlib import Path


def test_head_record_uses_pr_reported_sha():
    text = (Path(__file__).parents[1] / "docs" / "WS_QX_HEAD_RECORD.md").read_text()
    assert "pull request's reported head SHA" in text
    assert "do not infer it from an earlier file-creation response" in text

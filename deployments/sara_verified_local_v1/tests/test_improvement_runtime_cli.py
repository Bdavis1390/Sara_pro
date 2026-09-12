from __future__ import annotations

import json

from worldshepherd_sara.improvement_runtime_cli import main


def test_runtime_cli_status_uses_configured_local_store(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("WSRI_DATA_DIR", str((tmp_path / "wsri").resolve()))
    monkeypatch.delenv("WSRI_ECHO_DATA_DIR", raising=False)

    assert main(["status"]) == 0
    body = json.loads(capsys.readouterr().out)
    assert body["record_count"] == 0
    assert body["ledger_chain_verified"] is True
    assert body["autonomous_scheduler_active"] is False
    assert body["claim_promotion_performed"] is False
    assert body["deployment_performed"] is False


def test_runtime_cli_records_is_bounded_local_export(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("WSRI_DATA_DIR", str((tmp_path / "wsri").resolve()))
    monkeypatch.delenv("WSRI_ECHO_DATA_DIR", raising=False)

    assert main(["records", "--limit", "10"]) == 0
    body = json.loads(capsys.readouterr().out)
    assert body["records"] == []
    assert body["claims_boundary"] == "bounded local custody export only"

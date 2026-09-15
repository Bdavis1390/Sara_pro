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


def test_runtime_cli_evidence_manifest_is_verifiable_shape(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("WSRI_DATA_DIR", str((tmp_path / "wsri").resolve()))
    monkeypatch.delenv("WSRI_ECHO_DATA_DIR", raising=False)

    assert main([
        "evidence-manifest",
        "--generated-utc",
        "2026-09-12T21:10:00+00:00",
    ]) == 0
    body = json.loads(capsys.readouterr().out)
    assert body["schema"] == "ws-ri-evidence-manifest-1"
    assert body["record_count"] == 0
    assert body["ledger_chain_verified"] is True
    assert body["claim_promotion_performed"] is False
    assert body["deployment_performed"] is False
    assert body["manifest_digest"]


def test_runtime_cli_handoff_requires_authorized_scheduler_or_human(tmp_path, monkeypatch, capsys):
    wsri = (tmp_path / "wsri").resolve()
    echo = (tmp_path / "echo").resolve()
    echo.mkdir(mode=0o700)
    monkeypatch.setenv("WSRI_DATA_DIR", str(wsri))
    monkeypatch.setenv("WSRI_ECHO_DATA_DIR", str(echo))

    assert main([
        "handoff",
        "--requested-by",
        "operator",
        "--generated-utc",
        "2026-09-12T21:11:00+00:00",
        "--max-events",
        "8",
        "--max-proposals",
        "4",
    ]) == 0
    body = json.loads(capsys.readouterr().out)
    assert body["schema"] == "ws-ri-scheduler-handoff-1"
    assert body["execution_disposition"] == "HUMAN_REVIEW_REQUIRED"
    assert body["authorization_required"] is True
    assert body["autonomous_execution_authorized"] is False
    assert body["claim_promotion_authorized"] is False
    assert body["deployment_authorized"] is False
    assert body["external_execution_authorized"] is False

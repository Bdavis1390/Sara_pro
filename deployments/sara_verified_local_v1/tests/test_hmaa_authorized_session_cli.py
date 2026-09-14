from __future__ import annotations

import sys

import pytest

from worldshepherd_sara import hmaa_authorized_session_cli


def test_existing_output_directory_blocks_before_network_runner(tmp_path, monkeypatch):
    output_dir = tmp_path / "already-exists"
    output_dir.mkdir()
    called = False

    def forbidden_runner(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("network-capable session runner must not be invoked")

    monkeypatch.setattr(
        hmaa_authorized_session_cli,
        "run_authorized_read_session",
        forbidden_runner,
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "ws-hmaa-sandbox-session",
            "--mission-id",
            "CLI-PREFLIGHT-001",
            "--execute-network",
            "--authorization-confirmed",
            "--out",
            str(output_dir),
        ],
    )

    with pytest.raises(SystemExit, match="new --out directory; no network call was made"):
        hmaa_authorized_session_cli.main()

    assert called is False


def test_missing_authorization_blocks_before_network_runner(tmp_path, monkeypatch):
    output_dir = tmp_path / "new-output"
    called = False

    def forbidden_runner(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("network-capable session runner must not be invoked")

    monkeypatch.setattr(
        hmaa_authorized_session_cli,
        "run_authorized_read_session",
        forbidden_runner,
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "ws-hmaa-sandbox-session",
            "--mission-id",
            "CLI-AUTH-001",
            "--execute-network",
            "--out",
            str(output_dir),
        ],
    )

    with pytest.raises(SystemExit, match="--authorization-confirmed; no network call was made"):
        hmaa_authorized_session_cli.main()

    assert called is False
    assert output_dir.exists() is False


def test_default_cli_path_is_zero_network_preflight(monkeypatch, capsys):
    called = False

    def forbidden_runner(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("default CLI path must not invoke network-capable runner")

    monkeypatch.setattr(
        hmaa_authorized_session_cli,
        "run_authorized_read_session",
        forbidden_runner,
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "ws-hmaa-sandbox-session",
            "--mission-id",
            "CLI-DRY-RUN-001",
            "--max-entity-messages",
            "1",
            "--max-task-messages",
            "0",
        ],
    )

    hmaa_authorized_session_cli.main()
    rendered = capsys.readouterr().out

    assert called is False
    assert '"network_call_performed": false' in rendered
    assert '"network_enabled": false' in rendered
    assert '"live_environment_validated": false' in rendered

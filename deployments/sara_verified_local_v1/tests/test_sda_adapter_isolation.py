from __future__ import annotations

import os
import sys

import pytest
from pydantic import ValidationError

from worldshepherd_sara.sda_adapter_isolation import (
    SdaAdapterIsolationError,
    SdaAdapterIsolationPolicy,
    SdaAdapterRunStatus,
    run_isolated_adapter,
)


def policy(**overrides) -> SdaAdapterIsolationPolicy:
    values = {
        "policy_id": "SDA-ADAPTER-ISOLATION-G3A-TEST",
        "adapter_id": "WS-SDA-TEST-ADAPTER",
        "adapter_version": "1.0.0",
        "executable_path": sys.executable,
        "max_input_bytes": 1024,
        "max_output_bytes": 4096,
        "max_stderr_bytes": 4096,
        "timeout_seconds": 2.0,
        "cpu_seconds": 1,
        "memory_limit_bytes": 256 * 1024 * 1024,
        "max_open_files": 32,
        "allow_exit_codes": [0],
    }
    values.update(overrides)
    return SdaAdapterIsolationPolicy.model_validate(values)


def test_policy_rejects_relative_executable_and_duplicate_exit_codes():
    with pytest.raises(ValidationError, match="must be absolute"):
        policy(executable_path="python3")

    with pytest.raises(ValidationError, match="duplicates"):
        policy(allow_exit_codes=[0, 0])


def test_input_quota_rejects_before_adapter_execution():
    result = run_isolated_adapter(
        policy=policy(max_input_bytes=4),
        arguments=["-c", "raise SystemExit('should not execute')"],
        payload=b"12345",
    )

    assert result.status == SdaAdapterRunStatus.INPUT_REJECTED
    assert result.return_code is None
    assert result.input_bytes == 5
    assert result.stdout == b""
    assert result.stderr == b""


def test_successful_adapter_has_ephemeral_cwd_and_minimal_environment(monkeypatch):
    monkeypatch.setenv("WS_SECRET_SHOULD_NOT_LEAK", "super-secret")
    code = (
        "import os,sys;"
        "data=sys.stdin.buffer.read();"
        "print(os.getcwd());"
        "print(os.getenv('WS_SECRET_SHOULD_NOT_LEAK','MISSING'));"
        "sys.stdout.buffer.write(data)"
    )
    result = run_isolated_adapter(
        policy=policy(),
        arguments=["-c", code],
        payload=b"PAYLOAD",
    )

    assert result.status == SdaAdapterRunStatus.SUCCEEDED
    assert result.return_code == 0
    assert b"ws-sda-adapter-" in result.stdout
    assert b"MISSING" in result.stdout
    assert b"super-secret" not in result.stdout
    # Text and binary writes may flush in either order across Python runtimes;
    # the security invariant is presence without secret leakage, not stream order.
    assert b"PAYLOAD" in result.stdout
    assert result.environment_keys_exposed == [
        "LANG",
        "LC_ALL",
        "PYTHONDONTWRITEBYTECODE",
        "PYTHONNOUSERSITE",
    ]
    assert result.working_directory_ephemeral is True
    assert result.network_isolation_enforced is False
    assert "No network namespace" in result.claims_boundary


def test_shell_metacharacters_are_literal_arguments_not_shell_commands(tmp_path):
    marker = tmp_path / "must-not-exist"
    hostile = f"; touch {marker}"
    code = "import sys; print(repr(sys.argv[1]))"
    result = run_isolated_adapter(
        policy=policy(),
        arguments=["-c", code, hostile],
        payload=b"",
    )

    assert result.status == SdaAdapterRunStatus.SUCCEEDED
    assert hostile.encode() in result.stdout
    assert not marker.exists()


def test_wall_clock_timeout_kills_adapter_process_group():
    result = run_isolated_adapter(
        policy=policy(timeout_seconds=0.25, cpu_seconds=2),
        arguments=["-c", "import time; time.sleep(5)"],
        payload=b"",
    )

    assert result.status == SdaAdapterRunStatus.TIMED_OUT
    assert result.return_code is not None


def test_stdout_quota_is_enforced_and_output_is_bounded():
    result = run_isolated_adapter(
        policy=policy(max_output_bytes=128, max_stderr_bytes=128),
        arguments=["-c", "import sys; sys.stdout.write('X' * 100000)"],
        payload=b"",
    )

    assert result.status == SdaAdapterRunStatus.OUTPUT_LIMIT_EXCEEDED
    assert len(result.stdout) <= 128
    assert result.stdout_bytes <= 128


def test_stderr_quota_is_enforced_and_output_is_bounded():
    result = run_isolated_adapter(
        policy=policy(max_output_bytes=128, max_stderr_bytes=128),
        arguments=["-c", "import sys; sys.stderr.write('E' * 100000)"],
        payload=b"",
    )

    assert result.status == SdaAdapterRunStatus.OUTPUT_LIMIT_EXCEEDED
    assert len(result.stderr) <= 128
    assert result.stderr_bytes <= 128


def test_non_allowed_exit_code_fails_closed():
    result = run_isolated_adapter(
        policy=policy(),
        arguments=["-c", "raise SystemExit(7)"],
        payload=b"",
    )

    assert result.status == SdaAdapterRunStatus.PROCESS_FAILED
    assert result.return_code == 7


def test_missing_configured_executable_fails_before_execution():
    missing = policy(executable_path="/definitely/not/a/worldshepherd/adapter")
    with pytest.raises(SdaAdapterIsolationError, match="does not exist"):
        run_isolated_adapter(
            policy=missing,
            arguments=["--anything"],
            payload=b"",
        )


def test_argument_shape_and_nul_are_rejected_without_shell_interpretation():
    with pytest.raises(SdaAdapterIsolationError, match="NUL"):
        run_isolated_adapter(
            policy=policy(),
            arguments=["bad\x00argument"],
            payload=b"",
        )

    with pytest.raises(SdaAdapterIsolationError, match="count exceeds"):
        run_isolated_adapter(
            policy=policy(),
            arguments=["x"] * 65,
            payload=b"",
        )

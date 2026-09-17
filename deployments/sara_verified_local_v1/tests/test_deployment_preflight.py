from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from worldshepherd_sara.deployment_preflight import (
    DeploymentPreflightError,
    validate_deployment,
)


HEAD = "a" * 40


def _write_secret(path: Path) -> Path:
    path.write_text("test-secret-material\n", encoding="utf-8")
    path.chmod(0o600)
    return path.resolve()


def _env(tmp_path: Path, **overrides: str) -> Path:
    prime_key = _write_secret(tmp_path / "prime-key")
    prime_token = _write_secret(tmp_path / "prime-token")
    echo_token = _write_secret(tmp_path / "echo-token")
    echo_key = _write_secret(tmp_path / "echo-key")
    values = {
        "SARA_RELAY_TOKEN": "relay-" + "a" * 32,
        "SARA_ADMIN_TOKEN": "admin-" + "b" * 32,
        "SARA_BUILD_COMMIT": HEAD,
        "SARA_RELEASE_ID": "ws-local-test",
        "SARA_HOST_PORT": "9530",
        "PRIME_SENTINEL_HOST_PORT": "9540",
        "ECHO_HOST_PORT": "9550",
        "PRIME_SENTINEL_SIGNING_KEY_ID": "PS-LOCAL-V1",
        "PRIME_SENTINEL_PUBLIC_KEYS_JSON": json.dumps(
            {"PS-LOCAL-V1": "A" * 43},
            separators=(",", ":"),
        ),
        "ECHO_CHECKPOINT_KEY_ID": "ECHO-LOCAL-V1",
        "ECHO_CHECKPOINT_SIGNER_MODE": "LOCAL_PEM",
        "PRIME_SENTINEL_PRIVATE_KEY_HOST_PATH": str(prime_key),
        "PRIME_SENTINEL_SERVICE_TOKEN_HOST_PATH": str(prime_token),
        "ECHO_INGEST_TOKEN_HOST_PATH": str(echo_token),
        "ECHO_CHECKPOINT_PRIVATE_KEY_HOST_PATH": str(echo_key),
    }
    values.update(overrides)
    path = tmp_path / ".env"
    path.write_text(
        "\n".join(f"{key}={value}" for key, value in values.items()) + "\n",
        encoding="utf-8",
    )
    path.chmod(0o600)
    return path


def test_valid_local_full_stack_preflight(tmp_path):
    receipt = validate_deployment(
        _env(tmp_path),
        expected_head=HEAD,
        required_uid=os.geteuid(),
    )

    assert receipt["status"] == "PASS"
    assert receipt["build_commit"] == HEAD
    assert receipt["echo_signer_mode"] == "LOCAL_PEM"
    assert receipt["sara_tokens"]["independent"] is True
    assert len(receipt["sanitized_config_sha256"]) == 64
    rendered = json.dumps(receipt)
    assert "relay-" + "a" * 32 not in rendered
    assert "admin-" + "b" * 32 not in rendered


@pytest.mark.parametrize(
    ("name", "value", "match"),
    [
        ("SARA_RELEASE_ID", "UNVERIFIED", "placeholder"),
        ("SARA_BUILD_COMMIT", "UNKNOWN", "40-character"),
        ("PRIME_SENTINEL_SIGNING_KEY_ID", "UNCONFIGURED", "placeholder"),
        ("ECHO_CHECKPOINT_SIGNER_MODE", "EXTERNAL", "LOCAL_PEM"),
    ],
)
def test_preflight_rejects_unpromotable_configuration(
    tmp_path,
    name,
    value,
    match,
):
    with pytest.raises(DeploymentPreflightError, match=match):
        validate_deployment(
            _env(tmp_path, **{name: value}),
            expected_head=HEAD,
            required_uid=os.geteuid(),
        )


def test_preflight_rejects_commit_mismatch(tmp_path):
    with pytest.raises(DeploymentPreflightError, match="does not match"):
        validate_deployment(
            _env(tmp_path),
            expected_head="b" * 40,
            required_uid=os.geteuid(),
        )


def test_preflight_rejects_token_reuse(tmp_path):
    token = "same-" + "x" * 32
    with pytest.raises(DeploymentPreflightError, match="must be different"):
        validate_deployment(
            _env(
                tmp_path,
                SARA_RELAY_TOKEN=token,
                SARA_ADMIN_TOKEN=token,
            ),
            expected_head=HEAD,
            required_uid=os.geteuid(),
        )


def test_preflight_rejects_prime_key_not_present_in_trust_set(tmp_path):
    with pytest.raises(DeploymentPreflightError, match="must contain"):
        validate_deployment(
            _env(
                tmp_path,
                PRIME_SENTINEL_PUBLIC_KEYS_JSON=json.dumps(
                    {"DIFFERENT-KEY": "A" * 43}
                ),
            ),
            expected_head=HEAD,
            required_uid=os.geteuid(),
        )


def test_preflight_rejects_insecure_secret_mode(tmp_path):
    path = _env(tmp_path)
    values = path.read_text(encoding="utf-8")
    secret = tmp_path / "prime-token"
    secret.chmod(0o644)

    with pytest.raises(DeploymentPreflightError, match="group/other"):
        validate_deployment(
            path,
            expected_head=HEAD,
            required_uid=os.geteuid(),
        )


def test_preflight_rejects_unsafe_release_identifier(tmp_path):
    with pytest.raises(DeploymentPreflightError, match="safe bounded identifier"):
        validate_deployment(
            _env(tmp_path, SARA_RELEASE_ID="bad;release"),
            expected_head=HEAD,
            required_uid=os.geteuid(),
        )

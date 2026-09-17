from __future__ import annotations

import json

import pytest

from worldshepherd_sara.auth import (
    reject_prime_private_signing_material,
    validate_runtime_secrets,
)


def _base_env() -> dict[str, str]:
    return {
        "SARA_RELAY_TOKEN": "relay-token-0123456789abcdef012345",
        "SARA_ADMIN_TOKEN": "admin-token-0123456789abcdef012345",
    }


@pytest.mark.parametrize(
    "name",
    [
        "PRIME_SENTINEL_PRIVATE_KEY",
        "PRIME_SENTINEL_PRIVATE_KEY_FILE",
        "PRIME_SENTINEL_SIGNING_KEY",
        "PRIME_SENTINEL_SIGNING_KEY_FILE",
        "PRIME_SENTINEL_ED25519_PRIVATE_KEY",
        "PRIME_SENTINEL_ED25519_PRIVATE_KEY_FILE",
        "PRIME_SENTINEL_SECRET_KEY",
        "PRIME_SENTINEL_SEED",
    ],
)
def test_known_prime_private_signing_ingress_names_fail_closed(name):
    env = _base_env()
    env[name] = "non-empty-private-material"

    with pytest.raises(RuntimeError, match="must not receive PRIME SENTINEL private"):
        reject_prime_private_signing_material(env)


@pytest.mark.parametrize(
    "marker",
    [
        "-----BEGIN PRIVATE KEY-----",
        "-----BEGIN OPENSSH PRIVATE KEY-----",
        "-----BEGIN EC PRIVATE KEY-----",
        "-----BEGIN RSA PRIVATE KEY-----",
    ],
)
def test_prime_private_pem_markers_fail_even_under_unexpected_prime_variable(marker):
    env = _base_env()
    env["PRIME_SENTINEL_UNEXPECTED_BLOB"] = marker + "\nabc\n-----END-----"

    with pytest.raises(RuntimeError, match="detected PRIME SENTINEL private key"):
        reject_prime_private_signing_material(env)


def test_public_verification_and_revocation_configuration_remain_allowed():
    env = _base_env()
    env["PRIME_SENTINEL_PUBLIC_KEYS_JSON"] = json.dumps(
        {"PS-K1": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"}
    )
    env["PRIME_SENTINEL_REVOKED_KEY_IDS"] = "PS-OLD"

    reject_prime_private_signing_material(env)


def test_empty_private_key_variables_do_not_create_false_positive():
    env = _base_env()
    env["PRIME_SENTINEL_PRIVATE_KEY"] = ""
    env["PRIME_SENTINEL_SIGNING_KEY_FILE"] = "   "

    reject_prime_private_signing_material(env)


def test_non_prime_private_key_material_is_outside_this_specific_boundary():
    env = _base_env()
    env["ECHO_CHECKPOINT_PRIVATE_KEY_FILE"] = "/run/secrets/echo.pem"

    # G7 isolates PRIME signing material from SARA. It does not redefine the
    # independent ECHO checkpoint-signing design in this gate.
    reject_prime_private_signing_material(env)


def test_validate_runtime_secrets_enforces_prime_signer_isolation(monkeypatch):
    monkeypatch.setenv("SARA_RELAY_TOKEN", _base_env()["SARA_RELAY_TOKEN"])
    monkeypatch.setenv("SARA_ADMIN_TOKEN", _base_env()["SARA_ADMIN_TOKEN"])
    monkeypatch.setenv("PRIME_SENTINEL_PRIVATE_KEY", "must-fail")

    with pytest.raises(RuntimeError, match="must not receive PRIME SENTINEL private"):
        validate_runtime_secrets()

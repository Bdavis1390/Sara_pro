from __future__ import annotations

import os

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from worldshepherd_sara.registry_witness_service import (
    WITNESS_DB_PATH_ENV,
    WITNESS_ID_ENV,
    WITNESS_KEY_FILE_ENV,
    WITNESS_KEY_ID_ENV,
    WITNESS_NAMESPACE_ENV,
    WITNESS_TOKEN_FILE_ENV,
    RegistryWitnessService,
    RegistryWitnessServiceConfigError,
)


TOKEN = "registry-witness-config-token-0123456789abcdef"


def _write_private_key(path):
    private_key = Ed25519PrivateKey.generate()
    path.write_bytes(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    os.chmod(path, 0o600)
    return private_key


def _configure(monkeypatch, tmp_path):
    key_path = tmp_path / "witness-signing.pem"
    token_path = tmp_path / "witness-token"
    _write_private_key(key_path)
    token_path.write_text(TOKEN + "\n", encoding="utf-8")
    os.chmod(token_path, 0o600)

    monkeypatch.setenv(WITNESS_ID_ENV, "WS-CONFIG-TEST")
    monkeypatch.setenv(WITNESS_KEY_ID_ENV, "WS-CONFIG-KEY")
    monkeypatch.setenv(WITNESS_NAMESPACE_ENV, "worldshepherd/sara/config-test")
    monkeypatch.setenv(WITNESS_KEY_FILE_ENV, str(key_path.resolve()))
    monkeypatch.setenv(WITNESS_TOKEN_FILE_ENV, str(token_path.resolve()))
    monkeypatch.setenv(WITNESS_DB_PATH_ENV, str((tmp_path / "witness.db").resolve()))
    monkeypatch.delenv("SARA_ADMIN_TOKEN", raising=False)
    monkeypatch.delenv("SARA_RELAY_TOKEN", raising=False)
    return key_path, token_path


def test_environment_configuration_loads_owned_mode_0600_key_and_token(monkeypatch, tmp_path):
    _configure(monkeypatch, tmp_path)

    service = RegistryWitnessService.from_environment()

    assert service.ledger.witness_id == "WS-CONFIG-TEST"
    assert service.ledger.key_id == "WS-CONFIG-KEY"
    assert service.ledger.namespace == "worldshepherd/sara/config-test"
    assert service.service_token == TOKEN
    assert service.ledger.verify_integrity()["status"] == "PASS"


def test_private_key_symlink_is_rejected(monkeypatch, tmp_path):
    key_path, _token_path = _configure(monkeypatch, tmp_path)
    symlink = tmp_path / "witness-key-link.pem"
    symlink.symlink_to(key_path)
    monkeypatch.setenv(WITNESS_KEY_FILE_ENV, str(symlink.resolve(strict=False)))

    # Path.resolve() follows the symlink, so use the literal absolute symlink
    # path to exercise the no-follow configuration check.
    monkeypatch.setenv(WITNESS_KEY_FILE_ENV, str(symlink.absolute()))
    with pytest.raises(RegistryWitnessServiceConfigError, match="must not be a symbolic link"):
        RegistryWitnessService.from_environment()


def test_group_or_other_readable_secret_is_rejected(monkeypatch, tmp_path):
    _key_path, token_path = _configure(monkeypatch, tmp_path)
    os.chmod(token_path, 0o644)

    with pytest.raises(RegistryWitnessServiceConfigError, match="must not grant group/other permissions"):
        RegistryWitnessService.from_environment()


def test_relative_secret_path_is_rejected(monkeypatch, tmp_path):
    _key_path, _token_path = _configure(monkeypatch, tmp_path)
    monkeypatch.setenv(WITNESS_TOKEN_FILE_ENV, "relative-token")

    with pytest.raises(RegistryWitnessServiceConfigError, match="must be an absolute path"):
        RegistryWitnessService.from_environment()


def test_witness_token_cannot_equal_sara_admin_or_relay_token(monkeypatch, tmp_path):
    _configure(monkeypatch, tmp_path)
    monkeypatch.setenv("SARA_ADMIN_TOKEN", TOKEN)

    with pytest.raises(RegistryWitnessServiceConfigError, match="independent from SARA_ADMIN_TOKEN"):
        RegistryWitnessService.from_environment()

    monkeypatch.delenv("SARA_ADMIN_TOKEN")
    monkeypatch.setenv("SARA_RELAY_TOKEN", TOKEN)
    with pytest.raises(RegistryWitnessServiceConfigError, match="independent from SARA_RELAY_TOKEN"):
        RegistryWitnessService.from_environment()


def test_witness_database_path_must_be_absolute(monkeypatch, tmp_path):
    _configure(monkeypatch, tmp_path)
    monkeypatch.setenv(WITNESS_DB_PATH_ENV, "relative-witness.db")

    with pytest.raises(RegistryWitnessServiceConfigError, match="must be an absolute path"):
        RegistryWitnessService.from_environment()

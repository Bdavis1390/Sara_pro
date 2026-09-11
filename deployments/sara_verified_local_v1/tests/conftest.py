from __future__ import annotations

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient

from worldshepherd_sara.app import app


@pytest.fixture(autouse=True)
def echo_checkpoint_key(monkeypatch: pytest.MonkeyPatch, tmp_path_factory):
    key = Ed25519PrivateKey.generate()
    key_dir = tmp_path_factory.mktemp("echo-checkpoint-key")
    path = key_dir / "echo-checkpoint-ed25519-private.pem"
    path.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    path.chmod(0o600)
    monkeypatch.setenv("ECHO_CHECKPOINT_PRIVATE_KEY_FILE", str(path.resolve()))
    monkeypatch.setenv("ECHO_CHECKPOINT_KEY_ID", "ECHO-CHECKPOINT-PYTEST-V1")
    return key, path


@pytest.fixture()
def tokens(monkeypatch: pytest.MonkeyPatch, tmp_path):
    relay = "relay-token-0123456789abcdef012345"
    admin = "admin-token-0123456789abcdef012345"
    monkeypatch.setenv("SARA_RELAY_TOKEN", relay)
    monkeypatch.setenv("SARA_ADMIN_TOKEN", admin)
    monkeypatch.setenv("SARA_DATA_DIR", str(tmp_path / "data"))
    return relay, admin


@pytest.fixture()
def client(tokens):
    with TestClient(app) as test_client:
        yield test_client

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient

# Deployment tests include a small set of intentional cross-layer parity checks
# against the repository-level security.poo reference implementation. Pytest's
# working directory for the Verified Local gate is this deployment directory,
# so make the checked-out repository root explicit for tests only. The packaged
# worldshepherd_sara runtime does not import or depend on security.poo.
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

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

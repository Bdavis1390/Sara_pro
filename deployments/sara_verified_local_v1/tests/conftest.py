from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from worldshepherd_sara.app import app


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

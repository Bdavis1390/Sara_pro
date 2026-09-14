from __future__ import annotations

import io
import json

from pydantic import SecretStr

from worldshepherd_sara.hmaa_lattice_oauth import (
    SandboxClientCredentialsTokenProvider,
    SandboxOAuthConfig,
)


class FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self._io = io.BytesIO(json.dumps(payload).encode("utf-8"))
        self.headers = {"Content-Type": "application/json"}

    def read(self, limit: int = -1) -> bytes:
        return self._io.read(limit)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_documented_sandboxes_oauth_response_without_token_type_is_accepted():
    """The Sandboxes guide documents access_token/expires_in/scope only."""

    config = SandboxOAuthConfig(
        endpoint="sandbox-123.env.sandboxes.developer.anduril.com",
        client_id="client-id-example",
        client_secret=SecretStr("client-secret-example"),
        sandboxes_token=SecretStr("sandboxes-token-example"),
    )

    response = FakeResponse(
        {
            "access_token": "short-lived-token",
            "expires_in": 1800,
            "scope": "lattice",
        }
    )
    provider = SandboxClientCredentialsTokenProvider(
        config,
        open_request=lambda request, timeout: response,
    )

    token = provider.get_token()
    assert token.get_secret_value() == "short-lived-token"
    diagnostics = provider.diagnostics()
    assert diagnostics.token_type == "Bearer"
    assert diagnostics.cached_token_present is True
    assert diagnostics.persistent_token_storage is False
    assert diagnostics.live_environment_validated is False

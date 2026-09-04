from __future__ import annotations

import io
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs

import pytest
from pydantic import SecretStr

from worldshepherd_sara.hmaa_lattice_oauth import (
    LatticeOAuthError,
    OAUTH_TOKEN_PATH,
    SandboxClientCredentialsTokenProvider,
    SandboxOAuthConfig,
)
from worldshepherd_sara.hmaa_lattice_sandbox import (
    ENTITY_STREAM_PATH,
    EnvironmentTokenProvider,
    SandboxReadConfig,
    SandboxReadOnlySSETransport,
)


CLIENT_ID = "client-id-example"
CLIENT_SECRET = "client&secret=must+encode"
SANDBOXES_TOKEN = "sandbox-token-do-not-leak"
ACCESS_TOKEN = "short-lived-access-token-do-not-leak"
ENDPOINT = "sandbox-123.env.sandboxes.developer.anduril.com"


class FakeResponse:
    def __init__(
        self,
        raw: bytes,
        content_type: str = "application/json",
    ) -> None:
        self._io = io.BytesIO(raw)
        self.headers = {"Content-Type": content_type}
        self.closed = False

    def read(self, limit: int = -1) -> bytes:
        return self._io.read(limit)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.closed = True
        return False


class FakeClock:
    def __init__(self, now: float = 1000.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now


def _config(**overrides) -> SandboxOAuthConfig:
    values = {
        "endpoint": ENDPOINT,
        "client_id": CLIENT_ID,
        "client_secret": SecretStr(CLIENT_SECRET),
        "sandboxes_token": SecretStr(SANDBOXES_TOKEN),
        "timeout_seconds": 5,
        "max_token_response_bytes": 4096,
        "refresh_skew_seconds": 60,
    }
    values.update(overrides)
    return SandboxOAuthConfig(**values)


def _token_response(
    token: str = ACCESS_TOKEN,
    *,
    token_type: str = "Bearer",
    expires_in: object = 1800,
) -> FakeResponse:
    import json

    return FakeResponse(
        json.dumps(
            {
                "access_token": token,
                "token_type": token_type,
                "expires_in": expires_in,
            }
        ).encode("utf-8")
    )


def test_oauth_config_from_env_and_redacted_summary(monkeypatch):
    monkeypatch.setenv("LATTICE_ENDPOINT", ENDPOINT)
    monkeypatch.setenv("LATTICE_CLIENT_ID", CLIENT_ID)
    monkeypatch.setenv("LATTICE_CLIENT_SECRET", CLIENT_SECRET)
    monkeypatch.setenv("SANDBOXES_TOKEN", SANDBOXES_TOKEN)

    config = SandboxOAuthConfig.from_env()
    summary = config.redacted_summary()

    assert config.endpoint == f"https://{ENDPOINT}"
    assert config.client_secret.get_secret_value() == CLIENT_SECRET
    assert summary["client_id_present"] is True
    assert summary["client_secret_present"] is True
    assert summary["sandboxes_token_present"] is True
    assert summary["persistent_token_storage"] is False
    assert summary["live_environment_validated"] is False
    assert CLIENT_SECRET not in repr(config)
    assert CLIENT_SECRET not in repr(summary)
    assert SANDBOXES_TOKEN not in repr(summary)


def test_oauth_config_from_env_reports_missing_names_not_values(monkeypatch):
    monkeypatch.setenv("LATTICE_ENDPOINT", ENDPOINT)
    monkeypatch.delenv("LATTICE_CLIENT_ID", raising=False)
    monkeypatch.delenv("LATTICE_CLIENT_SECRET", raising=False)
    monkeypatch.setenv("SANDBOXES_TOKEN", SANDBOXES_TOKEN)

    with pytest.raises(ValueError) as exc_info:
        SandboxOAuthConfig.from_env()

    message = str(exc_info.value)
    assert "LATTICE_CLIENT_ID" in message
    assert "LATTICE_CLIENT_SECRET" in message
    assert SANDBOXES_TOKEN not in message


@pytest.mark.parametrize(
    "endpoint",
    [
        "http://sandbox-123.env.sandboxes.developer.anduril.com",
        "https://example.com",
        "https://user:pass@sandbox-123.env.sandboxes.developer.anduril.com",
        "https://sandbox-123.env.sandboxes.developer.anduril.com/api/v1/oauth/token",
        "https://sandbox-123.env.sandboxes.developer.anduril.com?x=1",
        "https://nested.sandbox-123.env.sandboxes.developer.anduril.com",
    ],
)
def test_oauth_endpoint_rejects_unsafe_or_non_sandbox_hosts(endpoint):
    with pytest.raises(ValueError):
        _config(endpoint=endpoint)


def test_token_request_matches_public_client_credentials_contract_and_url_encodes_secret():
    captured = {}

    def open_request(request, timeout):
        captured["request"] = request
        captured["timeout"] = timeout
        return _token_response()

    provider = SandboxClientCredentialsTokenProvider(
        _config(), open_request=open_request, clock=FakeClock()
    )
    token = provider.get_token()

    request = captured["request"]
    headers = {key.lower(): value for key, value in request.header_items()}
    form = parse_qs(request.data.decode("utf-8"), keep_blank_values=True)

    assert request.full_url == f"https://{ENDPOINT}{OAUTH_TOKEN_PATH}"
    assert request.method == "POST"
    assert captured["timeout"] == 5
    assert headers["content-type"] == "application/x-www-form-urlencoded"
    assert headers["accept"] == "application/json"
    assert headers["anduril-sandbox-authorization"] == f"Bearer {SANDBOXES_TOKEN}"
    assert form == {
        "grant_type": ["client_credentials"],
        "client_id": [CLIENT_ID],
        "client_secret": [CLIENT_SECRET],
    }
    assert token.get_secret_value() == ACCESS_TOKEN


def test_token_provider_is_protocol_compatible_and_secret_safe():
    provider = SandboxClientCredentialsTokenProvider(
        _config(), open_request=lambda request, timeout: _token_response()
    )
    assert isinstance(provider, EnvironmentTokenProvider)
    rendered = repr(provider)
    assert "storage=memory-only" in rendered
    assert CLIENT_SECRET not in rendered
    assert SANDBOXES_TOKEN not in rendered
    assert ACCESS_TOKEN not in rendered


def test_token_is_cached_and_refreshed_before_expiry():
    clock = FakeClock()
    calls = []

    def open_request(request, timeout):
        calls.append(len(calls) + 1)
        return _token_response(token=f"token-{len(calls)}", expires_in=1800)

    provider = SandboxClientCredentialsTokenProvider(
        _config(refresh_skew_seconds=60),
        open_request=open_request,
        clock=clock,
    )

    assert provider.get_token().get_secret_value() == "token-1"
    assert provider.get_token().get_secret_value() == "token-1"
    assert len(calls) == 1

    clock.now += 1739
    assert provider.get_token().get_secret_value() == "token-1"
    assert len(calls) == 1

    clock.now += 2
    assert provider.get_token().get_secret_value() == "token-2"
    assert len(calls) == 2

    diagnostics = provider.diagnostics()
    assert diagnostics.cached_token_present is True
    assert diagnostics.persistent_token_storage is False
    assert ACCESS_TOKEN not in repr(diagnostics)


def test_clear_forces_fresh_acquisition():
    calls = []

    def open_request(request, timeout):
        calls.append(1)
        return _token_response(token=f"token-{len(calls)}")

    provider = SandboxClientCredentialsTokenProvider(
        _config(), open_request=open_request, clock=FakeClock()
    )
    assert provider.get_token().get_secret_value() == "token-1"
    provider.clear()
    assert provider.diagnostics().cached_token_present is False
    assert provider.get_token().get_secret_value() == "token-2"
    assert len(calls) == 2


def test_missing_or_invalid_expiry_fails_closed():
    import json

    invalid_payloads = [
        {"access_token": ACCESS_TOKEN, "token_type": "Bearer"},
        {"access_token": ACCESS_TOKEN, "token_type": "Bearer", "expires_in": 0},
        {"access_token": ACCESS_TOKEN, "token_type": "Bearer", "expires_in": -1},
        {"access_token": ACCESS_TOKEN, "token_type": "Bearer", "expires_in": True},
        {"access_token": ACCESS_TOKEN, "token_type": "Bearer", "expires_in": "1800"},
    ]

    for payload in invalid_payloads:
        provider = SandboxClientCredentialsTokenProvider(
            _config(),
            open_request=lambda request, timeout, payload=payload: FakeResponse(
                json.dumps(payload).encode("utf-8")
            ),
        )
        with pytest.raises(LatticeOAuthError, match="expires_in"):
            provider.get_token()


def test_missing_access_token_and_non_bearer_type_are_rejected_without_leakage():
    import json

    missing = SandboxClientCredentialsTokenProvider(
        _config(),
        open_request=lambda request, timeout: FakeResponse(
            json.dumps({"token_type": "Bearer", "expires_in": 1800}).encode()
        ),
    )
    with pytest.raises(LatticeOAuthError, match="access_token"):
        missing.get_token()

    wrong_type = SandboxClientCredentialsTokenProvider(
        _config(),
        open_request=lambda request, timeout: _token_response(token_type="MAC"),
    )
    with pytest.raises(LatticeOAuthError, match="Bearer") as exc_info:
        wrong_type.get_token()
    assert ACCESS_TOKEN not in str(exc_info.value)


def test_malformed_oversized_and_wrong_content_type_responses_are_rejected():
    malformed = SandboxClientCredentialsTokenProvider(
        _config(),
        open_request=lambda request, timeout: FakeResponse(b"not-json"),
    )
    with pytest.raises(LatticeOAuthError, match="UTF-8 JSON"):
        malformed.get_token()

    oversized = SandboxClientCredentialsTokenProvider(
        _config(max_token_response_bytes=1024),
        open_request=lambda request, timeout: FakeResponse(b"x" * 1025),
    )
    with pytest.raises(LatticeOAuthError, match="size limit"):
        oversized.get_token()

    wrong_content = SandboxClientCredentialsTokenProvider(
        _config(),
        open_request=lambda request, timeout: FakeResponse(
            b"{}", content_type="text/plain"
        ),
    )
    with pytest.raises(LatticeOAuthError, match="content type"):
        wrong_content.get_token()


def test_network_http_and_redirect_errors_are_sanitized():
    def network_failure(request, timeout):
        raise URLError(f"failure containing {CLIENT_SECRET} {SANDBOXES_TOKEN}")

    network = SandboxClientCredentialsTokenProvider(
        _config(), open_request=network_failure
    )
    with pytest.raises(LatticeOAuthError) as exc_info:
        network.get_token()
    message = str(exc_info.value)
    assert CLIENT_SECRET not in message
    assert SANDBOXES_TOKEN not in message

    def redirect(request, timeout):
        raise HTTPError(request.full_url, 302, "Found", {}, None)

    redirected = SandboxClientCredentialsTokenProvider(
        _config(), open_request=redirect
    )
    with pytest.raises(LatticeOAuthError, match="redirect blocked"):
        redirected.get_token()

    def unauthorized(request, timeout):
        raise HTTPError(request.full_url, 401, ACCESS_TOKEN, {}, None)

    unauthorized_provider = SandboxClientCredentialsTokenProvider(
        _config(), open_request=unauthorized
    )
    with pytest.raises(LatticeOAuthError, match="HTTP 401") as exc_info:
        unauthorized_provider.get_token()
    assert ACCESS_TOKEN not in str(exc_info.value)


def test_oauth_provider_writes_no_token_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    provider = SandboxClientCredentialsTokenProvider(
        _config(),
        open_request=lambda request, timeout: _token_response(),
        clock=FakeClock(),
    )
    assert provider.get_token().get_secret_value() == ACCESS_TOKEN
    assert provider.diagnostics().cached_token_present is True
    assert list(tmp_path.iterdir()) == []


def test_read_transport_uses_provider_token_without_persisting_it():
    provider = SandboxClientCredentialsTokenProvider(
        _config(),
        open_request=lambda request, timeout: _token_response(),
        clock=FakeClock(),
    )
    read_config = SandboxReadConfig(
        endpoint=ENDPOINT,
        environment_token=None,
        sandboxes_token=SecretStr(SANDBOXES_TOKEN),
    )
    transport = SandboxReadOnlySSETransport(
        read_config,
        environment_token_provider=provider,
        open_request=lambda request, timeout: None,
    )

    request = transport._build_stream_request(ENTITY_STREAM_PATH, {})
    headers = {key.lower(): value for key, value in request.header_items()}
    assert headers["authorization"] == f"Bearer {ACCESS_TOKEN}"
    assert headers["anduril-sandbox-authorization"] == f"Bearer {SANDBOXES_TOKEN}"
    assert ACCESS_TOKEN not in repr(transport)
    assert CLIENT_SECRET not in repr(transport)


def test_transport_requires_static_token_or_provider():
    read_config = SandboxReadConfig(
        endpoint=ENDPOINT,
        environment_token=None,
        sandboxes_token=SecretStr(SANDBOXES_TOKEN),
    )
    with pytest.raises(ValueError, match="static environment token or token provider"):
        SandboxReadOnlySSETransport(read_config)

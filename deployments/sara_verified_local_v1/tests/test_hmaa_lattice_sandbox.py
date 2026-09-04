from __future__ import annotations

import io
from urllib.error import HTTPError, URLError

import pytest
from pydantic import SecretStr

from worldshepherd_sara.hmaa_lattice_contract import LatticeReadTransport
from worldshepherd_sara.hmaa_lattice_sandbox import (
    ENTITY_STREAM_PATH,
    TASK_STREAM_PATH,
    LatticeSandboxReadError,
    SandboxReadConfig,
    SandboxReadOnlySSETransport,
    sandbox_readiness_report,
)


ENVIRONMENT_TOKEN = "environment-token-do-not-leak"
SANDBOXES_TOKEN = "sandboxes-token-do-not-leak"


def _config() -> SandboxReadConfig:
    return SandboxReadConfig(
        endpoint="sandbox-123.env.sandboxes.developer.anduril.com",
        environment_token=SecretStr(ENVIRONMENT_TOKEN),
        sandboxes_token=SecretStr(SANDBOXES_TOKEN),
        timeout_seconds=5,
        max_sse_event_bytes=4096,
    )


class FakeResponse:
    def __init__(self, raw: bytes, content_type: str = "text/event-stream") -> None:
        self._io = io.BytesIO(raw)
        self.headers = {"Content-Type": content_type}
        self.closed = False

    def readline(self, limit: int = -1) -> bytes:
        return self._io.readline(limit)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.closed = True
        return False


def test_config_normalizes_hostname_and_redacts_secrets():
    config = _config()
    assert config.endpoint == "https://sandbox-123.env.sandboxes.developer.anduril.com"
    assert ENVIRONMENT_TOKEN not in repr(config)
    assert SANDBOXES_TOKEN not in repr(config)

    summary = config.redacted_summary()
    assert summary["environment_token_present"] is True
    assert summary["sandboxes_token_present"] is True
    assert ENVIRONMENT_TOKEN not in repr(summary)
    assert SANDBOXES_TOKEN not in repr(summary)
    assert summary["live_environment_validated"] is False


def test_config_from_env_uses_only_named_runtime_secrets(monkeypatch):
    monkeypatch.setenv("LATTICE_ENDPOINT", "sandbox.env.sandboxes.developer.anduril.com")
    monkeypatch.setenv("ENVIRONMENT_TOKEN", ENVIRONMENT_TOKEN)
    monkeypatch.setenv("SANDBOXES_TOKEN", SANDBOXES_TOKEN)

    config = SandboxReadConfig.from_env()
    assert config.endpoint == "https://sandbox.env.sandboxes.developer.anduril.com"
    assert config.environment_token.get_secret_value() == ENVIRONMENT_TOKEN
    assert config.sandboxes_token.get_secret_value() == SANDBOXES_TOKEN


def test_config_from_env_reports_missing_variable_names_only(monkeypatch):
    monkeypatch.delenv("LATTICE_ENDPOINT", raising=False)
    monkeypatch.delenv("ENVIRONMENT_TOKEN", raising=False)
    monkeypatch.setenv("SANDBOXES_TOKEN", SANDBOXES_TOKEN)

    with pytest.raises(ValueError) as exc_info:
        SandboxReadConfig.from_env()

    message = str(exc_info.value)
    assert "LATTICE_ENDPOINT" in message
    assert "ENVIRONMENT_TOKEN" in message
    assert SANDBOXES_TOKEN not in message


@pytest.mark.parametrize(
    "endpoint",
    [
        "http://sandbox.example",
        "https://user:pass@sandbox.example",
        "https://sandbox.example/api/v1/entities/stream",
        "https://sandbox.example?token=bad",
        "https://sandbox.example:8443",
    ],
)
def test_endpoint_validation_rejects_unsafe_shapes(endpoint):
    with pytest.raises(ValueError):
        SandboxReadConfig(
            endpoint=endpoint,
            environment_token=SecretStr("x"),
            sandboxes_token=SecretStr("y"),
        )


def test_readiness_report_never_claims_live_validation():
    report = sandbox_readiness_report(_config())
    assert report.ready_for_authorized_read_test is True
    assert report.live_environment_validated is False
    assert report.allowed_paths == [ENTITY_STREAM_PATH, TASK_STREAM_PATH]
    assert "no_write_or_control_methods" in report.controls


def test_transport_is_protocol_compatible_and_has_no_write_methods():
    transport = SandboxReadOnlySSETransport(_config(), open_request=lambda r, t: None)
    assert isinstance(transport, LatticeReadTransport)
    assert not hasattr(transport, "publish_entity")
    assert not hasattr(transport, "create_task")
    assert not hasattr(transport, "update_task")
    assert not hasattr(transport, "manual_control")


def test_transport_builds_only_allowlisted_stream_requests_with_required_headers():
    transport = SandboxReadOnlySSETransport(_config(), open_request=lambda r, t: None)
    request = transport._build_stream_request(
        ENTITY_STREAM_PATH,
        {"preExistingOnly": True},
    )
    headers = {key.lower(): value for key, value in request.header_items()}

    assert request.full_url.endswith(ENTITY_STREAM_PATH)
    assert request.method == "POST"
    assert headers["authorization"] == f"Bearer {ENVIRONMENT_TOKEN}"
    assert headers["anduril-sandbox-authorization"] == f"Bearer {SANDBOXES_TOKEN}"
    assert headers["accept"] == "text/event-stream"

    with pytest.raises(ValueError, match="allowlist"):
        transport._build_stream_request("/api/v1/entities", {})


def test_entity_sse_stream_yields_json_objects_and_closes_response():
    raw = (
        b": keepalive\n"
        b"data: {\"heartbeat\":{\"timestamp\":\"2026-09-04T22:40:00Z\"}}\n\n"
        b"event: ignored-name\n"
        b"data: {\"entity\":{\"eventType\":\"UPDATE\",\"entity\":{\"entityId\":\"E-1\",\"timestamp\":\"2026-09-04T22:40:01Z\"}}}\n\n"
    )
    response = FakeResponse(raw)
    captured_request = {}

    def open_request(request, timeout):
        captured_request["request"] = request
        captured_request["timeout"] = timeout
        return response

    transport = SandboxReadOnlySSETransport(_config(), open_request=open_request)
    messages = list(transport.stream_entities({"heartbeatIntervalMS": 30000}))

    assert len(messages) == 2
    assert "heartbeat" in messages[0]
    assert "entity" in messages[1]
    assert response.closed is True
    assert captured_request["timeout"] == 5


def test_stream_rejects_unexpected_content_type_without_exposing_tokens():
    response = FakeResponse(b"{}", content_type="application/json")
    transport = SandboxReadOnlySSETransport(
        _config(), open_request=lambda request, timeout: response
    )

    with pytest.raises(LatticeSandboxReadError) as exc_info:
        list(transport.stream_tasks({"rateLimit": 250}))

    message = str(exc_info.value)
    assert "unexpected content type" in message
    assert ENVIRONMENT_TOKEN not in message
    assert SANDBOXES_TOKEN not in message


def test_stream_sanitizes_network_errors_and_redirects():
    def network_failure(request, timeout):
        raise URLError(f"network problem containing {ENVIRONMENT_TOKEN}")

    transport = SandboxReadOnlySSETransport(_config(), open_request=network_failure)
    with pytest.raises(LatticeSandboxReadError) as exc_info:
        list(transport.stream_entities({}))
    assert ENVIRONMENT_TOKEN not in str(exc_info.value)

    def redirect(request, timeout):
        raise HTTPError(request.full_url, 302, "Found", {}, None)

    redirect_transport = SandboxReadOnlySSETransport(_config(), open_request=redirect)
    with pytest.raises(LatticeSandboxReadError, match="redirect blocked"):
        list(redirect_transport.stream_entities({}))


def test_stream_rejects_oversized_or_invalid_sse_data():
    oversized = FakeResponse(b"data: " + (b"x" * 5000) + b"\n\n")
    transport = SandboxReadOnlySSETransport(
        _config(), open_request=lambda request, timeout: oversized
    )
    with pytest.raises(LatticeSandboxReadError, match="size limit"):
        list(transport.stream_entities({}))

    invalid = FakeResponse(b"data: not-json\n\n")
    invalid_transport = SandboxReadOnlySSETransport(
        _config(), open_request=lambda request, timeout: invalid
    )
    with pytest.raises(LatticeSandboxReadError, match="invalid JSON"):
        list(invalid_transport.stream_entities({}))


def test_transport_repr_is_secret_safe():
    transport = SandboxReadOnlySSETransport(_config())
    rendered = repr(transport)
    assert "credentials=<redacted>" in rendered
    assert ENVIRONMENT_TOKEN not in rendered
    assert SANDBOXES_TOKEN not in rendered

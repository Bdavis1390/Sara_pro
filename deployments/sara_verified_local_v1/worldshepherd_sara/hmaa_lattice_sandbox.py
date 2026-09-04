from __future__ import annotations

import json
import os
from collections.abc import Callable, Iterable, Iterator, Mapping
from typing import Any, Protocol, runtime_checkable
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from pydantic import BaseModel, Field, SecretStr, field_validator

from .hmaa_lattice_contract import (
    LatticeReadTransport,
    validate_entity_stream_request,
    validate_task_stream_request,
)


ENTITY_STREAM_PATH = "/api/v1/entities/stream"
TASK_STREAM_PATH = "/api/v1/tasks/stream"
ALLOWED_READ_STREAM_PATHS = frozenset({ENTITY_STREAM_PATH, TASK_STREAM_PATH})
SANDBOX_HOST_SUFFIX = ".env.sandboxes.developer.anduril.com"


class LatticeSandboxReadError(RuntimeError):
    """Sanitized read-only Sandbox transport error."""


@runtime_checkable
class EnvironmentTokenProvider(Protocol):
    def get_token(self) -> SecretStr: ...


class SandboxReadConfig(BaseModel):
    endpoint: str = Field(min_length=1)
    environment_token: SecretStr | None = None
    sandboxes_token: SecretStr
    timeout_seconds: float = Field(default=30.0, gt=0, le=300)
    max_sse_event_bytes: int = Field(default=1_048_576, ge=1024, le=8_388_608)

    @field_validator("endpoint")
    @classmethod
    def validate_endpoint(cls, value: str) -> str:
        raw = value.strip()
        if not raw:
            raise ValueError("LATTICE_ENDPOINT must not be empty")
        candidate = raw if "://" in raw else f"https://{raw}"
        parsed = urlsplit(candidate)
        if parsed.scheme.lower() != "https":
            raise ValueError("LATTICE_ENDPOINT must use HTTPS")
        if not parsed.hostname:
            raise ValueError("LATTICE_ENDPOINT must include a hostname")
        if parsed.username or parsed.password:
            raise ValueError("LATTICE_ENDPOINT must not contain user information")
        if parsed.path not in ("", "/") or parsed.query or parsed.fragment:
            raise ValueError("LATTICE_ENDPOINT must be a host endpoint without path/query/fragment")
        if parsed.port not in (None, 443):
            raise ValueError("LATTICE_ENDPOINT may only use the default HTTPS port")
        hostname = parsed.hostname.lower()
        if not hostname.endswith(SANDBOX_HOST_SUFFIX):
            raise ValueError(
                "LATTICE_ENDPOINT must be a documented Lattice Sandboxes environment host"
            )
        environment_id = hostname[: -len(SANDBOX_HOST_SUFFIX)]
        if not environment_id or "." in environment_id:
            raise ValueError("LATTICE_ENDPOINT Sandbox environment identifier is invalid")
        return f"https://{hostname}"

    @classmethod
    def from_env(cls) -> "SandboxReadConfig":
        required = {
            "LATTICE_ENDPOINT": os.getenv("LATTICE_ENDPOINT"),
            "ENVIRONMENT_TOKEN": os.getenv("ENVIRONMENT_TOKEN"),
            "SANDBOXES_TOKEN": os.getenv("SANDBOXES_TOKEN"),
        }
        missing = sorted(name for name, value in required.items() if not value)
        if missing:
            raise ValueError(
                "missing required Sandbox read environment variables: "
                + ", ".join(missing)
            )
        return cls(
            endpoint=required["LATTICE_ENDPOINT"],
            environment_token=SecretStr(required["ENVIRONMENT_TOKEN"] or ""),
            sandboxes_token=SecretStr(required["SANDBOXES_TOKEN"] or ""),
        )

    def redacted_summary(self) -> dict[str, Any]:
        return {
            "endpoint": self.endpoint,
            "environment_token_present": bool(
                self.environment_token
                and self.environment_token.get_secret_value()
            ),
            "sandboxes_token_present": bool(self.sandboxes_token.get_secret_value()),
            "timeout_seconds": self.timeout_seconds,
            "max_sse_event_bytes": self.max_sse_event_bytes,
            "allowed_paths": sorted(ALLOWED_READ_STREAM_PATHS),
            "live_environment_validated": False,
        }


class SandboxReadinessReport(BaseModel):
    ready_for_authorized_read_test: bool
    live_environment_validated: bool = False
    endpoint: str
    allowed_paths: list[str]
    credential_presence: dict[str, bool]
    controls: list[str]


def sandbox_readiness_report(config: SandboxReadConfig) -> SandboxReadinessReport:
    summary = config.redacted_summary()
    credential_presence = {
        "environment_token": bool(summary["environment_token_present"]),
        "sandboxes_token": bool(summary["sandboxes_token_present"]),
    }
    return SandboxReadinessReport(
        ready_for_authorized_read_test=all(credential_presence.values()),
        live_environment_validated=False,
        endpoint=config.endpoint,
        allowed_paths=sorted(ALLOWED_READ_STREAM_PATHS),
        credential_presence=credential_presence,
        controls=[
            "https_only_endpoint",
            "official_sandbox_host_suffix",
            "exact_read_endpoint_allowlist",
            "redirects_blocked",
            "bounded_sse_event_size",
            "secret_redacted_diagnostics",
            "no_write_or_control_methods",
        ],
    )


class _NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[override]
        raise HTTPError(req.full_url, code, "redirect blocked", headers, fp)


OpenCallable = Callable[[Request, float], Any]


def _default_open(request: Request, timeout: float) -> Any:
    opener = build_opener(_NoRedirectHandler())
    return opener.open(request, timeout=timeout)


class SandboxReadOnlySSETransport(LatticeReadTransport):
    """Read-only REST SSE transport for an authorized Lattice Sandbox.

    Construction does not perform a network call. Only the two documented
    stream endpoints are reachable through public methods. The environment
    bearer can be static or supplied on demand by an in-memory token provider.
    """

    def __init__(
        self,
        config: SandboxReadConfig,
        *,
        environment_token_provider: EnvironmentTokenProvider | None = None,
        open_request: OpenCallable | None = None,
    ) -> None:
        if environment_token_provider is None and not (
            config.environment_token
            and config.environment_token.get_secret_value()
        ):
            raise ValueError(
                "Sandbox read transport requires a static environment token or token provider"
            )
        self._config = config
        self._environment_token_provider = environment_token_provider
        self._open_request = open_request or _default_open

    def __repr__(self) -> str:
        mode = "provider" if self._environment_token_provider else "static"
        return (
            "SandboxReadOnlySSETransport("
            f"endpoint={self._config.endpoint!r}, token_mode={mode!r}, "
            "credentials=<redacted>)"
        )

    def _environment_token_value(self) -> str:
        if self._environment_token_provider is not None:
            token = self._environment_token_provider.get_token()
            value = token.get_secret_value()
            if not value:
                raise LatticeSandboxReadError(
                    "environment token provider returned an unusable token"
                )
            return value
        if self._config.environment_token is None:
            raise LatticeSandboxReadError("environment token is unavailable")
        value = self._config.environment_token.get_secret_value()
        if not value:
            raise LatticeSandboxReadError("environment token is unavailable")
        return value

    def _build_stream_request(
        self,
        path: str,
        payload: Mapping[str, Any],
    ) -> Request:
        if path not in ALLOWED_READ_STREAM_PATHS:
            raise ValueError("path is not in the WS-HMAA read-only endpoint allowlist")
        body = json.dumps(
            dict(payload),
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return Request(
            url=self._config.endpoint + path,
            data=body,
            method="POST",
            headers={
                "Authorization": "Bearer " + self._environment_token_value(),
                "Anduril-Sandbox-Authorization": (
                    "Bearer " + self._config.sandboxes_token.get_secret_value()
                ),
                "Content-Type": "application/json",
                "Accept": "text/event-stream",
            },
        )

    def _stream(
        self,
        path: str,
        payload: Mapping[str, Any],
    ) -> Iterator[Mapping[str, Any]]:
        request = self._build_stream_request(path, payload)
        try:
            response = self._open_request(request, self._config.timeout_seconds)
            with response:
                content_type = str(response.headers.get("Content-Type", ""))
                if "text/event-stream" not in content_type.lower():
                    raise LatticeSandboxReadError(
                        "Sandbox stream returned an unexpected content type"
                    )
                yield from self._iter_sse(response)
        except LatticeSandboxReadError:
            raise
        except HTTPError as exc:
            if 300 <= exc.code < 400:
                raise LatticeSandboxReadError(
                    f"Sandbox stream redirect blocked (HTTP {exc.code})"
                ) from None
            raise LatticeSandboxReadError(
                f"Sandbox stream request failed (HTTP {exc.code})"
            ) from None
        except (URLError, TimeoutError, OSError) as exc:
            raise LatticeSandboxReadError(
                f"Sandbox stream connection failed ({type(exc).__name__})"
            ) from None

    def _iter_sse(self, response: Any) -> Iterator[Mapping[str, Any]]:
        data_lines: list[str] = []
        event_bytes = 0

        def emit() -> Mapping[str, Any] | None:
            nonlocal data_lines, event_bytes
            if not data_lines:
                event_bytes = 0
                return None
            raw_data = "\n".join(data_lines)
            data_lines = []
            event_bytes = 0
            try:
                value = json.loads(raw_data)
            except json.JSONDecodeError as exc:
                raise LatticeSandboxReadError(
                    "Sandbox SSE event contained invalid JSON"
                ) from exc
            if not isinstance(value, Mapping):
                raise LatticeSandboxReadError(
                    "Sandbox SSE event JSON must be an object"
                )
            return value

        while True:
            raw = response.readline(self._config.max_sse_event_bytes + 1)
            if not raw:
                final = emit()
                if final is not None:
                    yield final
                break
            if len(raw) > self._config.max_sse_event_bytes:
                raise LatticeSandboxReadError("Sandbox SSE line exceeded size limit")
            event_bytes += len(raw)
            if event_bytes > self._config.max_sse_event_bytes:
                raise LatticeSandboxReadError("Sandbox SSE event exceeded size limit")
            try:
                line = raw.decode("utf-8").rstrip("\r\n")
            except UnicodeDecodeError as exc:
                raise LatticeSandboxReadError(
                    "Sandbox SSE stream contained invalid UTF-8"
                ) from exc

            if line == "":
                event = emit()
                if event is not None:
                    yield event
                continue
            if line.startswith(":"):
                continue
            if line.startswith("data:"):
                data_lines.append(line[5:].lstrip(" "))

    def stream_entities(
        self, request: Mapping[str, Any]
    ) -> Iterable[Mapping[str, Any]]:
        validated = validate_entity_stream_request(request)
        return self._stream(ENTITY_STREAM_PATH, validated)

    def stream_tasks(
        self, request: Mapping[str, Any]
    ) -> Iterable[Mapping[str, Any]]:
        validated = validate_task_stream_request(request)
        return self._stream(TASK_STREAM_PATH, validated)

from __future__ import annotations

import json
import os
import threading
import time
from collections.abc import Callable
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from pydantic import BaseModel, Field, SecretStr, field_validator


OAUTH_TOKEN_PATH = "/api/v1/oauth/token"
SANDBOX_HOST_SUFFIX = ".env.sandboxes.developer.anduril.com"


class LatticeOAuthError(RuntimeError):
    """Sanitized OAuth client-credentials error."""


class SandboxOAuthConfig(BaseModel):
    endpoint: str = Field(min_length=1)
    client_id: str = Field(min_length=1)
    client_secret: SecretStr
    sandboxes_token: SecretStr
    timeout_seconds: float = Field(default=15.0, gt=0, le=120)
    max_token_response_bytes: int = Field(default=65_536, ge=1024, le=1_048_576)
    refresh_skew_seconds: float = Field(default=60.0, ge=0, le=600)

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

    @field_validator("client_id")
    @classmethod
    def validate_client_id(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("LATTICE_CLIENT_ID must not be empty")
        return normalized

    @classmethod
    def from_env(cls) -> "SandboxOAuthConfig":
        required = {
            "LATTICE_ENDPOINT": os.getenv("LATTICE_ENDPOINT"),
            "LATTICE_CLIENT_ID": os.getenv("LATTICE_CLIENT_ID"),
            "LATTICE_CLIENT_SECRET": os.getenv("LATTICE_CLIENT_SECRET"),
            "SANDBOXES_TOKEN": os.getenv("SANDBOXES_TOKEN"),
        }
        missing = sorted(name for name, value in required.items() if not value)
        if missing:
            raise ValueError(
                "missing required Sandbox OAuth environment variables: "
                + ", ".join(missing)
            )
        return cls(
            endpoint=required["LATTICE_ENDPOINT"] or "",
            client_id=required["LATTICE_CLIENT_ID"] or "",
            client_secret=SecretStr(required["LATTICE_CLIENT_SECRET"] or ""),
            sandboxes_token=SecretStr(required["SANDBOXES_TOKEN"] or ""),
        )

    def redacted_summary(self) -> dict[str, Any]:
        return {
            "endpoint": self.endpoint,
            "client_id_present": bool(self.client_id),
            "client_secret_present": bool(self.client_secret.get_secret_value()),
            "sandboxes_token_present": bool(self.sandboxes_token.get_secret_value()),
            "token_path": OAUTH_TOKEN_PATH,
            "timeout_seconds": self.timeout_seconds,
            "max_token_response_bytes": self.max_token_response_bytes,
            "refresh_skew_seconds": self.refresh_skew_seconds,
            "persistent_token_storage": False,
            "live_environment_validated": False,
        }


class OAuthTokenResponse(BaseModel):
    access_token: SecretStr
    token_type: str = "Bearer"
    expires_in: int = Field(gt=0)


class OAuthTokenDiagnostics(BaseModel):
    cached_token_present: bool
    token_type: str | None = None
    seconds_until_expiry: float | None = None
    refresh_due: bool = True
    persistent_token_storage: bool = False
    live_environment_validated: bool = False


class _NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[override]
        raise HTTPError(req.full_url, code, "redirect blocked", headers, fp)


OpenCallable = Callable[[Request, float], Any]
ClockCallable = Callable[[], float]


def _default_open(request: Request, timeout: float) -> Any:
    opener = build_opener(_NoRedirectHandler())
    return opener.open(request, timeout=timeout)


class SandboxClientCredentialsTokenProvider:
    """Acquire and cache short-lived Lattice bearer tokens in memory only."""

    def __init__(
        self,
        config: SandboxOAuthConfig,
        *,
        open_request: OpenCallable | None = None,
        clock: ClockCallable | None = None,
    ) -> None:
        self._config = config
        self._open_request = open_request or _default_open
        self._clock = clock or time.monotonic
        self._lock = threading.RLock()
        self._cached: OAuthTokenResponse | None = None
        self._refresh_at: float | None = None
        self._expires_at: float | None = None

    def __repr__(self) -> str:
        return (
            "SandboxClientCredentialsTokenProvider("
            f"endpoint={self._config.endpoint!r}, credentials=<redacted>, "
            "storage=memory-only)"
        )

    def _build_token_request(self) -> Request:
        body = urlencode(
            {
                "grant_type": "client_credentials",
                "client_id": self._config.client_id,
                "client_secret": self._config.client_secret.get_secret_value(),
            }
        ).encode("utf-8")
        return Request(
            url=self._config.endpoint + OAUTH_TOKEN_PATH,
            data=body,
            method="POST",
            headers={
                "Anduril-Sandbox-Authorization": (
                    "Bearer " + self._config.sandboxes_token.get_secret_value()
                ),
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
        )

    def _acquire(self) -> OAuthTokenResponse:
        request = self._build_token_request()
        try:
            response = self._open_request(request, self._config.timeout_seconds)
            with response:
                content_type = str(response.headers.get("Content-Type", ""))
                if "application/json" not in content_type.lower():
                    raise LatticeOAuthError(
                        "Sandbox OAuth endpoint returned an unexpected content type"
                    )
                raw = response.read(self._config.max_token_response_bytes + 1)
                if len(raw) > self._config.max_token_response_bytes:
                    raise LatticeOAuthError(
                        "Sandbox OAuth response exceeded the configured size limit"
                    )
        except LatticeOAuthError:
            raise
        except HTTPError as exc:
            if 300 <= exc.code < 400:
                raise LatticeOAuthError(
                    f"Sandbox OAuth redirect blocked (HTTP {exc.code})"
                ) from None
            raise LatticeOAuthError(
                f"Sandbox OAuth request failed (HTTP {exc.code})"
            ) from None
        except (URLError, TimeoutError, OSError) as exc:
            raise LatticeOAuthError(
                f"Sandbox OAuth connection failed ({type(exc).__name__})"
            ) from None

        try:
            decoded = raw.decode("utf-8")
            payload = json.loads(decoded)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise LatticeOAuthError(
                "Sandbox OAuth response was not valid UTF-8 JSON"
            ) from exc
        if not isinstance(payload, dict):
            raise LatticeOAuthError("Sandbox OAuth response JSON must be an object")

        access_token = payload.get("access_token")
        if not isinstance(access_token, str) or not access_token.strip():
            raise LatticeOAuthError(
                "Sandbox OAuth response did not contain a usable access_token"
            )

        token_type = payload.get("token_type")
        if not isinstance(token_type, str) or token_type.lower() != "bearer":
            raise LatticeOAuthError(
                "Sandbox OAuth response token_type must be Bearer"
            )

        expires_in = payload.get("expires_in")
        if isinstance(expires_in, bool) or not isinstance(expires_in, int) or expires_in <= 0:
            raise LatticeOAuthError(
                "Sandbox OAuth response expires_in must be a positive integer"
            )

        return OAuthTokenResponse(
            access_token=SecretStr(access_token),
            token_type="Bearer",
            expires_in=expires_in,
        )

    def get_token(self) -> SecretStr:
        with self._lock:
            now = self._clock()
            if (
                self._cached is not None
                and self._refresh_at is not None
                and now < self._refresh_at
            ):
                return self._cached.access_token

            token = self._acquire()
            acquired_at = self._clock()
            self._cached = token
            self._expires_at = acquired_at + float(token.expires_in)
            refresh_delay = max(
                0.0,
                float(token.expires_in) - self._config.refresh_skew_seconds,
            )
            self._refresh_at = acquired_at + refresh_delay
            return token.access_token

    def clear(self) -> None:
        with self._lock:
            self._cached = None
            self._refresh_at = None
            self._expires_at = None

    def diagnostics(self) -> OAuthTokenDiagnostics:
        with self._lock:
            now = self._clock()
            seconds_until_expiry = None
            if self._expires_at is not None:
                seconds_until_expiry = max(0.0, self._expires_at - now)
            refresh_due = (
                self._cached is None
                or self._refresh_at is None
                or now >= self._refresh_at
            )
            return OAuthTokenDiagnostics(
                cached_token_present=self._cached is not None,
                token_type=self._cached.token_type if self._cached else None,
                seconds_until_expiry=seconds_until_expiry,
                refresh_due=refresh_due,
            )

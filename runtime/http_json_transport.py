#!/usr/bin/env python3
"""Minimal production-oriented JSON transport for planner/verifier endpoints.

Credentials are read from an environment variable at call time and never stored in
configuration objects or returned payloads. HTTPS is required unless the endpoint is
localhost and local development is explicitly allowed.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional


@dataclass(frozen=True)
class HTTPJSONEndpoint:
    url: str
    bearer_token_env: Optional[str] = None
    timeout_seconds: float = 60.0
    allow_local_http: bool = False

    def __post_init__(self) -> None:
        parsed = urllib.parse.urlparse(self.url)
        if parsed.scheme not in ("https", "http") or not parsed.netloc:
            raise ValueError("endpoint URL must be absolute http(s)")
        local = parsed.hostname in ("localhost", "127.0.0.1", "::1")
        if parsed.scheme != "https" and not (self.allow_local_http and local):
            raise ValueError("HTTPS is required except explicitly allowed localhost development")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")


class HTTPJSONTransport:
    """Callable transport compatible with runtime.model_roles.Transport."""

    def __init__(self, endpoint: HTTPJSONEndpoint) -> None:
        self.endpoint = endpoint

    def __call__(self, role: str, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        if not role:
            raise ValueError("role is required")
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Worldshepherd-Role": role,
        }
        if self.endpoint.bearer_token_env:
            token = os.environ.get(self.endpoint.bearer_token_env)
            if not token:
                raise RuntimeError(
                    f"required credential environment variable {self.endpoint.bearer_token_env!r} is not set"
                )
            headers["Authorization"] = f"Bearer {token}"

        body = json.dumps(dict(payload), separators=(",", ":")).encode("utf-8")
        request = urllib.request.Request(
            self.endpoint.url,
            data=body,
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.endpoint.timeout_seconds) as response:
                status = getattr(response, "status", 200)
                raw = response.read()
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"model endpoint returned HTTP {exc.code}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"model endpoint unavailable: {exc.reason}") from exc

        if not 200 <= int(status) < 300:
            raise RuntimeError(f"model endpoint returned HTTP {status}")
        try:
            decoded: Dict[str, Any] = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RuntimeError("model endpoint returned invalid JSON") from exc
        if not isinstance(decoded, dict):
            raise RuntimeError("model endpoint JSON must be an object")
        return decoded

from __future__ import annotations

import json
import ssl
from collections.abc import Callable
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .registry_monotonic_witness import (
    REMOTE_WITNESS_MODE,
    RegistryWitnessConflict,
    RegistryWitnessCoordinates,
    RegistryWitnessError,
    RegistryWitnessRollbackDetected,
    RegistryWitnessUnavailable,
)


MAX_WITNESS_RESPONSE_BYTES = 128 * 1024
HttpExecutor = Callable[[Request, float, ssl.SSLContext], tuple[int, bytes]]


class RegistryWitnessTransportConfigError(RegistryWitnessError):
    pass


def _default_executor(
    request: Request,
    timeout_seconds: float,
    ssl_context: ssl.SSLContext,
) -> tuple[int, bytes]:
    try:
        with urlopen(request, timeout=timeout_seconds, context=ssl_context) as response:
            data = response.read(MAX_WITNESS_RESPONSE_BYTES + 1)
            if len(data) > MAX_WITNESS_RESPONSE_BYTES:
                raise RegistryWitnessUnavailable("registry witness response exceeds size limit")
            return int(response.status), data
    except HTTPError as exc:
        data = exc.read(MAX_WITNESS_RESPONSE_BYTES + 1)
        if len(data) > MAX_WITNESS_RESPONSE_BYTES:
            raise RegistryWitnessUnavailable("registry witness error response exceeds size limit") from exc
        return int(exc.code), data
    except (URLError, TimeoutError, OSError) as exc:
        raise RegistryWitnessUnavailable("registry witness HTTPS transport failed") from exc


class HttpsRegistryWitnessTransport:
    """Authenticated HTTP(S) transport for a separately hosted witness service.

    Production use requires HTTPS. Plain HTTP is permitted only for explicit
    loopback-only qualification. Transport separation is not equivalent to
    independent administration; the verifier deliberately does not infer that.
    """

    witness_mode = REMOTE_WITNESS_MODE

    def __init__(
        self,
        *,
        base_url: str,
        bearer_token: str,
        timeout_seconds: float = 5.0,
        ssl_context: ssl.SSLContext | None = None,
        allow_insecure_loopback_for_tests: bool = False,
        executor: HttpExecutor | None = None,
    ) -> None:
        parsed = urlparse(base_url)
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise RegistryWitnessTransportConfigError(
                "registry witness base URL must not contain credentials, query, or fragment"
            )
        if parsed.path not in {"", "/"}:
            raise RegistryWitnessTransportConfigError(
                "registry witness base URL must not contain a path"
            )
        if parsed.scheme == "https":
            pass
        elif parsed.scheme == "http" and allow_insecure_loopback_for_tests:
            if parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
                raise RegistryWitnessTransportConfigError(
                    "insecure registry witness transport is restricted to loopback tests"
                )
        else:
            raise RegistryWitnessTransportConfigError(
                "registry witness transport requires HTTPS"
            )
        if not parsed.netloc:
            raise RegistryWitnessTransportConfigError("registry witness base URL is incomplete")
        if not isinstance(bearer_token, str) or len(bearer_token) < 32:
            raise RegistryWitnessTransportConfigError(
                "registry witness bearer token must be at least 32 characters"
            )
        if timeout_seconds <= 0 or timeout_seconds > 30:
            raise RegistryWitnessTransportConfigError(
                "registry witness timeout must be greater than zero and at most 30 seconds"
            )
        self.base_url = base_url.rstrip("/")
        self.bearer_token = bearer_token
        self.timeout_seconds = float(timeout_seconds)
        self.ssl_context = ssl_context or ssl.create_default_context()
        self._executor = executor or _default_executor

    def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
    ) -> tuple[int, Any]:
        body: bytes | None = None
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.bearer_token}",
        }
        if payload is not None:
            body = json.dumps(
                payload,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
                allow_nan=False,
            ).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = Request(
            f"{self.base_url}{path}",
            data=body,
            headers=headers,
            method=method,
        )
        status, raw = self._executor(request, self.timeout_seconds, self.ssl_context)
        if not raw:
            parsed: Any = None
        else:
            try:
                parsed = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise RegistryWitnessUnavailable(
                    "registry witness returned invalid JSON"
                ) from exc
        return status, parsed

    @staticmethod
    def _raise_for_error(status: int, payload: Any) -> None:
        detail = payload.get("detail") if isinstance(payload, dict) else None
        code = detail.get("code") if isinstance(detail, dict) else None
        message = detail.get("message") if isinstance(detail, dict) else None
        if status == 409 and code == "ROLLBACK_DETECTED":
            raise RegistryWitnessRollbackDetected(
                str(message or "remote witness rejected rollback")
            )
        if status == 409 and code == "WITNESS_CONFLICT":
            raise RegistryWitnessConflict(
                str(message or "remote witness rejected conflicting checkpoint")
            )
        if status in {401, 403}:
            raise RegistryWitnessUnavailable(
                "registry witness authentication was rejected"
            )
        raise RegistryWitnessUnavailable(
            f"registry witness returned unexpected HTTP status {status}"
        )

    def read_head(self, namespace: str) -> dict[str, Any] | None:
        # The remote service is configured for one namespace. The signed receipt
        # is still verified against the caller's expected namespace by the
        # RegistryMonotonicWitnessVerifier.
        if not isinstance(namespace, str) or not namespace:
            raise RegistryWitnessTransportConfigError("witness namespace is required")
        status, payload = self._request("GET", "/v1/head")
        if status == 404:
            return None
        if status != 200:
            self._raise_for_error(status, payload)
        if not isinstance(payload, dict):
            raise RegistryWitnessUnavailable("registry witness head is not an object")
        return payload

    def witness(
        self,
        namespace: str,
        coordinates: RegistryWitnessCoordinates,
    ) -> dict[str, Any]:
        if not isinstance(namespace, str) or not namespace:
            raise RegistryWitnessTransportConfigError("witness namespace is required")
        status, payload = self._request(
            "POST",
            "/v1/witness",
            {
                "generation": coordinates.generation,
                "state_root_sha256": coordinates.state_root_sha256,
                "commit_hash": coordinates.commit_hash,
            },
        )
        if status != 200:
            self._raise_for_error(status, payload)
        if not isinstance(payload, dict):
            raise RegistryWitnessUnavailable("registry witness receipt is not an object")
        return payload

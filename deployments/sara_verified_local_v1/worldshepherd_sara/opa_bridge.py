from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Callable
from urllib.parse import urlparse
from urllib.request import Request, urlopen


OPA_BRIDGE_SCHEMA = "WS-OPA-DECISION-BRIDGE-V1"
_LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_hex(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def validate_endpoint(endpoint: str, *, allow_remote: bool = False) -> str:
    parsed = urlparse(endpoint)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("OPA endpoint must use http or https")
    if not parsed.hostname:
        raise ValueError("OPA endpoint must include a hostname")
    if not parsed.path.startswith("/v1/data/"):
        raise ValueError("OPA endpoint must target a /v1/data/... decision path")
    if parsed.username or parsed.password:
        raise ValueError("credentials must not be embedded in the OPA endpoint URL")
    if not allow_remote and parsed.hostname not in _LOOPBACK_HOSTS:
        raise ValueError(
            "remote OPA endpoint blocked; use allow_remote=True only after the caller "
            "has established the transport/authentication boundary"
        )
    return endpoint


def evaluate_boolean_policy(
    *,
    endpoint: str,
    input_document: dict[str, Any],
    allow_remote: bool = False,
    timeout_seconds: float = 5.0,
    opener: Callable[..., Any] = urlopen,
    now: Callable[[], datetime] | None = None,
) -> dict[str, Any]:
    validate_endpoint(endpoint, allow_remote=allow_remote)
    if timeout_seconds <= 0 or timeout_seconds > 60:
        raise ValueError("timeout_seconds must be > 0 and <= 60")

    request_payload = {"input": input_document}
    request_bytes = canonical_json_bytes(request_payload)
    request = Request(
        endpoint,
        data=request_bytes,
        method="POST",
        headers={"Content-Type": "application/json"},
    )

    try:
        response = opener(request, timeout=timeout_seconds)
        response_bytes = response.read()
    except Exception as exc:  # fail closed on transport or HTTP failures
        raise RuntimeError(f"OPA policy evaluation failed: {exc}") from exc

    try:
        payload = json.loads(response_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("OPA returned a non-JSON response") from exc

    if not isinstance(payload, dict):
        raise RuntimeError("OPA response must be a JSON object")
    if "result" not in payload:
        raise RuntimeError("OPA response missing required result field")
    if not isinstance(payload["result"], bool):
        raise RuntimeError(
            "OPA bridge requires a boolean result for bounded authorization decisions"
        )

    timestamp = (now or (lambda: datetime.now(timezone.utc)))()
    if timestamp.tzinfo is None:
        raise ValueError("decision timestamp must be timezone-aware")

    receipt = {
        "schema": OPA_BRIDGE_SCHEMA,
        "evaluated_utc": timestamp.astimezone(timezone.utc).isoformat().replace(
            "+00:00", "Z"
        ),
        "endpoint": endpoint,
        "request_sha256": sha256_hex(request_bytes),
        "decision": "ALLOW" if payload["result"] else "DENY",
        "opa_result": payload["result"],
        "decision_id": payload.get("decision_id"),
        "response_sha256": sha256_hex(canonical_json_bytes(payload)),
        "claims_boundary": (
            "This receipt records the result returned by the configured OPA decision path. "
            "It does not establish that the OPA policy is correct, approved, complete, current, "
            "or sufficient for a consequential action. Worldshepherd human-approval and local "
            "authorization gates remain independently applicable where required."
        ),
    }
    return receipt

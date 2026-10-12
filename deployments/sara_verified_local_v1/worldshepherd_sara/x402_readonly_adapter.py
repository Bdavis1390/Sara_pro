from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Callable
from urllib.request import Request, urlopen


X402_SUPPORTED_URL = "https://x402.org/facilitator/supported"
X402_PROBE_SCHEMA = "WS-X402-READONLY-CAPABILITY-PROBE-G4A-V1"
X402_ALLOWED_VERSION = 2
X402_ALLOWED_SCHEME = "exact"
X402_ALLOWED_NETWORK = "eip155:84532"
MAX_SUPPORTED_RESPONSE_BYTES = 65536
USER_AGENT = "Worldshepherd-G4A-readonly-probe/0.1"


class X402ReadOnlyAdapterError(RuntimeError):
    pass


@dataclass(frozen=True)
class X402ReadOnlyCapability:
    version: int
    scheme: str
    network: str
    capability_sha256: str


def _canonical_capability_document(kind: dict[str, Any]) -> dict[str, Any]:
    try:
        version = int(kind["x402Version"])
        scheme = str(kind["scheme"])
        network = str(kind["network"])
    except (KeyError, TypeError, ValueError) as exc:
        raise X402ReadOnlyAdapterError("malformed x402 supported-kind entry") from exc

    return {
        "schema": X402_PROBE_SCHEMA,
        "x402Version": version,
        "scheme": scheme,
        "network": network,
    }


def capability_sha256(kind: dict[str, Any]) -> str:
    document = _canonical_capability_document(kind)
    encoded = json.dumps(document, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_supported_response(payload: dict[str, Any]) -> X402ReadOnlyCapability:
    """Select only the first explicitly approved testnet x402 capability.

    G4A intentionally supports exactly x402 v2 + exact + Base Sepolia.
    Mainnet and every other scheme/network are ignored, not auto-promoted.
    """

    if not isinstance(payload, dict):
        raise X402ReadOnlyAdapterError("x402 /supported response must be a JSON object")
    kinds = payload.get("kinds")
    if not isinstance(kinds, list):
        raise X402ReadOnlyAdapterError("x402 /supported response must contain a kinds array")

    for item in kinds:
        if not isinstance(item, dict):
            continue
        try:
            document = _canonical_capability_document(item)
        except X402ReadOnlyAdapterError:
            continue
        if (
            document["x402Version"] == X402_ALLOWED_VERSION
            and document["scheme"] == X402_ALLOWED_SCHEME
            and document["network"] == X402_ALLOWED_NETWORK
        ):
            return X402ReadOnlyCapability(
                version=X402_ALLOWED_VERSION,
                scheme=X402_ALLOWED_SCHEME,
                network=X402_ALLOWED_NETWORK,
                capability_sha256=capability_sha256(item),
            )

    raise X402ReadOnlyAdapterError(
        "approved x402 v2 exact Base Sepolia capability is not advertised"
    )


def fetch_supported(
    *,
    opener: Callable[..., Any] = urlopen,
    timeout: float = 15.0,
) -> X402ReadOnlyCapability:
    """Perform one bounded read-only GET against the public facilitator.

    This function has no wallet, signer, payment payload, /verify call, /settle
    call, POST method, API credential, or transaction capability.
    """

    request = Request(
        X402_SUPPORTED_URL,
        headers={
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        },
        method="GET",
    )
    try:
        with opener(request, timeout=timeout) as response:
            status = int(getattr(response, "status", 0))
            if status != 200:
                raise X402ReadOnlyAdapterError(
                    f"x402 /supported returned HTTP {status}"
                )
            raw = response.read(MAX_SUPPORTED_RESPONSE_BYTES + 1)
    except X402ReadOnlyAdapterError:
        raise
    except Exception as exc:
        raise X402ReadOnlyAdapterError("x402 read-only capability probe failed") from exc

    if len(raw) > MAX_SUPPORTED_RESPONSE_BYTES:
        raise X402ReadOnlyAdapterError("x402 /supported response exceeds bounded size")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise X402ReadOnlyAdapterError("x402 /supported response is not valid JSON") from exc
    if not isinstance(payload, dict):
        raise X402ReadOnlyAdapterError("x402 /supported response must be a JSON object")
    return validate_supported_response(payload)

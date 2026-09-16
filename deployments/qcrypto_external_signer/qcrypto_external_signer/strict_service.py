"""Public fail-closed request surface for the isolated custody service."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from .custody import CustodyError, ExternalCustodyService as _CoreExternalCustodyService

_EXPECTED_TOP_LEVEL = frozenset(
    {
        "schema",
        "request_id",
        "intent",
        "human_approval",
        "handoff",
        "preflight",
        "unsigned_payload_b64url",
        "observed_network_identity_sha256",
        "broadcast_requested",
        "chain_native_signing_requested",
    }
)
_SECRET_KEY_FRAGMENTS = (
    "private_key",
    "secret_key",
    "seed_phrase",
    "mnemonic",
    "xprv",
    "wallet_seed",
    "validator_key",
    "withdrawal_key",
)


def _reject_secret_shaped_fields(value: Any, path: str = "request") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str):
                raise CustodyError(f"{path} contains a non-string JSON key")
            lowered = key.lower()
            if any(fragment in lowered for fragment in _SECRET_KEY_FRAGMENTS):
                raise CustodyError(f"secret/private-key-shaped field is forbidden at {path}.{key}")
            _reject_secret_shaped_fields(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_secret_shaped_fields(child, f"{path}[{index}]")


class StrictExternalCustodyService(_CoreExternalCustodyService):
    """Only supported entry point for custody-release requests.

    The lower-level service exists to keep ledger/signing mechanics independently
    testable.  This class supplies the public trust boundary: exact top-level schema,
    recursive secret-field rejection, then all cryptographic and ledger checks.
    """

    def execute_release(self, request: dict[str, Any], *, now: datetime | None = None) -> dict[str, Any]:
        if not isinstance(request, dict):
            raise CustodyError("custody request must be a JSON object")
        actual = frozenset(request)
        if actual != _EXPECTED_TOP_LEVEL:
            missing = sorted(_EXPECTED_TOP_LEVEL - actual)
            extra = sorted(actual - _EXPECTED_TOP_LEVEL)
            detail = []
            if missing:
                detail.append("missing=" + ",".join(missing))
            if extra:
                detail.append("extra=" + ",".join(extra))
            raise CustodyError("custody request surface mismatch: " + "; ".join(detail))
        _reject_secret_shaped_fields(request)
        return super().execute_release(request, now=now)

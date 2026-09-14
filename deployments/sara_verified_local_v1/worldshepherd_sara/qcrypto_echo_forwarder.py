from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .models import AuditRecord


EXPECTED_EVENTS = frozenset(
    {
        "qcrypto_echo_state",
        "qcrypto_prime_state",
        "qcrypto_sara_state",
        "qcrypto_overwatch_state",
    }
)


class QCryptoEchoForwarderError(RuntimeError):
    pass


class QCryptoEchoConflict(QCryptoEchoForwarderError):
    pass


Transport = Callable[[str, str, dict[str, Any], str], tuple[int, dict[str, Any]]]


@dataclass(frozen=True)
class QCryptoEchoSyncResult:
    stored: int
    deduplicated: int
    event_ids: tuple[str, ...]
    reconciliation: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "WS-QCRYPTO-ECHO-SYNC-V1",
            "forwarded_event_count": len(self.event_ids),
            "stored_count": self.stored,
            "deduplicated_count": self.deduplicated,
            "event_ids": list(self.event_ids),
            "reconciliation": self.reconciliation,
            "migration_executed": False,
            "execution_authority": False,
            "live_value_authorized": False,
            "federal_compliance_established": False,
            "ws_cae_conformance_established": False,
            "claim_boundary": (
                "Bounded SARA-to-ECHO evidence synchronization only; no migration execution, "
                "live-value authorization, post-quantum checkpoint assurance, Federal compliance, "
                "WS-CAE conformance, or external attestation is established."
            ),
        }


def stdlib_json_transport(
    base_url: str,
    path: str,
    payload: dict[str, Any],
    token: str,
) -> tuple[int, dict[str, Any]]:
    request = Request(
        f"{base_url.rstrip('/')}{path}",
        data=json.dumps(payload, sort_keys=True).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )
    try:
        with urlopen(request, timeout=3.0) as response:
            status = int(response.status)
            raw = response.read(262144)
    except HTTPError as exc:
        status = int(exc.code)
        raw = exc.read(262144)
    except (URLError, TimeoutError, OSError) as exc:
        raise QCryptoEchoForwarderError("ECHO persistence service is unavailable") from exc
    try:
        value = json.loads(raw.decode("utf-8")) if raw else {}
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise QCryptoEchoForwarderError("ECHO returned invalid JSON") from exc
    if not isinstance(value, dict):
        raise QCryptoEchoForwarderError("ECHO returned a non-object response")
    return status, value


class QCryptoEchoForwarder:
    def __init__(
        self,
        *,
        base_url: str,
        token: str,
        transport: Transport = stdlib_json_transport,
    ) -> None:
        if not base_url or not token:
            raise QCryptoEchoForwarderError("ECHO forwarding requires a URL and token")
        self.base_url = base_url.rstrip("/")
        self._token = token
        self._transport = transport

    def sync(self, records: list[AuditRecord]) -> QCryptoEchoSyncResult:
        if len(records) != 4 or {record.event for record in records} != EXPECTED_EVENTS:
            raise QCryptoEchoForwarderError("ECHO sync requires the four canonical QCRYPTO events")

        event_ids: list[str] = []
        documents: list[dict[str, Any]] = []
        stored = 0
        deduplicated = 0
        for record in records:
            event_id = record.payload.get("_outbox_event_id")
            if not isinstance(event_id, str) or not event_id or event_id in event_ids:
                raise QCryptoEchoForwarderError("QCRYPTO evidence has missing or duplicate event IDs")
            event_ids.append(event_id)
            document = record.model_dump(mode="json", exclude_none=True)
            documents.append(document)
            status, body = self._transport(self.base_url, "/v1/ingest", document, self._token)
            if status == 409:
                raise QCryptoEchoConflict("ECHO rejected conflicting QCRYPTO evidence")
            if status < 200 or status >= 300:
                raise QCryptoEchoForwarderError(f"ECHO ingest failed with HTTP {status}")
            if body.get("event_id") != event_id:
                raise QCryptoEchoForwarderError("ECHO ingest response event ID mismatch")
            outcome = body.get("outcome")
            if outcome == "STORED":
                stored += 1
            elif outcome == "DEDUPLICATED":
                deduplicated += 1
            else:
                raise QCryptoEchoForwarderError("ECHO ingest returned an unsupported outcome")

        status, reconciliation = self._transport(
            self.base_url,
            "/v1/reconcile",
            {"records": documents},
            self._token,
        )
        if status == 409:
            raise QCryptoEchoConflict("ECHO reconciliation reported conflicting evidence")
        if status < 200 or status >= 300:
            raise QCryptoEchoForwarderError(f"ECHO reconciliation failed with HTTP {status}")
        counts = reconciliation.get("counts")
        required = {"MATCHED": 4, "SARA_ONLY": 0, "ECHO_ONLY": 0, "PAYLOAD_MISMATCH": 0}
        if not isinstance(counts, dict) or any(counts.get(key) != value for key, value in required.items()):
            raise QCryptoEchoForwarderError("ECHO reconciliation did not confirm an exact four-event match")
        return QCryptoEchoSyncResult(stored, deduplicated, tuple(event_ids), reconciliation)

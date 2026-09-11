from __future__ import annotations

import hashlib
import json
import sqlite3
from typing import Any

from .prime_sentinel_issuance_store import (
    ISSUANCE_EVENT_SCHEMA,
    ZERO_HASH,
    PrimeSentinelIssuanceStore,
    PrimeSentinelIssuanceStoreError,
)


def _payload_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def verify_issuance_ledger_integrity(
    store: PrimeSentinelIssuanceStore,
) -> dict[str, Any]:
    try:
        connection = sqlite3.connect(store.db_path, timeout=5.0)
        connection.row_factory = sqlite3.Row
        quick = connection.execute("PRAGMA quick_check").fetchone()
        if quick is None or quick[0] != "ok":
            return {"ok": False, "reason": "SQLITE_QUICK_CHECK_FAILED"}
        records = {
            row["request_id"]: row
            for row in connection.execute("SELECT * FROM issuance").fetchall()
        }
        events = connection.execute(
            "SELECT * FROM issuance_events ORDER BY sequence"
        ).fetchall()
    except sqlite3.Error as exc:
        raise PrimeSentinelIssuanceStoreError(
            "unable to verify issuance ledger integrity"
        ) from exc
    finally:
        try:
            connection.close()
        except UnboundLocalError:
            pass

    previous_hash = ZERO_HASH
    event_types_by_request: dict[str, list[str]] = {}
    for event in events:
        request_id = event["request_id"]
        record = records.get(request_id)
        if record is None:
            return {
                "ok": False,
                "reason": "EVENT_REFERENCES_MISSING_ISSUANCE",
                "request_id": request_id,
            }
        if event["schema"] != ISSUANCE_EVENT_SCHEMA:
            return {"ok": False, "reason": "EVENT_SCHEMA_MISMATCH"}
        if event["previous_hash"] != previous_hash:
            return {"ok": False, "reason": "EVENT_CHAIN_PREVIOUS_HASH_MISMATCH"}

        event_type = event["event_type"]
        if event_type == "PREPARED":
            payload = {
                "authorization_id": record["authorization_id"],
                "prime_id": record["prime_id"],
                "target_environment": record["target_environment"],
                "lifetime_seconds": record["lifetime_seconds"],
                "key_id": record["key_id"],
                "issued_at": record["issued_at"],
                "expires_at": record["expires_at"],
                "nonce": record["nonce"],
                "request_digest_sha256": record["request_digest_sha256"],
            }
        elif event_type == "SIGNED":
            if not record["signature_b64url"] or not record["assertion_json"]:
                return {
                    "ok": False,
                    "reason": "SIGNED_EVENT_WITHOUT_SIGNED_RECORD",
                    "request_id": request_id,
                }
            payload = {
                "authorization_id": record["authorization_id"],
                "signature_sha256": hashlib.sha256(
                    record["signature_b64url"].encode("ascii")
                ).hexdigest(),
                "assertion_sha256": hashlib.sha256(
                    record["assertion_json"].encode("utf-8")
                ).hexdigest(),
            }
        else:
            return {"ok": False, "reason": "UNKNOWN_EVENT_TYPE"}

        if event["payload_sha256"] != _payload_hash(payload):
            return {
                "ok": False,
                "reason": "ISSUANCE_EVENT_PAYLOAD_MISMATCH",
                "request_id": request_id,
                "event_type": event_type,
            }
        canonical = {
            "schema": event["schema"],
            "event_id": event["event_id"],
            "request_id": request_id,
            "event_type": event_type,
            "event_time": event["event_time"],
            "payload_sha256": event["payload_sha256"],
            "previous_hash": event["previous_hash"],
        }
        expected_hash = hashlib.sha256(
            json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        if event["event_hash"] != expected_hash:
            return {
                "ok": False,
                "reason": "EVENT_HASH_MISMATCH",
                "request_id": request_id,
            }
        previous_hash = event["event_hash"]
        event_types_by_request.setdefault(request_id, []).append(event_type)

    for request_id, record in records.items():
        expected_events = ["PREPARED"] if record["state"] == "PREPARED" else ["PREPARED", "SIGNED"]
        if event_types_by_request.get(request_id, []) != expected_events:
            return {
                "ok": False,
                "reason": "ISSUANCE_EVENT_LIFECYCLE_MISMATCH",
                "request_id": request_id,
            }
        if record["state"] == "SIGNED":
            try:
                assertion = json.loads(record["assertion_json"])
            except (TypeError, json.JSONDecodeError):
                return {
                    "ok": False,
                    "reason": "SIGNED_ASSERTION_JSON_INVALID",
                    "request_id": request_id,
                }
            checks = {
                "authorization_id": record["authorization_id"],
                "prime_id": record["prime_id"],
                "target_environment": record["target_environment"],
                "key_id": record["key_id"],
                "issued_at": record["issued_at"],
                "expires_at": record["expires_at"],
                "nonce": record["nonce"],
                "signature_b64url": record["signature_b64url"],
            }
            if any(assertion.get(key) != value for key, value in checks.items()):
                return {
                    "ok": False,
                    "reason": "SIGNED_ASSERTION_RECORD_MISMATCH",
                    "request_id": request_id,
                }

    return {
        "ok": True,
        "records": len(records),
        "events": len(events),
        "tail_event_hash": previous_hash,
        "integrity_model": "LOCAL_HASH_CHAIN_PLUS_CROSS_TABLE_RECOMPUTATION",
    }

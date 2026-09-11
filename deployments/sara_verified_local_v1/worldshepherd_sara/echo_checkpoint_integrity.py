from __future__ import annotations

import json
import sqlite3
from typing import Any

from .echo_checkpoint import CHECKPOINT_DB_SCHEMA, EchoCheckpointError, EchoCheckpointManager
from .echo_checkpoint_verify import EchoCheckpointVerificationError, verify_bundle, verify_chain


def check_checkpoint_integrity(manager: EchoCheckpointManager) -> dict[str, Any]:
    connection = sqlite3.connect(manager.store.db_path, timeout=5.0)
    connection.row_factory = sqlite3.Row
    try:
        quick = connection.execute("PRAGMA quick_check").fetchone()
        if quick is None or quick[0] != "ok":
            raise EchoCheckpointError("ECHO checkpoint database integrity check failed")
        schema = connection.execute(
            "SELECT value FROM echo_checkpoint_metadata WHERE name='schema'"
        ).fetchone()
        if schema is None or schema["value"] != CHECKPOINT_DB_SCHEMA:
            raise EchoCheckpointError("ECHO checkpoint database schema mismatch")
        binding = connection.execute(
            "SELECT value FROM echo_checkpoint_metadata WHERE name=?",
            (f"checkpoint_key_fingerprint:{manager.key_id}",),
        ).fetchone()
        if binding is None or binding["value"] != manager.fingerprint_sha256:
            raise EchoCheckpointError("ECHO checkpoint key binding mismatch")

        rows = connection.execute(
            "SELECT * FROM echo_checkpoints ORDER BY sequence"
        ).fetchall()
        if not rows:
            return {
                "ok": True,
                "checkpoint_count": 0,
                "latest_sequence": None,
                "latest_checkpoint_sha256": None,
                "key_id": manager.key_id,
                "key_fingerprint_sha256": manager.fingerprint_sha256,
            }

        bundles: list[dict[str, Any]] = []
        for expected_sequence, row in enumerate(rows, start=1):
            if int(row["sequence"]) != expected_sequence:
                raise EchoCheckpointError("stored checkpoint sequence is not contiguous")
            try:
                bundle = json.loads(row["bundle_json"])
                manifest_copy = json.loads(row["manifest_json"])
            except json.JSONDecodeError as exc:
                raise EchoCheckpointError("stored checkpoint JSON is malformed") from exc
            if not isinstance(bundle, dict) or not isinstance(manifest_copy, dict):
                raise EchoCheckpointError("stored checkpoint JSON shape is invalid")
            try:
                verified = verify_bundle(bundle, manager.fingerprint_sha256)
            except EchoCheckpointVerificationError as exc:
                raise EchoCheckpointError(f"stored checkpoint verification failed: {exc}") from exc
            manifest = bundle["manifest"]
            if manifest_copy != manifest:
                raise EchoCheckpointError("stored manifest copy does not match checkpoint bundle")
            comparisons = {
                "checkpoint_id": manifest["checkpoint_id"],
                "created_at": manifest["created_at"],
                "previous_checkpoint_sha256": manifest["previous_checkpoint_sha256"],
                "checkpoint_sha256": verified["checkpoint_sha256"],
                "merkle_root_sha256": manifest["merkle_root_sha256"],
                "event_count": manifest["event_count"],
                "key_id": manifest["key_id"],
                "key_fingerprint_sha256": manifest["key_fingerprint_sha256"],
                "signature_b64url": bundle["signature_b64url"],
            }
            for field, expected in comparisons.items():
                if row[field] != expected:
                    raise EchoCheckpointError(f"stored checkpoint row mismatch: {field}")
            members = connection.execute(
                "SELECT ordinal,event_id,semantic_sha256 FROM echo_checkpoint_events "
                "WHERE checkpoint_sequence=? ORDER BY ordinal",
                (expected_sequence,),
            ).fetchall()
            member_values = [
                {
                    "ordinal": int(member["ordinal"]),
                    "event_id": str(member["event_id"]),
                    "semantic_sha256": str(member["semantic_sha256"]),
                }
                for member in members
            ]
            if member_values != manifest["events"]:
                raise EchoCheckpointError("checkpoint membership rows do not match signed manifest")
            bundles.append(bundle)

        try:
            verified_chain = verify_chain(bundles, manager.fingerprint_sha256)
        except EchoCheckpointVerificationError as exc:
            raise EchoCheckpointError(f"stored checkpoint chain failed verification: {exc}") from exc
        return {
            "ok": True,
            "checkpoint_count": verified_chain["checkpoint_count"],
            "latest_sequence": verified_chain["last_sequence"],
            "latest_checkpoint_sha256": verified_chain["last_checkpoint_sha256"],
            "key_id": manager.key_id,
            "key_fingerprint_sha256": manager.fingerprint_sha256,
        }
    except sqlite3.Error as exc:
        raise EchoCheckpointError("unable to inspect ECHO checkpoint ledger") from exc
    finally:
        connection.close()

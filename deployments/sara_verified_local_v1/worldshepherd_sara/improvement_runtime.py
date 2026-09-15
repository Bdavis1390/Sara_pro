from __future__ import annotations

import json
import os
from collections import Counter
from pathlib import Path

from .echo_event_store import EchoEventStore
from .improvement_checkpoint import LEDGER_ECHO_EVENT_SCHEMA, build_ledger_checkpoint
from .improvement_feedback import (
    ImprovementFeedbackCursor,
    ImprovementFeedbackPolicy,
    ImprovementFeedbackReport,
    feedback_cursor_digest,
    run_operational_feedback_cycle,
)
from .improvement_ledger import ImprovementLedger


RUNTIME_STATE_SCHEMA = "WS-RI-RUNTIME-STATE-V1"
RUNTIME_STATE_FILENAME = "ws-ri-runtime-state.json"


class ImprovementRuntimeError(RuntimeError):
    pass


class ImprovementRuntime:
    """Operator-invoked WS-RI runtime with persistent bounded-feedback cursor.

    The runtime does not schedule itself. Repeated execution requires an
    existing authorized scheduler or a human/operator call.
    """

    def __init__(
        self,
        wsri_data_dir: str | Path,
        *,
        echo_data_dir: str | Path | None = None,
    ) -> None:
        root = Path(wsri_data_dir)
        if not root.is_absolute():
            raise ImprovementRuntimeError("WS-RI data directory must be absolute")
        root.mkdir(parents=True, exist_ok=True)
        self.root = root
        self.ledger = ImprovementLedger(root)
        self.echo_store = None
        if echo_data_dir is not None:
            echo_root = Path(echo_data_dir)
            if not echo_root.is_absolute():
                raise ImprovementRuntimeError("WS-RI ECHO data directory must be absolute")
            self.echo_store = EchoEventStore(echo_root)
        self.state_path = root / RUNTIME_STATE_FILENAME

    @classmethod
    def from_environment(cls) -> "ImprovementRuntime | None":
        wsri = os.getenv("WSRI_DATA_DIR", "").strip()
        if not wsri:
            return None
        echo = os.getenv("WSRI_ECHO_DATA_DIR", "").strip() or None
        return cls(wsri, echo_data_dir=echo)

    def load_cursor(self) -> ImprovementFeedbackCursor:
        if not self.state_path.exists():
            return ImprovementFeedbackCursor()
        if self.state_path.is_symlink():
            raise ImprovementRuntimeError("WS-RI runtime state must not be a symbolic link")
        try:
            value = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ImprovementRuntimeError("unable to read WS-RI runtime state") from exc
        if not isinstance(value, dict) or value.get("schema") != RUNTIME_STATE_SCHEMA:
            raise ImprovementRuntimeError("WS-RI runtime state schema mismatch")
        raw = value.get("feedback_cursor")
        if not isinstance(raw, dict):
            raise ImprovementRuntimeError("WS-RI runtime feedback cursor is malformed")
        try:
            cursor = ImprovementFeedbackCursor.model_validate(raw)
        except ValueError as exc:
            raise ImprovementRuntimeError("WS-RI runtime feedback cursor is invalid") from exc
        stored_digest = value.get("feedback_cursor_digest")
        if not isinstance(stored_digest, str):
            raise ImprovementRuntimeError("WS-RI runtime cursor digest is missing")
        if stored_digest != feedback_cursor_digest(cursor):
            raise ImprovementRuntimeError("WS-RI runtime cursor digest mismatch")
        return cursor

    def _save_cursor(self, cursor: ImprovementFeedbackCursor) -> None:
        payload = {
            "schema": RUNTIME_STATE_SCHEMA,
            "feedback_cursor": cursor.model_dump(mode="json"),
            "feedback_cursor_digest": feedback_cursor_digest(cursor),
            "claims_boundary": (
                "operational cursor state only; not qualification evidence, "
                "authorization, claim promotion, or deployment evidence"
            ),
        }
        temp = self.state_path.with_suffix(".tmp")
        data = json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"
        try:
            with temp.open("w", encoding="utf-8") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp, self.state_path)
            descriptor = os.open(self.root, os.O_RDONLY)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
        except OSError as exc:
            try:
                temp.unlink(missing_ok=True)
            except OSError:
                pass
            raise ImprovementRuntimeError("unable to persist WS-RI runtime state") from exc

    def status(self) -> dict[str, object]:
        records = self.ledger.records()
        head = records[-1] if records else None
        counts = dict(sorted(Counter(record.state for record in records).items()))
        cursor = self.load_cursor()
        return {
            "configured": True,
            "echo_source_configured": self.echo_store is not None,
            "ledger_chain_verified": self.ledger.verify_chain(),
            "record_count": len(records),
            "head_sequence": None if head is None else head.sequence,
            "head_record_digest": None if head is None else head.record_digest,
            "state_counts": counts,
            "feedback_cursor": cursor.model_dump(mode="json"),
            "feedback_cursor_digest": feedback_cursor_digest(cursor),
            "autonomous_scheduler_active": False,
            "claim_promotion_performed": False,
            "deployment_performed": False,
            "external_execution_performed": False,
        }

    def export_records(
        self,
        *,
        limit: int = 50,
        improvement_id: str | None = None,
    ) -> list[dict[str, object]]:
        if limit < 1 or limit > 500:
            raise ImprovementRuntimeError("record export limit must be between 1 and 500")
        records = self.ledger.records()
        if improvement_id is not None:
            records = [record for record in records if record.improvement_id == improvement_id]
        selected = records[-limit:]
        return [
            {
                "sequence": record.sequence,
                "improvement_id": record.improvement_id,
                "state": record.state,
                "proposal_digest": record.proposal_digest,
                "previous_record_digest": record.previous_record_digest,
                "prior_improvement_digest": record.prior_improvement_digest,
                "actor": record.actor,
                "recorded_utc": record.recorded_utc,
                "reason": record.reason,
                "record_digest": record.record_digest,
                "proposal": record.proposal().model_dump(mode="json"),
            }
            for record in selected
        ]

    def run_feedback_once(
        self,
        *,
        actor: str,
        policy: ImprovementFeedbackPolicy | None = None,
    ) -> ImprovementFeedbackReport:
        if self.echo_store is None:
            raise ImprovementRuntimeError("WS-RI ECHO source is not configured")
        cursor = self.load_cursor()
        next_cursor, report = run_operational_feedback_cycle(
            self.echo_store,
            self.ledger,
            cursor,
            policy=policy,
            actor=actor,
        )
        self._save_cursor(next_cursor)
        return report

    def checkpoint_outbox_payload(self, *, created_utc: str) -> dict[str, object]:
        checkpoint = build_ledger_checkpoint(self.ledger, created_utc=created_utc)
        return {
            "_ws_ri_ledger_checkpoint": checkpoint.model_dump(mode="json"),
            "anchor_schema": LEDGER_ECHO_EVENT_SCHEMA,
            "claims_boundary": (
                "SARA outbox staging only; ECHO custody and signed inclusion require "
                "separate successful ECHO ingestion/checkpoint verification"
            ),
        }

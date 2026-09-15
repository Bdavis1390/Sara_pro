from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from .echo_event_store import EchoEventStore, EchoStoredEvent
from .improvement_cycle import ImprovementState
from .improvement_ledger import ImprovementLedger, ImprovementLedgerError
from .operational_improvement import OperationalImprovementSignalError, stored_echo_event_to_improvement
from .qualification import canonical_digest

_SIGNAL_KEY = "_ws_improvement_signal"


class ImprovementFeedbackPolicy(BaseModel):
    max_echo_events_per_cycle: int = Field(default=64, ge=1, le=4096)
    max_new_proposals_per_cycle: int = Field(default=32, ge=1, le=1024)
    allow_claim_promotion: bool = False
    allow_deployment: bool = False
    allow_external_execution: bool = False

    @model_validator(mode="after")
    def fail_closed(self) -> "ImprovementFeedbackPolicy":
        if self.allow_claim_promotion:
            raise ValueError("feedback cycle may not authorize claim promotion")
        if self.allow_deployment:
            raise ValueError("feedback cycle may not authorize deployment")
        if self.allow_external_execution:
            raise ValueError("feedback cycle may not authorize external execution")
        return self


class ImprovementFeedbackCursor(BaseModel):
    schema: str = "ws-ri-feedback-cursor-1"
    cycle_index: int = Field(default=0, ge=0)
    last_first_ingested_at: str | None = None
    last_event_id: str | None = None
    prior_state_digest: str | None = None


class ImprovementFeedbackReport(BaseModel):
    schema: str = "ws-ri-feedback-report-1"
    cycle_index: int
    scanned_events: int
    ordinary_events_ignored: int
    explicit_signals_seen: int
    proposals_stored: int
    proposals_deduplicated: int
    invalid_signal_event_ids: list[str] = Field(default_factory=list)
    deferred_signal_event_ids: list[str] = Field(default_factory=list)
    cursor_event_id: str | None = None
    claim_promotion_performed: bool = False
    deployment_performed: bool = False
    external_execution_performed: bool = False
    report_digest: str = ""


def feedback_cursor_digest(cursor: ImprovementFeedbackCursor) -> str:
    return canonical_digest(cursor.model_dump(mode="json"))


def _sort_key(item: EchoStoredEvent) -> tuple[str, str]:
    return item.first_ingested_at, item.event_id


def _after_cursor(item: EchoStoredEvent, cursor: ImprovementFeedbackCursor) -> bool:
    if cursor.last_first_ingested_at is None or cursor.last_event_id is None:
        return True
    return _sort_key(item) > (cursor.last_first_ingested_at, cursor.last_event_id)


def run_operational_feedback_cycle(
    store: EchoEventStore,
    ledger: ImprovementLedger,
    cursor: ImprovementFeedbackCursor,
    *,
    policy: ImprovementFeedbackPolicy | None = None,
    actor: str = "SARA",
) -> tuple[ImprovementFeedbackCursor, ImprovementFeedbackReport]:
    active = policy or ImprovementFeedbackPolicy()
    if not actor.strip():
        raise ValueError("identified ledger actor is required")
    pending = [item for item in store.all_records() if _after_cursor(item, cursor)]
    pending.sort(key=_sort_key)
    window = pending[: active.max_echo_events_per_cycle]
    scanned = ordinary = explicit = stored_count = dedupe_count = 0
    invalid: list[str] = []
    deferred: list[str] = []
    last_consumed: EchoStoredEvent | None = None
    for item in window:
        scanned += 1
        try:
            payload = item.payload()
        except Exception:
            invalid.append(item.event_id)
            break
        if _SIGNAL_KEY not in payload:
            ordinary += 1
            last_consumed = item
            continue
        explicit += 1
        if stored_count + dedupe_count >= active.max_new_proposals_per_cycle:
            deferred.append(item.event_id)
            break
        try:
            proposal = stored_echo_event_to_improvement(item, created_utc=item.first_ingested_at)
            if proposal.state != ImprovementState.PROPOSED:
                raise ImprovementLedgerError("feedback producer emitted a non-PROPOSED improvement")
            result = ledger.append(
                proposal,
                actor=actor.strip(),
                recorded_utc=item.first_ingested_at,
                reason=f"bounded ECHO feedback ingestion from {item.event_id}",
            )
        except (OperationalImprovementSignalError, ImprovementLedgerError, ValueError):
            invalid.append(item.event_id)
            last_consumed = item
            continue
        if result.outcome == "STORED":
            stored_count += 1
        elif result.outcome == "DEDUPLICATED":
            dedupe_count += 1
        else:
            raise ImprovementLedgerError("unexpected WS-RI ledger append outcome")
        last_consumed = item
    before_digest = feedback_cursor_digest(cursor)
    next_cursor = ImprovementFeedbackCursor(
        cycle_index=cursor.cycle_index + 1,
        last_first_ingested_at=cursor.last_first_ingested_at if last_consumed is None else last_consumed.first_ingested_at,
        last_event_id=cursor.last_event_id if last_consumed is None else last_consumed.event_id,
        prior_state_digest=before_digest,
    )
    payload = {
        "schema": "ws-ri-feedback-report-1",
        "cycle_index": next_cursor.cycle_index,
        "scanned_events": scanned,
        "ordinary_events_ignored": ordinary,
        "explicit_signals_seen": explicit,
        "proposals_stored": stored_count,
        "proposals_deduplicated": dedupe_count,
        "invalid_signal_event_ids": invalid,
        "deferred_signal_event_ids": deferred,
        "cursor_event_id": next_cursor.last_event_id,
        "claim_promotion_performed": False,
        "deployment_performed": False,
        "external_execution_performed": False,
    }
    return next_cursor, ImprovementFeedbackReport(**payload, report_digest=canonical_digest(payload))

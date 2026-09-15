from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from .improvement_cycle import ImprovementProposal, ImprovementState, proposal_digest
from .qualification import canonical_digest

LEDGER_SCHEMA = "WS-RI-LEDGER-V1"
MAX_LEDGER_RECORDS = 16384

class ImprovementLedgerError(RuntimeError):
    pass

@dataclass(frozen=True)
class ImprovementLedgerRecord:
    sequence: int
    improvement_id: str
    state: str
    proposal_digest: str
    proposal_json: str
    previous_record_digest: str | None
    prior_improvement_digest: str | None
    actor: str
    recorded_utc: str
    reason: str
    record_digest: str

    def proposal(self) -> ImprovementProposal:
        value = json.loads(self.proposal_json)
        if not isinstance(value, dict):
            raise ImprovementLedgerError("stored proposal is not a JSON object")
        return ImprovementProposal.model_validate(value)

@dataclass(frozen=True)
class ImprovementLedgerAppendResult:
    outcome: str
    record: ImprovementLedgerRecord

_ALLOWED_TRANSITIONS = {
    ImprovementState.PROPOSED: {ImprovementState.VALIDATING, ImprovementState.HUMAN_REVIEW_REQUIRED, ImprovementState.QUARANTINED},
    ImprovementState.VALIDATING: {ImprovementState.HUMAN_REVIEW_REQUIRED, ImprovementState.QUARANTINED},
    ImprovementState.QUARANTINED: {ImprovementState.PROPOSED, ImprovementState.VALIDATING},
    ImprovementState.HUMAN_REVIEW_REQUIRED: {ImprovementState.PROMOTED, ImprovementState.REJECTED},
    ImprovementState.PROMOTED: {ImprovementState.SUPERSEDED},
    ImprovementState.REJECTED: set(),
    ImprovementState.SUPERSEDED: set(),
}

def _transition_allowed(previous: ImprovementState | None, current: ImprovementState) -> bool:
    return current == ImprovementState.PROPOSED if previous is None else current in _ALLOWED_TRANSITIONS[previous]

def _row_to_record(row: sqlite3.Row) -> ImprovementLedgerRecord:
    return ImprovementLedgerRecord(
        sequence=int(row["sequence"]), improvement_id=str(row["improvement_id"]), state=str(row["state"]),
        proposal_digest=str(row["proposal_digest"]), proposal_json=str(row["proposal_json"]),
        previous_record_digest=row["previous_record_digest"], prior_improvement_digest=row["prior_improvement_digest"],
        actor=str(row["actor"]), recorded_utc=str(row["recorded_utc"]), reason=str(row["reason"]), record_digest=str(row["record_digest"]),
    )

def _record_material(record: ImprovementLedgerRecord | None = None, **values) -> dict:
    if record is not None:
        values = {
            "improvement_id": record.improvement_id,
            "state": record.state,
            "proposal_digest": record.proposal_digest,
            "previous_record_digest": record.previous_record_digest,
            "prior_improvement_digest": record.prior_improvement_digest,
            "actor": record.actor,
            "recorded_utc": record.recorded_utc,
            "reason": record.reason,
        }
    return {"schema": LEDGER_SCHEMA, **values}

class ImprovementLedger:
    """Persistent, application-enforced WS-RI lifecycle custody chain."""

    def __init__(self, data_dir: str | Path) -> None:
        self.data_dir = Path(data_dir)
        if not self.data_dir.is_absolute():
            raise ImprovementLedgerError("WS-RI ledger data directory must be absolute")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.data_dir / "ws-ri-ledger.db"
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, timeout=5.0, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA synchronous = FULL")
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection

    def _initialize(self) -> None:
        connection = self._connect()
        try:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS wsri_metadata (name TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS wsri_records (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    improvement_id TEXT NOT NULL,
                    state TEXT NOT NULL,
                    proposal_digest TEXT NOT NULL,
                    proposal_json TEXT NOT NULL,
                    previous_record_digest TEXT,
                    prior_improvement_digest TEXT,
                    actor TEXT NOT NULL,
                    recorded_utc TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    record_digest TEXT NOT NULL UNIQUE,
                    UNIQUE(improvement_id, proposal_digest)
                );
                CREATE INDEX IF NOT EXISTS idx_wsri_records_improvement ON wsri_records(improvement_id, sequence);
            """)
            connection.execute("INSERT OR IGNORE INTO wsri_metadata(name,value) VALUES('schema',?)", (LEDGER_SCHEMA,))
            row = connection.execute("SELECT value FROM wsri_metadata WHERE name='schema'").fetchone()
            if row is None or row["value"] != LEDGER_SCHEMA:
                raise ImprovementLedgerError("WS-RI ledger schema mismatch")
        finally:
            connection.close()

    def append(self, proposal: ImprovementProposal, *, actor: str, recorded_utc: str, reason: str) -> ImprovementLedgerAppendResult:
        if not actor.strip() or not recorded_utc.strip() or not reason.strip():
            raise ImprovementLedgerError("actor, recorded_utc, and reason are required")
        pdigest = proposal_digest(proposal)
        pjson = json.dumps(proposal.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            duplicate = connection.execute("SELECT * FROM wsri_records WHERE improvement_id=? AND proposal_digest=?", (proposal.improvement_id, pdigest)).fetchone()
            if duplicate is not None:
                connection.commit()
                return ImprovementLedgerAppendResult("DEDUPLICATED", _row_to_record(duplicate))
            count = connection.execute("SELECT COUNT(*) FROM wsri_records").fetchone()[0]
            if count >= MAX_LEDGER_RECORDS:
                raise ImprovementLedgerError("WS-RI ledger capacity reached")
            global_prior = connection.execute("SELECT * FROM wsri_records ORDER BY sequence DESC LIMIT 1").fetchone()
            item_prior = connection.execute("SELECT * FROM wsri_records WHERE improvement_id=? ORDER BY sequence DESC LIMIT 1", (proposal.improvement_id,)).fetchone()
            prior_state = None if item_prior is None else ImprovementState(item_prior["state"])
            if not _transition_allowed(prior_state, proposal.state):
                before = "NONE" if prior_state is None else prior_state.value
                raise ImprovementLedgerError(f"invalid WS-RI transition {before}->{proposal.state.value}")
            previous_digest = None if global_prior is None else global_prior["record_digest"]
            item_digest = None if item_prior is None else item_prior["record_digest"]
            material = _record_material(
                improvement_id=proposal.improvement_id, state=proposal.state.value, proposal_digest=pdigest,
                previous_record_digest=previous_digest, prior_improvement_digest=item_digest,
                actor=actor.strip(), recorded_utc=recorded_utc.strip(), reason=reason.strip(),
            )
            rdigest = canonical_digest(material)
            connection.execute("""
                INSERT INTO wsri_records(improvement_id,state,proposal_digest,proposal_json,previous_record_digest,prior_improvement_digest,actor,recorded_utc,reason,record_digest)
                VALUES(?,?,?,?,?,?,?,?,?,?)
            """, (proposal.improvement_id, proposal.state.value, pdigest, pjson, previous_digest, item_digest, actor.strip(), recorded_utc.strip(), reason.strip(), rdigest))
            row = connection.execute("SELECT * FROM wsri_records WHERE record_digest=?", (rdigest,)).fetchone()
            connection.commit()
            assert row is not None
            return ImprovementLedgerAppendResult("STORED", _row_to_record(row))
        except Exception:
            if connection.in_transaction:
                connection.rollback()
            raise
        finally:
            connection.close()

    def records(self) -> list[ImprovementLedgerRecord]:
        connection = self._connect()
        try:
            return [_row_to_record(row) for row in connection.execute("SELECT * FROM wsri_records ORDER BY sequence").fetchall()]
        finally:
            connection.close()

    def latest(self, improvement_id: str) -> ImprovementLedgerRecord | None:
        connection = self._connect()
        try:
            row = connection.execute("SELECT * FROM wsri_records WHERE improvement_id=? ORDER BY sequence DESC LIMIT 1", (improvement_id,)).fetchone()
            return None if row is None else _row_to_record(row)
        finally:
            connection.close()

    def verify_chain(self) -> bool:
        previous = None
        prior_by_id: dict[str, ImprovementLedgerRecord] = {}
        for record in self.records():
            prior = prior_by_id.get(record.improvement_id)
            if record.previous_record_digest != previous:
                return False
            if record.prior_improvement_digest != (None if prior is None else prior.record_digest):
                return False
            try:
                proposal = record.proposal()
            except Exception:
                return False
            if proposal.improvement_id != record.improvement_id or proposal.state.value != record.state:
                return False
            prior_state = None if prior is None else ImprovementState(prior.state)
            if not _transition_allowed(prior_state, proposal.state):
                return False
            if proposal_digest(proposal) != record.proposal_digest:
                return False
            if canonical_digest(_record_material(record)) != record.record_digest:
                return False
            previous = record.record_digest
            prior_by_id[record.improvement_id] = record
        return True

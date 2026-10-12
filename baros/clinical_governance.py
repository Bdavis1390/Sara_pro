"""Fail-closed translational governance for BAROS research validation.

NON-CLINICAL. This module controls evidence-state transitions only. It does not
establish physical dose accuracy, clinical safety/effectiveness, regulatory
authorization, or permission for patient-care use.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import math
import sqlite3
from pathlib import Path
from typing import Iterable, Mapping, Sequence


GATES = ("G0", "G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8", "G9")
EXTERNAL_GATES = {"G5", "G6", "G7", "G8", "G9"}

REQUIRED_EVIDENCE: dict[str, frozenset[str]] = {
    "G0": frozenset({"requirements_traceability"}),
    "G1": frozenset({"component_verification"}),
    "G2": frozenset({"end_to_end_pipeline"}),
    "G3": frozenset({"independent_numerical_reference"}),
    "G4": frozenset({"dicom_rt_interoperability"}),
    "G5": frozenset({"external_tps_recalculation"}),
    "G6": frozenset({"measured_dose", "deliverability"}),
    "G7": frozenset({"held_out_retrospective"}),
    "G8": frozenset({"independent_replication", "peer_review"}),
    "G9": frozenset({"prospective_evidence", "regulatory_determination"}),
}


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _sha256(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _require_sha256(name: str, value: str) -> str:
    rendered = str(value).strip().lower()
    if len(rendered) != 64 or any(ch not in "0123456789abcdef" for ch in rendered):
        raise ValueError(f"{name} must be a 64-character lowercase SHA-256 hex digest")
    return rendered


def _parse_utc(value: str) -> datetime:
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include a timezone")
    return parsed.astimezone(timezone.utc)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class IntendedUseManifest:
    """Locked validation configuration for one BAROS translational campaign."""

    validation_id: str
    indication: str
    disease_stage_or_risk_group: str
    modality: str
    delivery_technique: str
    machine_class: str
    tps_name: str
    tps_version: str
    fractionation: str
    comparator_workflow: str
    planning_protocol: str
    operator_roles: tuple[str, ...]
    primary_endpoints: tuple[str, ...]
    secondary_endpoints: tuple[str, ...] = ()
    permitted_human_overrides: tuple[str, ...] = ()
    non_intended_uses: tuple[str, ...] = (
        "autonomous treatment decision",
        "bypass of commissioned TPS dose recalculation",
        "bypass of patient-specific QA",
    )

    def validate(self) -> None:
        required = {
            "validation_id": self.validation_id,
            "indication": self.indication,
            "disease_stage_or_risk_group": self.disease_stage_or_risk_group,
            "modality": self.modality,
            "delivery_technique": self.delivery_technique,
            "machine_class": self.machine_class,
            "tps_name": self.tps_name,
            "tps_version": self.tps_version,
            "fractionation": self.fractionation,
            "comparator_workflow": self.comparator_workflow,
            "planning_protocol": self.planning_protocol,
        }
        empty = [name for name, value in required.items() if not str(value).strip()]
        if empty:
            raise ValueError("intended-use fields must be non-empty: " + ", ".join(sorted(empty)))
        if not self.operator_roles:
            raise ValueError("operator_roles must be non-empty")
        if not self.primary_endpoints:
            raise ValueError("primary_endpoints must be non-empty")

    def digest(self) -> str:
        self.validate()
        return _sha256(asdict(self))


@dataclass(frozen=True)
class EvidenceEnvelope:
    """Evidence Bill of Materials (EBOM)-style BAROS validation envelope."""

    validation_id: str
    commit_sha: str
    intended_use_sha256: str
    protocol_sha256: str
    configuration_sha256: str
    evidence_kinds: tuple[str, ...]
    raw_artifact_sha256: tuple[str, ...]
    analysis_artifact_sha256: tuple[str, ...]
    environment_sha256: str
    source_custody: str
    uncertainty_statement: str
    deviations: tuple[str, ...] = ()
    unresolved_contradictions: tuple[str, ...] = ()
    independent_reviewer_role: str | None = None
    externally_controlled: bool = False
    human_authorized: bool = False
    patient_care_allowed: bool = False
    notes: tuple[str, ...] = ()

    def validate(self) -> None:
        if not self.validation_id.strip():
            raise ValueError("validation_id must be non-empty")
        if not self.commit_sha.strip():
            raise ValueError("commit_sha must be non-empty")
        _require_sha256("intended_use_sha256", self.intended_use_sha256)
        _require_sha256("protocol_sha256", self.protocol_sha256)
        _require_sha256("configuration_sha256", self.configuration_sha256)
        _require_sha256("environment_sha256", self.environment_sha256)
        for digest in (*self.raw_artifact_sha256, *self.analysis_artifact_sha256):
            _require_sha256("artifact digest", digest)
        if not self.source_custody.strip():
            raise ValueError("source_custody must be non-empty")
        if not self.uncertainty_statement.strip():
            raise ValueError("uncertainty_statement must be non-empty")
        if self.patient_care_allowed:
            raise ValueError("BAROS research evidence envelopes cannot authorize patient care")

    def digest(self) -> str:
        self.validate()
        return _sha256(asdict(self))


@dataclass(frozen=True)
class EvidenceAssessment:
    target_gate: str
    promotable: bool
    missing_evidence_kinds: tuple[str, ...]
    blockers: tuple[str, ...]


def assess_evidence_for_gate(envelope: EvidenceEnvelope, target_gate: str) -> EvidenceAssessment:
    """Evaluate whether evidence is structurally eligible to support a gate.

    This is intentionally conservative. It evaluates evidence completeness and
    governance conditions, not the scientific truth of a result.
    """
    envelope.validate()
    if target_gate not in GATES:
        raise ValueError(f"unknown BAROS validation gate: {target_gate}")

    present = frozenset(item.strip() for item in envelope.evidence_kinds if item.strip())
    missing = tuple(sorted(REQUIRED_EVIDENCE[target_gate] - present))
    blockers: list[str] = []

    if envelope.unresolved_contradictions:
        blockers.append("unresolved contradictions require quarantine")
    if envelope.deviations:
        blockers.append("unresolved protocol deviations block promotion")
    if not envelope.raw_artifact_sha256:
        blockers.append("raw evidence artifacts are required")
    if not envelope.analysis_artifact_sha256:
        blockers.append("analysis artifacts are required")
    if target_gate in EXTERNAL_GATES:
        if not envelope.externally_controlled:
            blockers.append("external gate requires partner-controlled evidence")
        if not (envelope.independent_reviewer_role or "").strip():
            blockers.append("external gate requires an independent reviewer role")
    if target_gate in {"G7", "G8", "G9"} and not envelope.human_authorized:
        blockers.append("clinical/external progression requires explicit human authorization")
    if envelope.patient_care_allowed:
        blockers.append("research envelope cannot authorize patient care")

    return EvidenceAssessment(
        target_gate=target_gate,
        promotable=not missing and not blockers,
        missing_evidence_kinds=missing,
        blockers=tuple(blockers),
    )


@dataclass(frozen=True)
class GateTransitionRequest:
    """Exact-effect request for one adjacent BAROS validation-state transition."""

    validation_id: str
    from_gate: str
    to_gate: str
    expected_epoch: int
    commit_sha: str
    intended_use_sha256: str
    evidence_sha256: str
    target_environment: str
    nonce: str
    expires_at: str

    def validate(self) -> None:
        if self.from_gate not in GATES or self.to_gate not in GATES:
            raise ValueError("from_gate and to_gate must be known BAROS gates")
        if GATES.index(self.to_gate) != GATES.index(self.from_gate) + 1:
            raise ValueError("BAROS validation transitions must advance exactly one gate")
        if self.expected_epoch < 0:
            raise ValueError("expected_epoch must be non-negative")
        if not self.validation_id.strip() or not self.commit_sha.strip():
            raise ValueError("validation_id and commit_sha must be non-empty")
        _require_sha256("intended_use_sha256", self.intended_use_sha256)
        _require_sha256("evidence_sha256", self.evidence_sha256)
        if not self.target_environment.strip():
            raise ValueError("target_environment must be non-empty")
        if not self.nonce.strip():
            raise ValueError("nonce must be non-empty")
        _parse_utc(self.expires_at)

    def effect_payload(self) -> dict[str, object]:
        self.validate()
        return {
            "validation_id": self.validation_id,
            "from_gate": self.from_gate,
            "to_gate": self.to_gate,
            "expected_epoch": self.expected_epoch,
            "commit_sha": self.commit_sha,
            "intended_use_sha256": self.intended_use_sha256,
            "evidence_sha256": self.evidence_sha256,
            "target_environment": self.target_environment,
        }

    def effect_digest(self) -> str:
        return _sha256(self.effect_payload())

    def request_digest(self) -> str:
        self.validate()
        return _sha256(asdict(self))


@dataclass(frozen=True)
class GateAuthorization:
    """Human approval bound to the exact transition effect and request."""

    validation_id: str
    approver_id: str
    approver_role: str
    request_sha256: str
    effect_sha256: str
    issued_at: str
    expires_at: str
    authorization_id: str

    def validate(self) -> None:
        if not self.validation_id.strip():
            raise ValueError("validation_id must be non-empty")
        if not self.approver_id.strip() or not self.approver_role.strip():
            raise ValueError("approver identity and role are required")
        _require_sha256("request_sha256", self.request_sha256)
        _require_sha256("effect_sha256", self.effect_sha256)
        issued = _parse_utc(self.issued_at)
        expires = _parse_utc(self.expires_at)
        if expires <= issued:
            raise ValueError("authorization must expire after issuance")
        if not self.authorization_id.strip():
            raise ValueError("authorization_id must be non-empty")


def authorize_request(
    request: GateTransitionRequest,
    *,
    approver_id: str,
    approver_role: str,
    authorization_id: str,
    issued_at: str,
    expires_at: str | None = None,
) -> GateAuthorization:
    request.validate()
    auth = GateAuthorization(
        validation_id=request.validation_id,
        approver_id=approver_id,
        approver_role=approver_role,
        request_sha256=request.request_digest(),
        effect_sha256=request.effect_digest(),
        issued_at=issued_at,
        expires_at=expires_at or request.expires_at,
        authorization_id=authorization_id,
    )
    auth.validate()
    return auth


class SQLiteGateLedger:
    """Durable replay/epoch guard for BAROS validation progression.

    The ledger records current gate/epoch and consumed nonces/authorization IDs.
    It does not replace institutional authorization, IRB review, QMP sign-off,
    regulatory review, or an external cryptographic witness.
    """

    def __init__(self, path: str | Path):
        self.path = str(path)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10.0, isolation_level=None)
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA journal_mode=WAL")
        return connection

    def _initialize(self) -> None:
        with self._connect() as db:
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS validation_state (
                    validation_id TEXT PRIMARY KEY,
                    current_gate TEXT NOT NULL,
                    epoch INTEGER NOT NULL,
                    last_effect_sha256 TEXT
                )
                """
            )
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS consumed_authorizations (
                    validation_id TEXT NOT NULL,
                    nonce TEXT NOT NULL,
                    authorization_id TEXT NOT NULL,
                    request_sha256 TEXT NOT NULL,
                    effect_sha256 TEXT NOT NULL,
                    consumed_at TEXT NOT NULL,
                    PRIMARY KEY (validation_id, nonce),
                    UNIQUE (validation_id, authorization_id)
                )
                """
            )

    def state(self, validation_id: str) -> tuple[str, int, str | None]:
        with self._connect() as db:
            row = db.execute(
                "SELECT current_gate, epoch, last_effect_sha256 FROM validation_state WHERE validation_id=?",
                (validation_id,),
            ).fetchone()
        if row is None:
            return ("G0", 0, None)
        return (str(row[0]), int(row[1]), None if row[2] is None else str(row[2]))

    def apply(
        self,
        *,
        request: GateTransitionRequest,
        authorization: GateAuthorization,
        envelope: EvidenceEnvelope,
        now: str | None = None,
    ) -> tuple[str, int]:
        """Atomically apply an authorized adjacent transition or fail closed."""
        request.validate()
        authorization.validate()
        envelope.validate()

        current_time = _parse_utc(now) if now is not None else _now_utc()
        if current_time >= _parse_utc(request.expires_at):
            raise ValueError("transition request is expired")
        if current_time >= _parse_utc(authorization.expires_at):
            raise ValueError("authorization is expired")
        if authorization.validation_id != request.validation_id:
            raise ValueError("authorization validation_id mismatch")
        if envelope.validation_id != request.validation_id:
            raise ValueError("evidence validation_id mismatch")
        if envelope.commit_sha != request.commit_sha:
            raise ValueError("evidence commit does not match authorized commit")
        if envelope.intended_use_sha256 != request.intended_use_sha256:
            raise ValueError("evidence intended use does not match authorized intended use")
        if envelope.digest() != request.evidence_sha256:
            raise ValueError("evidence digest does not match transition request")
        if authorization.request_sha256 != request.request_digest():
            raise ValueError("authorization does not bind the exact request")
        if authorization.effect_sha256 != request.effect_digest():
            raise ValueError("authorization does not bind the exact activation effect")

        assessment = assess_evidence_for_gate(envelope, request.to_gate)
        if not assessment.promotable:
            detail = "; ".join((*assessment.missing_evidence_kinds, *assessment.blockers))
            raise ValueError("evidence is not promotable for target gate: " + detail)

        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                row = db.execute(
                    "SELECT current_gate, epoch FROM validation_state WHERE validation_id=?",
                    (request.validation_id,),
                ).fetchone()
                if row is None:
                    current_gate, epoch = "G0", 0
                else:
                    current_gate, epoch = str(row[0]), int(row[1])

                if current_gate != request.from_gate:
                    raise ValueError(
                        f"stale from_gate: ledger={current_gate}, request={request.from_gate}"
                    )
                if epoch != request.expected_epoch:
                    raise ValueError(
                        f"stale epoch: ledger={epoch}, request={request.expected_epoch}"
                    )

                existing = db.execute(
                    "SELECT 1 FROM consumed_authorizations WHERE validation_id=? AND (nonce=? OR authorization_id=?)",
                    (request.validation_id, request.nonce, authorization.authorization_id),
                ).fetchone()
                if existing is not None:
                    raise ValueError("authorization nonce or authorization_id has already been consumed")

                new_epoch = epoch + 1
                db.execute(
                    """
                    INSERT INTO validation_state(validation_id,current_gate,epoch,last_effect_sha256)
                    VALUES(?,?,?,?)
                    ON CONFLICT(validation_id) DO UPDATE SET
                        current_gate=excluded.current_gate,
                        epoch=excluded.epoch,
                        last_effect_sha256=excluded.last_effect_sha256
                    """,
                    (
                        request.validation_id,
                        request.to_gate,
                        new_epoch,
                        request.effect_digest(),
                    ),
                )
                db.execute(
                    """
                    INSERT INTO consumed_authorizations(
                        validation_id,nonce,authorization_id,request_sha256,
                        effect_sha256,consumed_at
                    ) VALUES(?,?,?,?,?,?)
                    """,
                    (
                        request.validation_id,
                        request.nonce,
                        authorization.authorization_id,
                        request.request_digest(),
                        request.effect_digest(),
                        current_time.isoformat(),
                    ),
                )
                db.execute("COMMIT")
                return request.to_gate, new_epoch
            except Exception:
                db.execute("ROLLBACK")
                raise

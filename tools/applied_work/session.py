from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any

try:
    from .accounting import (
        AppliedWorkLedger,
        CrossKindModel,
        EvidenceClass,
        WorkAccountingError,
        WorkQuantity,
    )
except ImportError:  # pragma: no cover - direct test execution from this directory
    from accounting import (
        AppliedWorkLedger,
        CrossKindModel,
        EvidenceClass,
        WorkAccountingError,
        WorkQuantity,
    )


SESSION_SCHEMA = "WS-APPLIED-WORK-SESSION-V1"
EVENT_SCHEMA = "WS-APPLIED-WORK-EVENT-V1"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
_STRONG_EVIDENCE = frozenset({EvidenceClass.MEASURED, EvidenceClass.BENCHMARKED})


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _parse_time(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise WorkAccountingError("session timestamps must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise WorkAccountingError("session timestamps must be timezone-aware")
    return parsed


def _quantity_payload(quantity: WorkQuantity) -> dict[str, Any]:
    return {
        "quantity_id": quantity.quantity_id,
        "kind": quantity.kind.value,
        "value": str(quantity.value),
        "unit": quantity.unit,
        "basis": quantity.basis,
        "provenance": quantity.provenance,
        "evidence_class": quantity.evidence_class.value,
        "uncertainty": None if quantity.uncertainty is None else str(quantity.uncertainty),
        "scope": quantity.scope,
        "time_window": quantity.time_window,
    }


def _model_payload(model: CrossKindModel) -> dict[str, Any]:
    return {
        "model_id": model.model_id,
        "input_kind": model.input_kind.value,
        "input_unit": model.input_unit,
        "input_basis": model.input_basis,
        "output_kind": model.output_kind.value,
        "output_unit": model.output_unit,
        "output_basis": model.output_basis,
        "output_per_input": str(model.output_per_input),
        "provenance": model.provenance,
        "evidence_class": model.evidence_class.value,
        "assumptions": list(model.assumptions),
        "conditions": list(model.conditions),
        "model_version": model.model_version,
        "uncertainty_fraction": (
            None if model.uncertainty_fraction is None else str(model.uncertainty_fraction)
        ),
    }


@dataclass(frozen=True)
class EvidenceArtifact:
    evidence_id: str
    sha256: str
    uri: str
    captured_at: str
    collector: str
    media_type: str = "application/octet-stream"

    def __post_init__(self) -> None:
        if not self.evidence_id.strip():
            raise WorkAccountingError("evidence_id is required")
        if not _SHA256_RE.fullmatch(self.sha256):
            raise WorkAccountingError("evidence artifact sha256 must be 64 lowercase hex characters")
        if not self.uri.strip() or not self.collector.strip():
            raise WorkAccountingError("evidence artifact uri and collector are required")
        _parse_time(self.captured_at)

    def payload(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class SessionEvent:
    sequence: int
    event_type: str
    subject_id: str
    payload: dict[str, Any]
    previous_event_sha256: str | None
    payload_sha256: str
    event_sha256: str

    @classmethod
    def create(
        cls,
        *,
        sequence: int,
        event_type: str,
        subject_id: str,
        payload: dict[str, Any],
        previous_event_sha256: str | None,
    ) -> "SessionEvent":
        if sequence < 1:
            raise WorkAccountingError("event sequence must begin at 1")
        if not event_type.strip() or not subject_id.strip():
            raise WorkAccountingError("event_type and subject_id are required")
        payload_sha256 = _sha256(payload)
        envelope = {
            "schema": EVENT_SCHEMA,
            "sequence": sequence,
            "event_type": event_type,
            "subject_id": subject_id,
            "payload_sha256": payload_sha256,
            "previous_event_sha256": previous_event_sha256,
        }
        event_sha256 = _sha256(envelope)
        return cls(
            sequence=sequence,
            event_type=event_type,
            subject_id=subject_id,
            payload=payload,
            previous_event_sha256=previous_event_sha256,
            payload_sha256=payload_sha256,
            event_sha256=event_sha256,
        )

    def payload_record(self) -> dict[str, Any]:
        return {
            "schema": EVENT_SCHEMA,
            "sequence": self.sequence,
            "event_type": self.event_type,
            "subject_id": self.subject_id,
            "payload": self.payload,
            "previous_event_sha256": self.previous_event_sha256,
            "payload_sha256": self.payload_sha256,
            "event_sha256": self.event_sha256,
        }


@dataclass
class AppliedWorkSession:
    session_id: str
    subject: str
    source_commit: str
    build_identity: str
    collector: str
    started_at: str
    ledger: AppliedWorkLedger = field(default_factory=AppliedWorkLedger)
    evidence: dict[str, EvidenceArtifact] = field(default_factory=dict)
    events: list[SessionEvent] = field(default_factory=list)
    ended_at: str | None = None
    seal_digest: str | None = None

    def __post_init__(self) -> None:
        if not self.session_id.strip() or not self.subject.strip():
            raise WorkAccountingError("session_id and subject are required")
        if not _COMMIT_RE.fullmatch(self.source_commit):
            raise WorkAccountingError("source_commit must be a full 40-character lowercase Git SHA")
        if not self.build_identity.strip() or not self.collector.strip():
            raise WorkAccountingError("build_identity and collector are required")
        _parse_time(self.started_at)

    @property
    def sealed(self) -> bool:
        return self.seal_digest is not None

    def _ensure_open(self) -> None:
        if self.sealed:
            raise WorkAccountingError("sealed work sessions are immutable")

    def _append(self, event_type: str, subject_id: str, payload: dict[str, Any]) -> SessionEvent:
        self._ensure_open()
        previous = self.events[-1].event_sha256 if self.events else None
        event = SessionEvent.create(
            sequence=len(self.events) + 1,
            event_type=event_type,
            subject_id=subject_id,
            payload=payload,
            previous_event_sha256=previous,
        )
        self.events.append(event)
        return event

    def add_evidence(self, artifact: EvidenceArtifact) -> None:
        self._ensure_open()
        if artifact.evidence_id in self.evidence:
            raise WorkAccountingError(f"duplicate evidence_id: {artifact.evidence_id}")
        self.evidence[artifact.evidence_id] = artifact
        self._append("EVIDENCE_RECORDED", artifact.evidence_id, artifact.payload())

    def _validated_evidence_ids(
        self,
        evidence_class: EvidenceClass,
        evidence_ids: tuple[str, ...],
    ) -> tuple[str, ...]:
        if len(set(evidence_ids)) != len(evidence_ids):
            raise WorkAccountingError("evidence references cannot contain duplicates")
        missing = [item for item in evidence_ids if item not in self.evidence]
        if missing:
            raise WorkAccountingError("unknown evidence reference: " + ", ".join(missing))
        if evidence_class in _STRONG_EVIDENCE and not evidence_ids:
            raise WorkAccountingError(
                f"{evidence_class.value} quantities/models require at least one hashed evidence artifact"
            )
        return evidence_ids

    def add_quantity(
        self,
        quantity: WorkQuantity,
        *,
        evidence_ids: tuple[str, ...] = (),
    ) -> None:
        self._ensure_open()
        refs = self._validated_evidence_ids(quantity.evidence_class, evidence_ids)
        self.ledger.add_quantity(quantity)
        self._append(
            "QUANTITY_RECORDED",
            quantity.quantity_id,
            {
                "quantity": _quantity_payload(quantity),
                "evidence_ids": list(refs),
            },
        )

    def add_model(
        self,
        model: CrossKindModel,
        *,
        evidence_ids: tuple[str, ...] = (),
    ) -> None:
        self._ensure_open()
        refs = self._validated_evidence_ids(model.evidence_class, evidence_ids)
        self.ledger.add_model(model)
        self._append(
            "MODEL_RECORDED",
            model.model_id,
            {
                "model": _model_payload(model),
                "evidence_ids": list(refs),
            },
        )

    def derive(self, input_quantity_id: str, model_id: str, *, output_id: str) -> WorkQuantity:
        self._ensure_open()
        result = self.ledger.derive(input_quantity_id, model_id, output_id=output_id)
        self._append(
            "QUANTITY_DERIVED",
            output_id,
            {
                "quantity": _quantity_payload(result),
                "input_quantity_id": input_quantity_id,
                "model_id": model_id,
            },
        )
        return result

    def seal(self, *, ended_at: str) -> str:
        self._ensure_open()
        if not self.events:
            raise WorkAccountingError("cannot seal an empty work session")
        start = _parse_time(self.started_at)
        end = _parse_time(ended_at)
        if end < start:
            raise WorkAccountingError("ended_at cannot precede started_at")
        self.ended_at = ended_at
        body = {
            "schema": SESSION_SCHEMA,
            "session_id": self.session_id,
            "subject": self.subject,
            "source_commit": self.source_commit,
            "build_identity": self.build_identity,
            "collector": self.collector,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "event_count": len(self.events),
            "event_tip_sha256": self.events[-1].event_sha256,
            "evidence_count": len(self.evidence),
            "quantity_count": len(self.ledger.quantities),
            "model_count": len(self.ledger.models),
            "ledger_vector": self.ledger.vector(),
        }
        self.seal_digest = _sha256(body)
        return self.seal_digest

    def manifest(self) -> dict[str, Any]:
        if not self.sealed or self.ended_at is None:
            raise WorkAccountingError("session must be sealed before export")
        return {
            "schema": SESSION_SCHEMA,
            "session_id": self.session_id,
            "subject": self.subject,
            "source_commit": self.source_commit,
            "build_identity": self.build_identity,
            "collector": self.collector,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "evidence": {
                key: value.payload() for key, value in sorted(self.evidence.items())
            },
            "events": [event.payload_record() for event in self.events],
            "ledger_vector": self.ledger.vector(),
            "seal_digest": self.seal_digest,
            "claims_boundary": (
                "Internal tamper-evident measurement-session record only. The seal detects "
                "changes relative to a preserved seal digest but is not independently immutable "
                "until the manifest or seal digest is externally anchored."
            ),
        }


def verify_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    reasons: list[str] = []
    if manifest.get("schema") != SESSION_SCHEMA:
        reasons.append("unsupported session schema")

    source_commit = manifest.get("source_commit")
    if not isinstance(source_commit, str) or not _COMMIT_RE.fullmatch(source_commit):
        reasons.append("source_commit is not a full lowercase Git SHA")

    try:
        start = _parse_time(str(manifest.get("started_at", "")))
        end = _parse_time(str(manifest.get("ended_at", "")))
        if end < start:
            reasons.append("ended_at precedes started_at")
    except WorkAccountingError as exc:
        reasons.append(str(exc))

    evidence = manifest.get("evidence")
    if not isinstance(evidence, dict):
        evidence = {}
        reasons.append("evidence map is malformed")
    else:
        for evidence_id, artifact in evidence.items():
            if not isinstance(artifact, dict):
                reasons.append(f"evidence {evidence_id} is malformed")
                continue
            if artifact.get("evidence_id") != evidence_id:
                reasons.append(f"evidence key mismatch: {evidence_id}")
            digest = artifact.get("sha256")
            if not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest):
                reasons.append(f"evidence {evidence_id} has invalid sha256")
            try:
                _parse_time(str(artifact.get("captured_at", "")))
            except WorkAccountingError:
                reasons.append(f"evidence {evidence_id} has invalid captured_at")

    events = manifest.get("events")
    if not isinstance(events, list) or not events:
        events = []
        reasons.append("event list is empty or malformed")

    previous: str | None = None
    for index, event in enumerate(events, start=1):
        if not isinstance(event, dict):
            reasons.append(f"event {index} is malformed")
            continue
        if event.get("schema") != EVENT_SCHEMA:
            reasons.append(f"event {index} schema mismatch")
        if event.get("sequence") != index:
            reasons.append(f"event sequence mismatch at position {index}")
        if event.get("previous_event_sha256") != previous:
            reasons.append(f"event predecessor mismatch at sequence {index}")

        payload = event.get("payload")
        if not isinstance(payload, dict):
            reasons.append(f"event {index} payload is malformed")
            payload = {}
        expected_payload_sha = _sha256(payload)
        if event.get("payload_sha256") != expected_payload_sha:
            reasons.append(f"event payload hash mismatch at sequence {index}")

        envelope = {
            "schema": EVENT_SCHEMA,
            "sequence": event.get("sequence"),
            "event_type": event.get("event_type"),
            "subject_id": event.get("subject_id"),
            "payload_sha256": expected_payload_sha,
            "previous_event_sha256": event.get("previous_event_sha256"),
        }
        expected_event_sha = _sha256(envelope)
        if event.get("event_sha256") != expected_event_sha:
            reasons.append(f"event hash mismatch at sequence {index}")
        previous = event.get("event_sha256") if isinstance(event.get("event_sha256"), str) else None

        if event.get("event_type") in {"QUANTITY_RECORDED", "MODEL_RECORDED"}:
            body_key = "quantity" if event.get("event_type") == "QUANTITY_RECORDED" else "model"
            body = payload.get(body_key)
            refs = payload.get("evidence_ids")
            if not isinstance(body, dict) or not isinstance(refs, list):
                reasons.append(f"event {index} measurement/model payload is malformed")
                continue
            evidence_class = body.get("evidence_class")
            if evidence_class in {item.value for item in _STRONG_EVIDENCE} and not refs:
                reasons.append(
                    f"event {index} promotes {evidence_class} without hashed evidence references"
                )
            for ref in refs:
                if ref not in evidence:
                    reasons.append(f"event {index} references unknown evidence {ref}")

    ledger_vector = manifest.get("ledger_vector")
    if not isinstance(ledger_vector, dict):
        reasons.append("ledger_vector is malformed")
        ledger_vector = {}

    seal_body = {
        "schema": SESSION_SCHEMA,
        "session_id": manifest.get("session_id"),
        "subject": manifest.get("subject"),
        "source_commit": manifest.get("source_commit"),
        "build_identity": manifest.get("build_identity"),
        "collector": manifest.get("collector"),
        "started_at": manifest.get("started_at"),
        "ended_at": manifest.get("ended_at"),
        "event_count": len(events),
        "event_tip_sha256": previous,
        "evidence_count": len(evidence),
        "quantity_count": len(ledger_vector),
        "model_count": sum(
            1 for event in events if isinstance(event, dict) and event.get("event_type") == "MODEL_RECORDED"
        ),
        "ledger_vector": ledger_vector,
    }
    recomputed_seal = _sha256(seal_body)
    if manifest.get("seal_digest") != recomputed_seal:
        reasons.append("session seal digest mismatch")

    return {
        "schema": "WS-APPLIED-WORK-SESSION-VERIFY-V1",
        "status": "PASS" if not reasons else "FAIL",
        "ok": not reasons,
        "reasons": reasons,
        "event_count": len(events),
        "evidence_count": len(evidence),
        "recomputed_seal_digest": recomputed_seal,
        "claims_boundary": (
            "Verification proves internal hash-chain/seal consistency only. External anchoring "
            "is required for independent immutability/time custody."
        ),
    }

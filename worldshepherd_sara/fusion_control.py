"""Worldshepherd fusion-control demonstrator core.

This module is intentionally simulator-only.  It contains no hardware driver,
EPICS client, coil command path, gas command path, heating command path, or
machine-control transport.  It is designed to exercise the Worldshepherd
pattern:

    measurement -> validation -> state estimate -> control proposal
    -> deterministic PRIME-style gate -> audit/replay record

The safety gate is deterministic and independent of the proposal generator.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
import math
import time
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


@dataclass(frozen=True)
class SensorSample:
    timestamp: float
    shot_id: str
    diagnostic: str
    value: float
    unit: str
    uncertainty: float
    valid: bool
    quality: str
    provenance: str

    def validate(self) -> Tuple[bool, str]:
        if not self.valid:
            return False, "sensor_invalid"
        if not math.isfinite(self.timestamp):
            return False, "timestamp_not_finite"
        if not math.isfinite(self.value):
            return False, "value_not_finite"
        if not math.isfinite(self.uncertainty) or self.uncertainty < 0:
            return False, "uncertainty_invalid"
        if not self.diagnostic.strip():
            return False, "diagnostic_missing"
        if not self.unit.strip():
            return False, "unit_missing"
        if not self.quality.strip():
            return False, "quality_missing"
        if not self.provenance.strip():
            return False, "provenance_missing"
        return True, "ok"


@dataclass(frozen=True)
class PlasmaStateEstimate:
    timestamp: float
    shot_id: str
    vertical_displacement_m: float
    confidence: float
    estimator_id: str
    source_diagnostics: Tuple[str, ...]

    def validate(self) -> Tuple[bool, str]:
        if not math.isfinite(self.vertical_displacement_m):
            return False, "state_not_finite"
        if not (0.0 <= self.confidence <= 1.0):
            return False, "confidence_out_of_range"
        if not self.estimator_id.strip():
            return False, "estimator_id_missing"
        if not self.source_diagnostics:
            return False, "source_diagnostics_missing"
        return True, "ok"


@dataclass(frozen=True)
class ControlProposal:
    timestamp: float
    shot_id: str
    actuator: str
    requested_value: float
    unit: str
    model_id: str
    confidence: float
    rationale: str


@dataclass(frozen=True)
class SafetyEnvelope:
    actuator: str
    minimum: float
    maximum: float
    max_abs_slew_per_s: float
    unit: str
    minimum_confidence: float = 0.80

    def validate(self) -> Tuple[bool, str]:
        if not self.actuator.strip():
            return False, "actuator_missing"
        if not all(math.isfinite(v) for v in (self.minimum, self.maximum, self.max_abs_slew_per_s)):
            return False, "envelope_not_finite"
        if self.minimum >= self.maximum:
            return False, "envelope_range_invalid"
        if self.max_abs_slew_per_s <= 0:
            return False, "slew_limit_invalid"
        if not (0.0 <= self.minimum_confidence <= 1.0):
            return False, "minimum_confidence_invalid"
        return True, "ok"


@dataclass(frozen=True)
class GateDecision:
    timestamp: float
    shot_id: str
    actuator: str
    accepted: bool
    reason: str
    requested_value: float
    applied_value: Optional[float]
    unit: str
    proposal_model_id: str
    proposal_confidence: float


@dataclass
class AuditRecord:
    sequence: int
    event: str
    timestamp: float
    payload: Dict[str, Any]
    previous_hash: str
    record_hash: str = ""

    def seal(self) -> "AuditRecord":
        material = {
            "sequence": self.sequence,
            "event": self.event,
            "timestamp": self.timestamp,
            "payload": self.payload,
            "previous_hash": self.previous_hash,
        }
        encoded = json.dumps(material, sort_keys=True, separators=(",", ":")).encode("utf-8")
        self.record_hash = hashlib.sha256(encoded).hexdigest()
        return self


class FusionAuditLedger:
    """Minimal append-only, hash-chained event ledger for replay demonstrations."""

    def __init__(self) -> None:
        self._records: List[AuditRecord] = []

    @property
    def records(self) -> Sequence[AuditRecord]:
        return tuple(self._records)

    def append(self, event: str, payload: Mapping[str, Any], timestamp: Optional[float] = None) -> AuditRecord:
        ts = time.time() if timestamp is None else float(timestamp)
        previous_hash = self._records[-1].record_hash if self._records else "GENESIS"
        record = AuditRecord(
            sequence=len(self._records),
            event=event,
            timestamp=ts,
            payload=dict(payload),
            previous_hash=previous_hash,
        ).seal()
        self._records.append(record)
        return record

    def verify(self) -> Tuple[bool, str]:
        previous_hash = "GENESIS"
        for index, record in enumerate(self._records):
            if record.sequence != index:
                return False, f"sequence_mismatch:{index}"
            if record.previous_hash != previous_hash:
                return False, f"previous_hash_mismatch:{index}"
            expected = AuditRecord(
                sequence=record.sequence,
                event=record.event,
                timestamp=record.timestamp,
                payload=dict(record.payload),
                previous_hash=record.previous_hash,
            ).seal().record_hash
            if record.record_hash != expected:
                return False, f"record_hash_mismatch:{index}"
            previous_hash = record.record_hash
        return True, "ok"

    def to_jsonl(self) -> str:
        return "\n".join(json.dumps(asdict(r), sort_keys=True) for r in self._records)


class PrimeSafetyGate:
    """Deterministic command gate for abstract virtual actuators.

    The gate does not know how a proposal was generated.  It only evaluates
    whether the proposal satisfies explicit, reviewable constraints.
    """

    def __init__(self, envelopes: Iterable[SafetyEnvelope], ledger: Optional[FusionAuditLedger] = None) -> None:
        self.envelopes: Dict[str, SafetyEnvelope] = {}
        for envelope in envelopes:
            ok, reason = envelope.validate()
            if not ok:
                raise ValueError(f"invalid safety envelope for {envelope.actuator}: {reason}")
            self.envelopes[envelope.actuator] = envelope
        self.ledger = ledger or FusionAuditLedger()
        self._last_applied: Dict[str, Tuple[float, float]] = {}

    def evaluate(self, proposal: ControlProposal) -> GateDecision:
        envelope = self.envelopes.get(proposal.actuator)
        reason = "accepted"
        accepted = True
        applied_value: Optional[float] = proposal.requested_value

        if envelope is None:
            accepted = False
            reason = "actuator_not_allowlisted"
        elif proposal.unit != envelope.unit:
            accepted = False
            reason = "unit_mismatch"
        elif not proposal.model_id.strip():
            accepted = False
            reason = "model_id_missing"
        elif not math.isfinite(proposal.requested_value):
            accepted = False
            reason = "requested_value_not_finite"
        elif not (0.0 <= proposal.confidence <= 1.0):
            accepted = False
            reason = "proposal_confidence_invalid"
        elif proposal.confidence < envelope.minimum_confidence:
            accepted = False
            reason = "proposal_confidence_below_threshold"
        elif not (envelope.minimum <= proposal.requested_value <= envelope.maximum):
            accepted = False
            reason = "requested_value_out_of_bounds"
        else:
            previous = self._last_applied.get(proposal.actuator)
            if previous is not None:
                previous_ts, previous_value = previous
                dt = proposal.timestamp - previous_ts
                if dt <= 0:
                    accepted = False
                    reason = "non_monotonic_command_time"
                else:
                    slew = abs(proposal.requested_value - previous_value) / dt
                    if slew > envelope.max_abs_slew_per_s:
                        accepted = False
                        reason = "slew_limit_exceeded"

        if not accepted:
            applied_value = None
        else:
            self._last_applied[proposal.actuator] = (proposal.timestamp, proposal.requested_value)

        decision = GateDecision(
            timestamp=proposal.timestamp,
            shot_id=proposal.shot_id,
            actuator=proposal.actuator,
            accepted=accepted,
            reason=reason,
            requested_value=proposal.requested_value,
            applied_value=applied_value,
            unit=proposal.unit,
            proposal_model_id=proposal.model_id,
            proposal_confidence=proposal.confidence,
        )
        self.ledger.append("fusion_gate_decision", asdict(decision), timestamp=proposal.timestamp)
        return decision


class DifferentialOpticalEstimator:
    """Simple differential-emission estimator for simulator/replay use.

    It is not a validated plasma-physics estimator.  It exists to exercise the
    data contract, confidence handling, fallback logic, and audit trail.
    """

    def __init__(self, gain_m_per_normalized_difference: float = 0.01, estimator_id: str = "ws-optical-diff-v0.1") -> None:
        self.gain = float(gain_m_per_normalized_difference)
        self.estimator_id = estimator_id

    def estimate(self, upper: SensorSample, lower: SensorSample) -> PlasmaStateEstimate:
        upper_ok, upper_reason = upper.validate()
        lower_ok, lower_reason = lower.validate()
        if not upper_ok:
            raise ValueError(f"upper sample invalid: {upper_reason}")
        if not lower_ok:
            raise ValueError(f"lower sample invalid: {lower_reason}")
        if upper.unit != lower.unit:
            raise ValueError("optical sample unit mismatch")
        if upper.shot_id != lower.shot_id:
            raise ValueError("shot mismatch")
        if upper.diagnostic == lower.diagnostic:
            raise ValueError("optical diagnostic identity collision")

        denominator = abs(upper.value) + abs(lower.value)
        if denominator <= 0:
            raise ValueError("optical differential denominator is zero")

        normalized_difference = (upper.value - lower.value) / denominator
        displacement = self.gain * normalized_difference

        relative_uncertainty = min(
            1.0,
            (upper.uncertainty + lower.uncertainty) / max(denominator, 1e-12),
        )
        confidence = max(0.0, min(1.0, 1.0 - relative_uncertainty))

        return PlasmaStateEstimate(
            timestamp=max(upper.timestamp, lower.timestamp),
            shot_id=upper.shot_id,
            vertical_displacement_m=displacement,
            confidence=confidence,
            estimator_id=self.estimator_id,
            source_diagnostics=(upper.diagnostic, lower.diagnostic),
        )


class ProportionalVirtualActuatorController:
    """Produces an abstract virtual-actuator proposal for simulation only."""

    def __init__(
        self,
        actuator: str = "virtual_vertical_balance",
        gain: float = -25.0,
        model_id: str = "ws-p-v0.1",
        unit: str = "arb",
    ) -> None:
        self.actuator = actuator
        self.gain = float(gain)
        self.model_id = model_id
        self.unit = unit

    def propose(self, state: PlasmaStateEstimate) -> ControlProposal:
        ok, reason = state.validate()
        if not ok:
            raise ValueError(f"invalid plasma state: {reason}")
        requested = self.gain * state.vertical_displacement_m
        return ControlProposal(
            timestamp=state.timestamp,
            shot_id=state.shot_id,
            actuator=self.actuator,
            requested_value=requested,
            unit=self.unit,
            model_id=self.model_id,
            confidence=state.confidence,
            rationale="proportional correction of simulated vertical displacement",
        )


@dataclass
class DemoResult:
    state: PlasmaStateEstimate
    proposal: ControlProposal
    decision: GateDecision
    ledger_ok: bool
    ledger_reason: str


def run_simulated_control_cycle(
    upper: SensorSample,
    lower: SensorSample,
    *,
    estimator: Optional[DifferentialOpticalEstimator] = None,
    controller: Optional[ProportionalVirtualActuatorController] = None,
    gate: Optional[PrimeSafetyGate] = None,
) -> DemoResult:
    ledger = gate.ledger if gate is not None else FusionAuditLedger()
    estimator = estimator or DifferentialOpticalEstimator()
    controller = controller or ProportionalVirtualActuatorController()
    gate = gate or PrimeSafetyGate(
        [
            SafetyEnvelope(
                actuator="virtual_vertical_balance",
                minimum=-1.0,
                maximum=1.0,
                max_abs_slew_per_s=10.0,
                unit="arb",
                minimum_confidence=0.80,
            )
        ],
        ledger=ledger,
    )

    ledger.append("fusion_sensor_sample", asdict(upper), timestamp=upper.timestamp)
    ledger.append("fusion_sensor_sample", asdict(lower), timestamp=lower.timestamp)

    state = estimator.estimate(upper, lower)
    ledger.append("fusion_state_estimate", asdict(state), timestamp=state.timestamp)

    proposal = controller.propose(state)
    ledger.append("fusion_control_proposal", asdict(proposal), timestamp=proposal.timestamp)

    decision = gate.evaluate(proposal)
    ledger_ok, ledger_reason = ledger.verify()
    return DemoResult(
        state=state,
        proposal=proposal,
        decision=decision,
        ledger_ok=ledger_ok,
        ledger_reason=ledger_reason,
    )

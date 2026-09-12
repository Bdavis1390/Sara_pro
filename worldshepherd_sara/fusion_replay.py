"""Deterministic replay engine for WS-FUSION-CTRL-001.

Replay consumes already-ingested SensorSample sequences.  It does not read from
or write to any machine-control interface.  Its job is to prove that a fixed
input stream plus fixed estimator/controller/gate configuration yields a stable
sequence of virtual decisions and a stable evidence fingerprint.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Iterable, List, Optional, Sequence, Tuple

from worldshepherd_sara.fusion_control import (
    DemoResult,
    DifferentialOpticalEstimator,
    FusionAuditLedger,
    PrimeSafetyGate,
    ProportionalVirtualActuatorController,
    SafetyEnvelope,
    SensorSample,
)


@dataclass(frozen=True)
class ReplayCycle:
    index: int
    timestamp: float
    accepted: bool
    reason: str
    requested_value: float
    applied_value: Optional[float]
    confidence: float


@dataclass(frozen=True)
class ReplayReport:
    shot_id: str
    cycle_count: int
    accepted_count: int
    rejected_count: int
    ledger_ok: bool
    ledger_reason: str
    fingerprint_sha256: str
    cycles: Tuple[ReplayCycle, ...]


def _canonical_fingerprint_payload(
    shot_id: str,
    cycles: Sequence[ReplayCycle],
    ledger: FusionAuditLedger,
) -> bytes:
    payload = {
        "shot_id": shot_id,
        "cycles": [asdict(cycle) for cycle in cycles],
        "ledger": [asdict(record) for record in ledger.records],
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


class FusionReplayRunner:
    """Replay paired diagnostic sequences through the simulator control chain."""

    def __init__(
        self,
        *,
        estimator: Optional[DifferentialOpticalEstimator] = None,
        controller: Optional[ProportionalVirtualActuatorController] = None,
        envelope: Optional[SafetyEnvelope] = None,
        maximum_pair_time_skew_s: float = 1e-6,
    ) -> None:
        self.estimator = estimator or DifferentialOpticalEstimator()
        self.controller = controller or ProportionalVirtualActuatorController()
        self.envelope = envelope or SafetyEnvelope(
            actuator="virtual_vertical_balance",
            minimum=-1.0,
            maximum=1.0,
            max_abs_slew_per_s=10.0,
            unit="arb",
            minimum_confidence=0.80,
        )
        self.maximum_pair_time_skew_s = float(maximum_pair_time_skew_s)
        if self.maximum_pair_time_skew_s < 0:
            raise ValueError("maximum_pair_time_skew_s must be non-negative")

    def replay(
        self,
        upper_samples: Sequence[SensorSample],
        lower_samples: Sequence[SensorSample],
    ) -> ReplayReport:
        if len(upper_samples) != len(lower_samples):
            raise ValueError("paired_series_length_mismatch")
        if not upper_samples:
            raise ValueError("paired_series_empty")

        shot_id = upper_samples[0].shot_id
        ledger = FusionAuditLedger()
        gate = PrimeSafetyGate([self.envelope], ledger=ledger)
        cycles: List[ReplayCycle] = []

        previous_timestamp: Optional[float] = None
        for index, (upper, lower) in enumerate(zip(upper_samples, lower_samples)):
            if upper.shot_id != shot_id or lower.shot_id != shot_id:
                raise ValueError(f"shot_id_mismatch:{index}")
            if abs(upper.timestamp - lower.timestamp) > self.maximum_pair_time_skew_s:
                raise ValueError(f"paired_timestamp_skew_exceeded:{index}")
            cycle_timestamp = max(upper.timestamp, lower.timestamp)
            if previous_timestamp is not None and cycle_timestamp <= previous_timestamp:
                raise ValueError(f"replay_time_not_strictly_increasing:{index}")
            previous_timestamp = cycle_timestamp

            ledger.append("fusion_sensor_sample", asdict(upper), timestamp=upper.timestamp)
            ledger.append("fusion_sensor_sample", asdict(lower), timestamp=lower.timestamp)

            state = self.estimator.estimate(upper, lower)
            ledger.append("fusion_state_estimate", asdict(state), timestamp=state.timestamp)

            proposal = self.controller.propose(state)
            ledger.append("fusion_control_proposal", asdict(proposal), timestamp=proposal.timestamp)
            decision = gate.evaluate(proposal)

            cycles.append(
                ReplayCycle(
                    index=index,
                    timestamp=decision.timestamp,
                    accepted=decision.accepted,
                    reason=decision.reason,
                    requested_value=decision.requested_value,
                    applied_value=decision.applied_value,
                    confidence=decision.proposal_confidence,
                )
            )

        ledger_ok, ledger_reason = ledger.verify()
        fingerprint = hashlib.sha256(
            _canonical_fingerprint_payload(shot_id, cycles, ledger)
        ).hexdigest()
        accepted_count = sum(1 for cycle in cycles if cycle.accepted)
        return ReplayReport(
            shot_id=shot_id,
            cycle_count=len(cycles),
            accepted_count=accepted_count,
            rejected_count=len(cycles) - accepted_count,
            ledger_ok=ledger_ok,
            ledger_reason=ledger_reason,
            fingerprint_sha256=fingerprint,
            cycles=tuple(cycles),
        )

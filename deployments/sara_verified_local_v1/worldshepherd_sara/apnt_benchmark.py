from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import statistics
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from .apnt_awareness import (
    APNTEvent,
    CLAIMS_BOUNDARY,
    IntegrityState,
    alert_for_event,
    recommendation_for_event,
    run_scenario,
)


BENCHMARK_ID = "WS-NP004-SYNTHETIC-THROUGHPUT-V0.1"
BENCHMARK_CLAIMS_BOUNDARY = (
    "SIMULATED_ONLY / SYNTHETIC SOFTWARE-PATH BENCHMARK / "
    "NOT END-TO-END LATENCY COMPLIANCE / INFORMATIONAL DECISION AID ONLY"
)
DEFAULT_SOURCE_COUNTS = (3, 5, 8)
DEFAULT_UPDATE_RATES_HZ = (1, 5, 10)
DEFAULT_DURATION_S = 30


@dataclass(frozen=True)
class BenchmarkCase:
    source_count: int
    update_rate_hz: int
    duration_s: int

    @property
    def expected_event_count(self) -> int:
        return self.source_count * self.update_rate_hz * self.duration_s

    @property
    def case_id(self) -> str:
        return (
            f"sources-{self.source_count}_rate-{self.update_rate_hz}hz_"
            f"duration-{self.duration_s}s"
        )


@dataclass(frozen=True)
class BenchmarkCaseResult:
    case_id: str
    source_count: int
    update_rate_hz: int
    duration_s: int
    event_count: int
    recommendation_count: int
    initial_awareness_p50_ms: float
    initial_awareness_p95_ms: float
    initial_awareness_p99_ms: float
    initial_awareness_max_ms: float
    full_replay_ms: float
    full_replay_events_per_second: float
    trace_complete: bool
    execution_attempted: bool
    final_integrity_state: str
    internal_software_path_p99_under_1000ms: bool


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha256(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _nearest_rank(values: list[float], percentile: float) -> float:
    if not values:
        raise ValueError("percentile requires at least one value")
    if not 0 < percentile <= 100:
        raise ValueError("percentile must be in (0, 100]")
    ordered = sorted(values)
    rank = max(1, math.ceil((percentile / 100.0) * len(ordered)))
    return ordered[rank - 1]


def benchmark_profile(
    *,
    duration_s: int = DEFAULT_DURATION_S,
    source_counts: Iterable[int] = DEFAULT_SOURCE_COUNTS,
    update_rates_hz: Iterable[int] = DEFAULT_UPDATE_RATES_HZ,
) -> tuple[BenchmarkCase, ...]:
    if duration_s < 1:
        raise ValueError("duration_s must be at least 1")
    cases: list[BenchmarkCase] = []
    for source_count in source_counts:
        if source_count < 1:
            raise ValueError("source_count must be at least 1")
        for update_rate_hz in update_rates_hz:
            if update_rate_hz < 1:
                raise ValueError("update_rate_hz must be at least 1")
            cases.append(
                BenchmarkCase(
                    source_count=source_count,
                    update_rate_hz=update_rate_hz,
                    duration_s=duration_s,
                )
            )
    return tuple(cases)


def _state_for_tick(tick: int, total_ticks: int) -> tuple[IntegrityState, str, str | None]:
    if tick == total_ticks - 1:
        return IntegrityState.RESTORED, "SYNTHETIC_TRUST_RESTORED", None
    phase = tick % 40
    if phase == 10:
        return (
            IntegrityState.DEGRADED,
            "SYNTHETIC_INTEGRITY_MARGIN_REDUCED",
            "COMPARE_ALTERNATE_SOURCE",
        )
    if phase == 20:
        return (
            IntegrityState.SUSPECT,
            "SYNTHETIC_SOURCE_REQUIRES_REVIEW",
            "REVIEW_PRIMARY_SOURCE",
        )
    if phase == 30:
        return (
            IntegrityState.DISAGREEMENT,
            "SYNTHETIC_SOURCE_DISAGREEMENT",
            "COMPARE_SOURCE_SET",
        )
    if phase == 35:
        return (
            IntegrityState.RECOVERING,
            "SYNTHETIC_RECOVERY_CROSS_CHECK",
            "RETAIN_ALTERNATE_CROSS_CHECK",
        )
    return IntegrityState.NOMINAL, "SYNTHETIC_NOMINAL_TRACK", None


def generate_synthetic_payloads(case: BenchmarkCase) -> list[dict[str, Any]]:
    total_ticks = case.duration_s * case.update_rate_hz
    payloads: list[dict[str, Any]] = []
    sequence = 1
    for tick in range(total_ticks):
        timestamp_s = tick / case.update_rate_hz
        state, reason_code, recovery_candidate = _state_for_tick(tick, total_ticks)
        for source_index in range(case.source_count):
            payloads.append(
                {
                    "sequence": sequence,
                    "timestamp_s": timestamp_s,
                    "source": f"SYNTHETIC_SOURCE_{source_index + 1:02d}",
                    "integrity_state": state.value,
                    "position": {
                        "x_m": 1000.0 + tick + source_index * 0.01,
                        "y_m": 2000.0 + tick * 0.5 + source_index * 0.01,
                        "z_m": 25.0,
                    },
                    "confidence": 0.98 if state in {IntegrityState.NOMINAL, IntegrityState.RESTORED} else 0.72,
                    "integrity_indicator": 0.97 if state in {IntegrityState.NOMINAL, IntegrityState.RESTORED} else 0.68,
                    "anomaly_code": None if state in {IntegrityState.NOMINAL, IntegrityState.RESTORED} else "SYNTHETIC_INTEGRITY_EVENT",
                    "reason_code": reason_code,
                    "recommended_recovery_candidate": recovery_candidate,
                }
            )
            sequence += 1
    return payloads


def workload_digest(cases: Iterable[BenchmarkCase]) -> str:
    payload = []
    for case in cases:
        generated = generate_synthetic_payloads(case)
        payload.append({"case": asdict(case), "events": generated})
    return _sha256(payload)


def run_benchmark_case(case: BenchmarkCase) -> BenchmarkCaseResult:
    payloads = generate_synthetic_payloads(case)
    if len(payloads) != case.expected_event_count:
        raise RuntimeError("generated benchmark event count does not match profile")

    events: list[APNTEvent] = []
    recommendation_count = 0
    initial_path_latencies_ms: list[float] = []

    for payload in payloads:
        started_ns = time.perf_counter_ns()
        event = APNTEvent.model_validate(payload)
        alert_for_event(event)
        recommendation = recommendation_for_event(event)
        elapsed_ms = (time.perf_counter_ns() - started_ns) / 1_000_000.0
        if not math.isfinite(elapsed_ms) or elapsed_ms < 0:
            raise RuntimeError("invalid measured software-path latency")
        initial_path_latencies_ms.append(elapsed_ms)
        events.append(event)
        if recommendation is not None:
            recommendation_count += 1

    replay_started_ns = time.perf_counter_ns()
    replay = run_scenario(
        scenario_id=f"{BENCHMARK_ID}:{case.case_id}",
        events=events,
        operator_inputs=[],
    )
    replay_ms = (time.perf_counter_ns() - replay_started_ns) / 1_000_000.0
    throughput = len(events) / (replay_ms / 1000.0) if replay_ms > 0 else float("inf")

    p50 = _nearest_rank(initial_path_latencies_ms, 50)
    p95 = _nearest_rank(initial_path_latencies_ms, 95)
    p99 = _nearest_rank(initial_path_latencies_ms, 99)

    return BenchmarkCaseResult(
        case_id=case.case_id,
        source_count=case.source_count,
        update_rate_hz=case.update_rate_hz,
        duration_s=case.duration_s,
        event_count=len(events),
        recommendation_count=recommendation_count,
        initial_awareness_p50_ms=round(p50, 6),
        initial_awareness_p95_ms=round(p95, 6),
        initial_awareness_p99_ms=round(p99, 6),
        initial_awareness_max_ms=round(max(initial_path_latencies_ms), 6),
        full_replay_ms=round(replay_ms, 6),
        full_replay_events_per_second=round(throughput, 3),
        trace_complete=replay.trace_complete,
        execution_attempted=replay.execution_attempted,
        final_integrity_state=replay.final_integrity_state.value,
        internal_software_path_p99_under_1000ms=p99 < 1000.0,
    )


def run_benchmark(*, duration_s: int = DEFAULT_DURATION_S) -> dict[str, Any]:
    cases = benchmark_profile(duration_s=duration_s)
    results = [run_benchmark_case(case) for case in cases]
    if not all(result.trace_complete for result in results):
        raise RuntimeError("benchmark replay trace is incomplete")
    if any(result.execution_attempted for result in results):
        raise RuntimeError("benchmark crossed the non-actuation boundary")

    environment = {
        "python": sys.version.split()[0],
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "github_sha": os.getenv("GITHUB_SHA"),
        "github_run_id": os.getenv("GITHUB_RUN_ID"),
    }
    result = {
        "benchmark_id": BENCHMARK_ID,
        "claims_boundary": BENCHMARK_CLAIMS_BOUNDARY,
        "poc_claims_boundary": CLAIMS_BOUNDARY,
        "measurement_definition": {
            "initial_awareness_path": (
                "in-process APNTEvent validation + alert_for_event + recommendation_for_event"
            ),
            "full_replay": (
                "in-process run_scenario over prevalidated synthetic events with no operator inputs"
            ),
            "excluded_from_initial_awareness_measurement": [
                "network transport",
                "external message-bus latency",
                "OS scheduling guarantees",
                "UI rendering",
                "display scan-out",
                "operator perception/reaction",
                "ASPN/pntOS/GPNTS adapters",
                "physical PNT sensor processing",
            ],
            "percentile_method": "nearest-rank",
            "clock": "time.perf_counter_ns",
        },
        "profile": {
            "source_counts": list(DEFAULT_SOURCE_COUNTS),
            "update_rates_hz": list(DEFAULT_UPDATE_RATES_HZ),
            "duration_s": duration_s,
            "case_count": len(cases),
            "total_synthetic_events": sum(case.expected_event_count for case in cases),
        },
        "workload_digest": workload_digest(cases),
        "environment": environment,
        "results": [asdict(item) for item in results],
        "summary": {
            "all_traces_complete": all(item.trace_complete for item in results),
            "any_execution_attempted": any(item.execution_attempted for item in results),
            "all_internal_software_path_p99_under_1000ms": all(
                item.internal_software_path_p99_under_1000ms for item in results
            ),
            "worst_initial_awareness_p99_ms": round(
                max(item.initial_awareness_p99_ms for item in results), 6
            ),
            "median_case_full_replay_events_per_second": round(
                statistics.median(item.full_replay_events_per_second for item in results),
                3,
            ),
        },
        "claim_note": (
            "A passing internal software-path timing observation is not evidence of the Navy "
            "sub-second end-to-end requirement. The published requirement covers ingestion "
            "through presentation of alert and initial recommended COA; UI rendering, transport, "
            "real APNT interfaces, and target hardware remain unmeasured here."
        ),
    }
    result["result_digest"] = _sha256(result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the NP004 synthetic throughput benchmark")
    parser.add_argument("--duration", type=int, default=DEFAULT_DURATION_S)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run_benchmark(duration_s=args.duration)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    print(f"result_digest={result['result_digest']}")


if __name__ == "__main__":
    main()

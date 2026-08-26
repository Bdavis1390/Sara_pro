from __future__ import annotations

from typing import Any, Callable

from .edge_benchmark import benchmark_callable
from .qualification import (
    CapabilityStatus,
    EvidenceScope,
    QualificationEvidenceRecord,
    RequirementDeltaRecord,
    ResultStatus,
    canonical_digest,
    compile_qualification_bundle,
)


def qualify_host_callable(
    *,
    function: Callable[[Any], Any],
    input_value: Any,
    requirement: RequirementDeltaRecord,
    software_commit: str,
    executed_utc: str,
    operator: str,
    environment: dict[str, Any],
    repetitions: int = 10,
    warmup: int = 1,
) -> dict[str, Any]:
    summary = benchmark_callable(
        function, input_value, repetitions=repetitions, warmup=warmup
    )
    passed = summary.deterministic_output
    evidence = QualificationEvidenceRecord(
        qualification_id="WS-QE-2026-9101",
        requirement_id=requirement.requirement_delta_id,
        test_id="edge_host_callable_v1",
        evidence_scope=EvidenceScope.SOFTWARE,
        capability_status=CapabilityStatus.PROVEN_INTERNALLY,
        environment_digest=canonical_digest(environment),
        configuration_digest=canonical_digest(
            {"repetitions": repetitions, "warmup": warmup}
        ),
        inputs=[{"input_digest": summary.input_digest}],
        outputs=[
            {
                "median_elapsed_ms": summary.median_elapsed_ms,
                "p95_elapsed_ms": summary.p95_elapsed_ms,
                "max_peak_python_bytes": summary.max_peak_python_bytes,
                "deterministic_output": summary.deterministic_output,
                "output_digests": [run.output_digest for run in summary.runs],
            }
        ],
        metrics=[
            {"name": "median_elapsed_ms", "value": summary.median_elapsed_ms},
            {"name": "p95_elapsed_ms", "value": summary.p95_elapsed_ms},
            {"name": "max_peak_python_bytes", "value": summary.max_peak_python_bytes},
            {"name": "deterministic_output", "value": summary.deterministic_output},
        ],
        uncertainty=[
            {"name": "target_edge_device_performance", "state": "NOT_EVALUATED"},
            {"name": "real_time_schedulability", "state": "NOT_EVALUATED"},
        ],
        result=ResultStatus.PASS if passed else ResultStatus.FAIL,
        rationale=(
            "Host-specific callable benchmark produced deterministic output across repetitions"
            if passed
            else "Host-specific callable benchmark produced divergent output"
        ),
        negative_evidence=[] if passed else [{"output_digests": [run.output_digest for run in summary.runs]}],
        software_commit=software_commit,
        executed_utc=executed_utc,
        operator=operator,
    )
    bundle = compile_qualification_bundle(requirement, [evidence])
    bundle.pop("bundle_digest", None)
    bundle["scope_note"] = (
        "Host/runtime-specific Python benchmark only; no GPU/NPU/Jetson/flight-computer, hard-real-time, power, thermal, or mission-performance claim."
    )
    bundle["bundle_digest"] = canonical_digest(bundle)
    return bundle

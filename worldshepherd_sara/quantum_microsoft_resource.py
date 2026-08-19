"""Microsoft QDK resource-estimator adapter for QRF.

Runs locally with no Azure account. The adapter records explicit architecture,
QEC, error-budget, program identity, and estimator version assumptions. It does
not imply availability of a fault-tolerant quantum computer.
"""

from __future__ import annotations

from dataclasses import asdict
from hashlib import sha256
import importlib.metadata
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from qdk.qre import estimate
from qdk.qre.application import OpenQASMApplication
from qdk.qre.models import GateBased, RoundBasedFactory, SurfaceCode

from worldshepherd_sara.quantum_resource import ResourceEstimateRecord, validate_resource_estimate


def _sha256_text(text: str) -> str:
    return "sha256:" + sha256(text.encode("utf-8")).hexdigest()


def _sha256_json(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return _sha256_text(encoded)


def _scalar(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if hasattr(value, "item"):
        try:
            return value.item()
        except (ValueError, TypeError):
            pass
    return str(value)


def _records_from_frame(frame: Any) -> list[dict[str, Any]]:
    """Normalize QRE DataFrame without truncating pandas Timedelta values.

    DataFrame.to_json defaults can represent timedelta-like values in epoch
    milliseconds. QRE runtimes can be much shorter than one millisecond, so that
    path loses evidence by rounding them to zero. Preserve nanoseconds and seconds.
    """
    normalized: list[dict[str, Any]] = []
    for source in frame.to_dict(orient="records"):
        row: dict[str, Any] = {}
        for key, value in source.items():
            if key == "runtime" and hasattr(value, "total_seconds"):
                seconds = float(value.total_seconds())
                nanoseconds = int(getattr(value, "value", round(seconds * 1e9)))
                row["runtime_seconds"] = seconds
                row["runtime_nanoseconds"] = nanoseconds
            else:
                row[key] = _scalar(value)
        normalized.append(row)
    return normalized


def estimate_openqasm(
    program: str,
    *,
    benchmark_id: str,
    logical_qubits: int,
    logical_gate_count: int,
    max_error: float = 0.01,
    physical_error_rate: float = 1e-4,
    gate_time_ns: int = 100,
    measurement_time_ns: int = 500,
) -> dict[str, Any]:
    if logical_qubits <= 0 or logical_gate_count <= 0:
        raise ValueError("logical qubits and logical gate count must be positive")
    if not 0 < max_error < 1:
        raise ValueError("max_error must be in (0, 1)")
    if not 0 < physical_error_rate < 1:
        raise ValueError("physical_error_rate must be in (0, 1)")
    if gate_time_ns <= 0 or measurement_time_ns <= 0:
        raise ValueError("QDK timing parameters must be positive integer nanoseconds")

    app = OpenQASMApplication(program)
    architecture = GateBased(
        error_rate=physical_error_rate,
        gate_time=int(gate_time_ns),
        measurement_time=int(measurement_time_ns),
    )
    results = estimate(
        app,
        architecture,
        isa_query=SurfaceCode.q() * RoundBasedFactory.q(),
        max_error=max_error,
    )
    records = _records_from_frame(results.as_frame())
    if not records:
        raise RuntimeError("Microsoft QDK returned no Pareto-optimal resource estimates")

    candidates = [
        row
        for row in records
        if row.get("qubits") is not None and row.get("runtime_seconds") is not None
    ]
    if not candidates:
        raise RuntimeError(f"QDK result lacks documented qubits/runtime fields: {records!r}")
    selected = min(
        candidates,
        key=lambda row: (float(row["qubits"]), float(row["runtime_seconds"])),
    )

    qdk_version = importlib.metadata.version("qdk")
    record = ResourceEstimateRecord(
        benchmark_id=benchmark_id,
        estimator_name="Microsoft Quantum Resource Estimator / QDK qre",
        estimator_version=qdk_version,
        program_digest=_sha256_text(program),
        logical_qubits=logical_qubits,
        logical_gate_count=logical_gate_count,
        target_logical_error_rate=max_error,
        error_correction_model="SurfaceCode + RoundBasedFactory",
        physical_qubits_estimate=int(selected["qubits"]),
        estimated_runtime_seconds=float(selected["runtime_seconds"]),
        assumptions={
            "physical_error_rate": str(physical_error_rate),
            "gate_time_ns": str(int(gate_time_ns)),
            "measurement_time_ns": str(int(measurement_time_ns)),
            "max_error": str(max_error),
            "selection_rule": "minimum physical qubits, then runtime from Pareto frontier",
            "runtime_evidence": "pandas Timedelta preserved as exact nanoseconds and seconds",
        },
    )
    decision = validate_resource_estimate(record)
    if not decision.accepted:
        raise RuntimeError(f"resource-estimate governance rejected QDK output: {decision.reasons}")

    return {
        "schema_version": "1.1",
        "evidence_level": "resource_estimated",
        "record": asdict(record),
        "selected_qre_result": selected,
        "pareto_result_count": len(records),
        "pareto_results": records,
        "governance": {"accepted": decision.accepted, "reasons": list(decision.reasons)},
        "claim_control": (
            "Estimator-backed fault-tolerant resource projection only. It does not prove that matching hardware exists, "
            "that the program is practically advantageous, or that Worldshepherd owns fault-tolerant quantum hardware."
        ),
    }


DEFAULT_SENSITIVITY_SCENARIOS: tuple[dict[str, Any], ...] = (
    {
        "scenario_id": "optimistic_fast_gate_based",
        "physical_error_rate": 5e-5,
        "gate_time_ns": 50,
        "measurement_time_ns": 250,
        "max_error": 0.01,
    },
    {
        "scenario_id": "reference_gate_based",
        "physical_error_rate": 1e-4,
        "gate_time_ns": 100,
        "measurement_time_ns": 500,
        "max_error": 0.01,
    },
    {
        "scenario_id": "conservative_gate_based",
        "physical_error_rate": 5e-4,
        "gate_time_ns": 250,
        "measurement_time_ns": 1000,
        "max_error": 0.01,
    },
)


def estimate_openqasm_sensitivity(
    program: str,
    *,
    benchmark_id: str,
    logical_qubits: int,
    logical_gate_count: int,
    scenarios: Iterable[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run a governed QDK sensitivity envelope across >=3 explicit assumptions.

    The scenarios intentionally vary physical error/timing assumptions while retaining
    the same application and SurfaceCode + RoundBasedFactory QEC model. This answers
    how sensitive the projected physical-qubit/runtime cost is to hardware assumptions;
    it does not predict which future hardware architecture will actually exist.
    """
    scenario_rows = [dict(row) for row in (scenarios or DEFAULT_SENSITIVITY_SCENARIOS)]
    if len(scenario_rows) < 3:
        raise ValueError("resource sensitivity requires at least three scenarios")
    scenario_ids = [str(row.get("scenario_id", "")).strip() for row in scenario_rows]
    if any(not scenario_id for scenario_id in scenario_ids):
        raise ValueError("every sensitivity scenario requires scenario_id")
    if len(set(scenario_ids)) != len(scenario_ids):
        raise ValueError("sensitivity scenario_id values must be unique")

    results: list[dict[str, Any]] = []
    for row in scenario_rows:
        scenario_id = str(row["scenario_id"])
        assumptions = {
            "physical_error_rate": float(row["physical_error_rate"]),
            "gate_time_ns": int(row["gate_time_ns"]),
            "measurement_time_ns": int(row["measurement_time_ns"]),
            "max_error": float(row.get("max_error", 0.01)),
        }
        payload = estimate_openqasm(
            program,
            benchmark_id=f"{benchmark_id}:{scenario_id}",
            logical_qubits=logical_qubits,
            logical_gate_count=logical_gate_count,
            **assumptions,
        )
        record = payload["record"]
        results.append({
            "scenario_id": scenario_id,
            "scenario_digest": _sha256_json({"scenario_id": scenario_id, **assumptions}),
            "assumptions": assumptions,
            "physical_qubits_estimate": int(record["physical_qubits_estimate"]),
            "estimated_runtime_seconds": float(record["estimated_runtime_seconds"]),
            "selected_qre_result": payload["selected_qre_result"],
            "pareto_result_count": payload["pareto_result_count"],
            "governance": payload["governance"],
        })

    qubits = [row["physical_qubits_estimate"] for row in results]
    runtimes = [row["estimated_runtime_seconds"] for row in results]
    min_qubits = min(qubits)
    max_qubits = max(qubits)
    min_runtime = min(runtimes)
    max_runtime = max(runtimes)
    program_digest = _sha256_text(program)

    return {
        "schema_version": "1.0",
        "evidence_level": "resource_estimated_sensitivity",
        "benchmark_id": benchmark_id,
        "program_digest": program_digest,
        "scenario_count": len(results),
        "qec_model": "SurfaceCode + RoundBasedFactory",
        "scenario_set_digest": _sha256_json([
            {"scenario_id": row["scenario_id"], **row["assumptions"]} for row in results
        ]),
        "scenarios": results,
        "envelope": {
            "physical_qubits_min": min_qubits,
            "physical_qubits_max": max_qubits,
            "physical_qubits_ratio_max_to_min": max_qubits / min_qubits,
            "runtime_seconds_min": min_runtime,
            "runtime_seconds_max": max_runtime,
            "runtime_ratio_max_to_min": max_runtime / min_runtime,
        },
        "claim_control": (
            "Sensitivity envelope over explicit fault-tolerant hardware assumptions only. The envelope is not a hardware forecast, "
            "does not prove availability of a matching QPU, and does not establish quantum advantage."
        ),
    }


def estimate_file(path: str | Path, **kwargs: Any) -> dict[str, Any]:
    source = Path(path).read_text(encoding="utf-8")
    return estimate_openqasm(source, **kwargs)


def estimate_file_sensitivity(path: str | Path, **kwargs: Any) -> dict[str, Any]:
    source = Path(path).read_text(encoding="utf-8")
    return estimate_openqasm_sensitivity(source, **kwargs)

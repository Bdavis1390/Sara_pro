"""Microsoft QDK resource-estimator adapter for QRF.

Runs locally with no Azure account. The adapter records explicit architecture,
QEC, error-budget, program identity, and estimator version assumptions. It does
not imply availability of a fault-tolerant quantum computer.
"""

from __future__ import annotations

from dataclasses import asdict
from hashlib import sha256
import importlib.metadata
from pathlib import Path
from typing import Any

from qdk.qre import estimate
from qdk.qre.application import OpenQASMApplication
from qdk.qre.models import GateBased, RoundBasedFactory, SurfaceCode

from worldshepherd_sara.quantum_resource import ResourceEstimateRecord, validate_resource_estimate


def _sha256_text(text: str) -> str:
    return "sha256:" + sha256(text.encode("utf-8")).hexdigest()


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


def estimate_file(path: str | Path, **kwargs: Any) -> dict[str, Any]:
    source = Path(path).read_text(encoding="utf-8")
    return estimate_openqasm(source, **kwargs)

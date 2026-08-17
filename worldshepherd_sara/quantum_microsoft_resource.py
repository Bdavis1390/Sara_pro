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
from typing import Any

from qdk.qre import estimate
from qdk.qre.application import OpenQASMApplication
from qdk.qre.models import GateBased, RoundBasedFactory, SurfaceCode

from worldshepherd_sara.quantum_resource import ResourceEstimateRecord, validate_resource_estimate


def _sha256_text(text: str) -> str:
    return "sha256:" + sha256(text.encode("utf-8")).hexdigest()


def _records_from_frame(frame: Any) -> list[dict[str, Any]]:
    # Pandas DataFrame is the documented QRE presentation path. Normalize to
    # JSON-safe records without making pandas a direct Worldshepherd dependency.
    return json.loads(frame.to_json(orient="records"))


def estimate_openqasm(
    program: str,
    *,
    benchmark_id: str,
    logical_qubits: int,
    logical_gate_count: int,
    max_error: float = 0.01,
    physical_error_rate: float = 1e-4,
    gate_time_ns: float = 100.0,
    measurement_time_ns: float = 500.0,
) -> dict[str, Any]:
    if logical_qubits <= 0 or logical_gate_count <= 0:
        raise ValueError("logical qubits and logical gate count must be positive")
    if not 0 < max_error < 1:
        raise ValueError("max_error must be in (0, 1)")

    app = OpenQASMApplication(program)
    architecture = GateBased(
        error_rate=physical_error_rate,
        gate_time=gate_time_ns,
        measurement_time=measurement_time_ns,
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

    # QRE documents `qubits`, `runtime` (nanoseconds), and `error` for each
    # Pareto-optimal point. Choose minimum physical qubits, then runtime.
    candidates = [row for row in records if row.get("qubits") is not None and row.get("runtime") is not None]
    if not candidates:
        raise RuntimeError(f"QDK result lacks documented qubits/runtime fields: {records!r}")
    selected = min(candidates, key=lambda row: (float(row["qubits"]), float(row["runtime"])))

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
        estimated_runtime_seconds=float(selected["runtime"]) * 1e-9,
        assumptions={
            "physical_error_rate": str(physical_error_rate),
            "gate_time_ns": str(gate_time_ns),
            "measurement_time_ns": str(measurement_time_ns),
            "max_error": str(max_error),
            "selection_rule": "minimum physical qubits, then runtime from Pareto frontier",
        },
    )
    decision = validate_resource_estimate(record)
    if not decision.accepted:
        raise RuntimeError(f"resource-estimate governance rejected QDK output: {decision.reasons}")

    return {
        "schema_version": "1.0",
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

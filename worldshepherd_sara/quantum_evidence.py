"""Machine-readable evidence generation for Worldshepherd quantum benchmarks.

The evidence bundle records simulator identity, software versions, circuit/program
digests, result digests, noise parameters, and acceptance metrics. It does not
promote simulator output into a QPU or quantum-advantage claim.
"""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from importlib.metadata import PackageNotFoundError, version
import json
from pathlib import Path
import platform
from typing import Any

from .quantum_qiskit import run_bell_simulation


def _package_version(name: str) -> str:
    try:
        return version(name)
    except PackageNotFoundError:
        return "unknown"


def _sha256_bytes(payload: bytes) -> str:
    return f"sha256:{sha256(payload).hexdigest()}"


def _result_to_dict(result: Any) -> dict[str, Any]:
    return {
        "backend": result.backend,
        "backend_class": "noisy_simulator" if result.noisy else "statevector_simulator",
        "noisy": result.noisy,
        "shots": result.shots,
        "seed": result.seed,
        "counts": dict(sorted(result.counts.items())),
        "correlated_fraction": result.correlated_fraction,
        "result_digest": result.result_digest,
        "noise_model": dict(result.noise_model),
        "claim_class": "quantum_simulated",
    }


def build_bell_evidence_bundle(
    qasm_path: str | Path,
    *,
    shots: int = 4096,
    seed: int = 9675,
    one_qubit_error: float = 0.05,
    two_qubit_error: float = 0.15,
) -> dict[str, Any]:
    path = Path(qasm_path)
    qasm_bytes = path.read_bytes()

    ideal = run_bell_simulation(shots=shots, seed=seed, noisy=False)
    noisy = run_bell_simulation(
        shots=shots,
        seed=seed,
        noisy=True,
        one_qubit_error=one_qubit_error,
        two_qubit_error=two_qubit_error,
    )

    bundle: dict[str, Any] = {
        "schema_version": "1.0",
        "benchmark_id": "QRF-BELL-001",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "program": str(path.as_posix()),
        "program_digest": _sha256_bytes(qasm_bytes),
        "execution_class": "simulation_only",
        "scientific_claim": "none",
        "software": {
            "python": platform.python_version(),
            "qiskit": _package_version("qiskit"),
            "qiskit_aer": _package_version("qiskit-aer"),
        },
        "runs": {
            "ideal": _result_to_dict(ideal),
            "noisy": _result_to_dict(noisy),
        },
        "acceptance": {
            "ideal_correlated_fraction_required": 1.0,
            "noisy_correlated_fraction_range": [0.5, 1.0],
            "qpu_gate": "not_satisfied",
            "quantum_advantage_gate": "not_applicable",
        },
    }
    canonical = json.dumps(bundle, sort_keys=True, separators=(",", ":")).encode("utf-8")
    bundle["bundle_digest"] = _sha256_bytes(canonical)
    return bundle


def write_evidence_bundle(bundle: dict[str, Any], output_path: str | Path) -> Path:
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(bundle, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return out

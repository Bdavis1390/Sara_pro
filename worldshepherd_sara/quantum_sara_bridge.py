"""Bridge QRF simulation evidence into the existing SARA evidence contract."""

from __future__ import annotations

from hashlib import sha256
import math
from pathlib import Path
from typing import Any

from .evidence_contract import validate_experiment_record


def _file_sha256(path: Path) -> str:
    return f"sha256:{sha256(path.read_bytes()).hexdigest()}"


def _expanded_binomial_uncertainty(p: float, shots: int) -> float:
    if shots <= 0:
        return 0.0
    p = min(max(float(p), 0.0), 1.0)
    return 2.0 * math.sqrt(p * (1.0 - p) / shots)


def simulation_bundle_to_experiment_record(
    bundle: dict[str, Any],
    *,
    evidence_path: str | Path,
    sara_version: str,
    commit: str,
    campaign_id: str = "SARA-QRF",
    result_class: str = "WS-R1",
    review_state: str = "DRAFT",
) -> dict[str, Any]:
    path = Path(evidence_path)
    if not path.is_file():
        raise FileNotFoundError(path)

    benchmark_id = str(bundle.get("benchmark_id", "")).strip()
    generated = str(bundle.get("generated_at_utc", "")).strip()
    program_digest = str(bundle.get("program_digest", "")).strip()
    bundle_digest = str(bundle.get("bundle_digest", "")).strip()
    if not benchmark_id or not generated or not program_digest or not bundle_digest:
        raise ValueError("bundle is missing required benchmark/timestamp/digest fields")

    runs = bundle.get("runs") or {}
    noisy = runs.get("noisy") or {}
    shots = int(noisy.get("shots", 0) or 0)
    correlated = float(noisy.get("correlated_fraction", 0.0) or 0.0)
    raw_digest = _file_sha256(path)

    record = {
        "experiment_id": f"QRF-{benchmark_id}-{bundle_digest.split(':')[-1][:12]}",
        "campaign_id": campaign_id,
        "test_article_id": benchmark_id,
        "timestamp_utc": generated,
        "evidence_class": ["SIMULATED", "ARTIFACT"],
        "hardware": {
            "geometry_digest": program_digest,
            "configuration_digest": bundle_digest,
            "material_batch_ids": [],
        },
        "software": {
            "sara_version": sara_version,
            "commit": commit,
        },
        "calibration_ids": [],
        "sensor_manifest": [],
        "environment": {
            "quantum_domain": "quantum_computing",
            "execution_class": bundle.get("execution_class", "simulation_only"),
            "backend": noisy.get("backend"),
            "backend_class": noisy.get("backend_class"),
            "software": bundle.get("software", {}),
            "noise_model": noisy.get("noise_model", {}),
            "claim_class": noisy.get("claim_class", "quantum_simulated"),
            "qpu_gate": (bundle.get("acceptance") or {}).get("qpu_gate"),
        },
        "raw_data": {
            "location": str(path),
            "digest": raw_digest,
        },
        "uncertainty": {
            "model_id": "QRF-BELL-BINOMIAL-2SIGMA",
            "expanded_uncertainty": _expanded_binomial_uncertainty(correlated, shots),
        },
        "hypotheses": {
            "H0": "The governed simulator execution does not satisfy the predeclared Bell-correlation smoke-test acceptance behavior.",
            "H1": "The governed simulator execution satisfies the predeclared Bell-correlation smoke-test acceptance behavior.",
        },
        "result_class": result_class,
        "review_state": review_state,
        "quantum": {
            "benchmark_id": benchmark_id,
            "program_digest": program_digest,
            "bundle_digest": bundle_digest,
            "result_digest": noisy.get("result_digest"),
            "claim_ceiling": "quantum_simulated",
            "hardware_execution": False,
        },
    }
    return validate_experiment_record(record)

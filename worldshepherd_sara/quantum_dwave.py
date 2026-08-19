"""Credential-gated D-Wave annealing adapter for Worldshepherd QRF.

This module treats quantum annealing as a distinct optimization modality. It does not
compare annealing qubit counts to universal gate-model qubits and does not permit a
toy/synthetic QUBO result to satisfy a mission gate without an explicitly frozen
instance family and strong classical baseline.

The D-Wave Ocean dependency is imported lazily so QRF's core governance remains
provider-neutral and does not require Leap credentials or Ocean for non-D-Wave work.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
import importlib
import importlib.metadata
import json
from time import perf_counter
from typing import Any, Mapping

from worldshepherd_sara.quantum_external_evidence import ExternalEvidenceRecord, ExternalEvidenceType


def _digest_json(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return "sha256:" + sha256(encoded).hexdigest()


def _utc_now_z() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _json_safe(payload: Any) -> Any:
    return json.loads(json.dumps(payload, sort_keys=True, default=str))


def qubo_digest(qubo: Mapping[tuple[Any, Any], float]) -> str:
    rows = [
        {"u": str(u), "v": str(v), "weight": float(weight)}
        for (u, v), weight in qubo.items()
    ]
    rows.sort(key=lambda row: (row["u"], row["v"], row["weight"]))
    return _digest_json(rows)


@dataclass(frozen=True)
class DWaveAnnealResult:
    provider: str
    modality: str
    solver_name: str
    solver_identity: Mapping[str, Any]
    solver_identity_digest: str
    solver_properties_digest: str
    problem_digest: str
    num_reads: int
    best_sample: Mapping[str, int]
    best_energy: float
    samples: tuple[Mapping[str, Any], ...]
    timing: Mapping[str, Any]
    timing_digest: str
    embedding_context: Mapping[str, Any]
    result_digest: str
    wall_latency_seconds: float
    executed_at_utc: str
    ocean_version: str | None
    claim_control: str = (
        "D-Wave quantum-annealing execution evidence only. Annealing is a distinct computational modality; "
        "this record does not imply gate-model quantum execution, quantum advantage, or mission relevance."
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _solver_identity(sampler: Any) -> tuple[str, dict[str, Any]]:
    solver = getattr(sampler, "solver", None)
    name = str(getattr(solver, "name", "unknown"))
    identity_obj = getattr(solver, "identity", None)
    if identity_obj is None:
        identity = {"name": name}
    else:
        try:
            identity = identity_obj.dict()
        except Exception:
            try:
                identity = dict(identity_obj)
            except Exception:
                identity = {"repr": repr(identity_obj), "name": name}
    return name, _json_safe(identity)


def _sampleset_rows(sampleset: Any) -> tuple[Mapping[str, Any], ...]:
    rows: list[Mapping[str, Any]] = []
    for datum in sampleset.data(fields=["sample", "energy", "num_occurrences"], sorted_by="energy"):
        rows.append({
            "sample": {str(key): int(value) for key, value in dict(datum.sample).items()},
            "energy": float(datum.energy),
            "num_occurrences": int(datum.num_occurrences),
        })
    return tuple(rows)


def run_qubo_on_dwave_hardware(
    qubo: Mapping[tuple[Any, Any], float],
    *,
    token: str,
    num_reads: int = 1000,
    solver_name: str | None = None,
    topology_type: str = "zephyr",
    label: str = "Worldshepherd QRF annealing benchmark",
) -> DWaveAnnealResult:
    """Run a QUBO on a real D-Wave QPU through Ocean/Leap.

    Requires an injected Leap token. The function requests a QPU solver and uses
    EmbeddingComposite so an unstructured BQM/QUBO can be minor-embedded into the
    selected hardware topology. Solver identity and working-graph identity are retained
    from Ocean's current solver representation.
    """
    if not token or not token.strip():
        raise ValueError("D-Wave Leap API token must be injected at runtime")
    if num_reads <= 0:
        raise ValueError("num_reads must be positive")
    if not qubo:
        raise ValueError("QUBO must be non-empty")

    dwave_system = importlib.import_module("dwave.system")
    DWaveSampler = getattr(dwave_system, "DWaveSampler")
    EmbeddingComposite = getattr(dwave_system, "EmbeddingComposite")

    sampler_kwargs: dict[str, Any] = {"token": token.strip()}
    if solver_name:
        sampler_kwargs["solver"] = solver_name
    else:
        sampler_kwargs["topology__type"] = topology_type

    wall_start = perf_counter()
    with DWaveSampler(**sampler_kwargs) as raw_sampler:
        category = str(raw_sampler.properties.get("category", "")).lower()
        if category != "qpu":
            raise RuntimeError(f"selected D-Wave solver is not a QPU: category={category!r}")
        name, identity = _solver_identity(raw_sampler)
        properties = _json_safe(dict(raw_sampler.properties))
        properties_digest = _digest_json(properties)
        identity_digest = _digest_json(identity)
        with EmbeddingComposite(raw_sampler) as sampler:
            sampleset = sampler.sample_qubo(
                dict(qubo),
                num_reads=num_reads,
                label=label,
                return_embedding=True,
            )
            sampleset.resolve()
            rows = _sampleset_rows(sampleset)
            info = _json_safe(dict(sampleset.info))

    wall_latency = max(0.0, perf_counter() - wall_start)
    if not rows:
        raise RuntimeError("D-Wave QPU returned no samples")
    timing = _json_safe(info.get("timing", {})) if isinstance(info, dict) else {}
    embedding_context = _json_safe(info.get("embedding_context", {})) if isinstance(info, dict) else {}
    problem_id = qubo_digest(qubo)
    result_payload = {
        "provider": "D-Wave Leap",
        "modality": "quantum_annealing",
        "solver_name": name,
        "solver_identity": identity,
        "problem_digest": problem_id,
        "num_reads": num_reads,
        "samples": list(rows),
        "timing": timing,
        "embedding_context": embedding_context,
    }
    try:
        ocean_version = importlib.metadata.version("dwave-ocean-sdk")
    except importlib.metadata.PackageNotFoundError:
        ocean_version = None

    return DWaveAnnealResult(
        provider="D-Wave Leap",
        modality="quantum_annealing",
        solver_name=name,
        solver_identity=identity,
        solver_identity_digest=identity_digest,
        solver_properties_digest=properties_digest,
        problem_digest=problem_id,
        num_reads=num_reads,
        best_sample=dict(rows[0]["sample"]),
        best_energy=float(rows[0]["energy"]),
        samples=rows,
        timing=timing,
        timing_digest=_digest_json(timing),
        embedding_context=embedding_context,
        result_digest=_digest_json(result_payload),
        wall_latency_seconds=wall_latency,
        executed_at_utc=_utc_now_z(),
        ocean_version=ocean_version,
    )


def build_dwave_mission_optimization_evidence(
    result: DWaveAnnealResult,
    *,
    project_id: str,
    campaign_gate_id: str,
    classical_baseline_digest: str,
    instance_family_digest: str,
    objective_definition: str,
    constraint_definition: str,
    cost_usd: float,
) -> ExternalEvidenceRecord:
    """Convert a genuine D-Wave run into a structurally typed optimization record.

    The caller must provide the frozen mission-instance family and classical baseline.
    This deliberately prevents an arbitrary toy QUBO from being relabeled as mission
    evidence solely because it executed on an annealer.
    """
    for name, value in {
        "project_id": project_id,
        "campaign_gate_id": campaign_gate_id,
        "classical_baseline_digest": classical_baseline_digest,
        "instance_family_digest": instance_family_digest,
        "objective_definition": objective_definition,
        "constraint_definition": constraint_definition,
    }.items():
        if not str(value).strip():
            raise ValueError(f"{name} is required")
    if cost_usd < 0:
        raise ValueError("cost_usd must be non-negative")

    configuration = {
        "modality": result.modality,
        "solver_name": result.solver_name,
        "solver_identity_digest": result.solver_identity_digest,
        "solver_properties_digest": result.solver_properties_digest,
        "problem_digest": result.problem_digest,
        "num_reads": result.num_reads,
        "ocean_version": result.ocean_version,
    }
    raw_digest = _digest_json(result.to_dict())
    return ExternalEvidenceRecord(
        project_id=project_id,
        evidence_type=ExternalEvidenceType.MISSION_OPTIMIZATION,
        source_id=f"dwave-leap:{result.solver_name}:{result.result_digest}",
        raw_artifact_digest=raw_digest,
        collected_utc=result.executed_at_utc,
        provider_or_lab=result.provider,
        configuration_digest=_digest_json(configuration),
        repeat_count=1,
        result_digest=result.result_digest,
        classical_baseline_digest=classical_baseline_digest,
        job_or_run_id=result.result_digest,
        backend_or_device=result.solver_name,
        latency_seconds=result.wall_latency_seconds,
        cost_usd=float(cost_usd),
        environment="remote_dwave_qpu",
        metadata={
            "campaign_gate_id": campaign_gate_id,
            "instance_family_digest": instance_family_digest,
            "objective_definition": objective_definition,
            "constraint_definition": constraint_definition,
            "quantum_modality": result.modality,
            "solver_identity_digest": result.solver_identity_digest,
            "solver_properties_digest": result.solver_properties_digest,
            "timing_digest": result.timing_digest,
            "problem_digest": result.problem_digest,
            "embedding_retained": str(bool(result.embedding_context)).lower(),
            "ocean_version": result.ocean_version or "unknown",
        },
    )

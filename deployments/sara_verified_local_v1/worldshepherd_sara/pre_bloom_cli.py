from __future__ import annotations

import argparse
import json
import os
import platform
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

from .ddil_rejoin_qualification import qualify_partition_rejoin
from .edge_qualification import qualify_host_callable
from .evidence_store import EvidenceStore
from .pre_cli import build_all
from .pre_portfolio import build_horizon_portfolio, build_readiness_ledger
from .qualification import (
    CapabilityStatus,
    DemandClass,
    ForecastHorizon,
    RequirementDeltaRecord,
    SourceRecord,
    SourceStatus,
    canonical_digest,
)
from .software_provenance import BuildProvenance, SoftwareComponent


def _write(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def _requirement(
    requirement_id: str,
    title: str,
    statement: str,
    lanes: list[str],
    missing: list[str],
) -> RequirementDeltaRecord:
    return RequirementDeltaRecord(
        requirement_delta_id=requirement_id,
        demand_class=DemandClass.EMERGING_DEMAND,
        source=SourceRecord(
            title=title,
            agency="Worldshepherd PRE",
            url=f"internal://pre/{requirement_id.lower()}",
            source_status=SourceStatus.PRIMARY_TECHNICAL_SOURCE,
            retrieved_utc="2026-08-26T00:00:00Z",
        ),
        statement=statement,
        recurrence="Reusable predictive readiness requirement",
        forecast_horizon=ForecastHorizon.D0_90,
        affected_lanes=lanes,
        existing_capability=["claims-controlled internal software baseline"],
        capability_status=[CapabilityStatus.IMPLEMENTED_IN_SOFTWARE],
        missing_capability=missing,
        experiment_or_demonstration_needed=["reproducible bounded benchmark"],
        evidence_target=["machine-readable Qualification Evidence bundle"],
        claims_boundary=["Internal/synthetic evidence only unless explicitly upgraded by corresponding external evidence."],
    )


def _edge_workload(value: dict[str, Any]) -> dict[str, Any]:
    values = [float(item) for item in value["values"]]
    return {
        "count": len(values),
        "sum": sum(values),
        "minimum": min(values),
        "maximum": max(values),
    }


def _installed_component(name: str, *, supplier: str | None = None) -> SoftwareComponent:
    try:
        installed_version = version(name)
    except PackageNotFoundError:
        installed_version = "UNKNOWN"
    return SoftwareComponent(
        name=name,
        version=installed_version,
        package_type="python",
        supplier=supplier,
        purl=None if installed_version == "UNKNOWN" else f"pkg:pypi/{name}@{installed_version}",
    )


def build_bloom(
    *, fixtures: Path, out: Path, software_commit: str, executed_utc: str, operator: str
) -> dict[str, Any]:
    index = build_all(
        fixtures=fixtures,
        out=out,
        software_commit=software_commit,
        executed_utc=executed_utc,
        operator=operator,
    )

    edge_requirement = _requirement(
        "PRE-RD-2026-0018",
        "Edge-AI host benchmark readiness target",
        "Measure deterministic host/runtime latency and memory before target edge-device claims.",
        ["edge AI", "autonomy", "sensor fusion", "C2"],
        ["target device", "power/thermal evidence", "hard-real-time validation"],
    )
    rejoin_requirement = _requirement(
        "PRE-RD-2026-0019",
        "DDIL partition/rejoin reconciliation readiness target",
        "Reconcile non-conflicting state after partition and surface equal-authority divergence without silent resolution.",
        ["DDIL", "C2", "autonomy", "configuration custody"],
        ["distributed deployment", "real network partitions", "consensus validation"],
    )

    runtime_identity = {
        "python_version": platform.python_version(),
        "implementation": platform.python_implementation(),
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "execution_context": "pre-bloom-cli",
    }

    edge = qualify_host_callable(
        function=_edge_workload,
        input_value={"values": list(range(1, 129))},
        requirement=edge_requirement,
        software_commit=software_commit,
        executed_utc=executed_utc,
        operator=operator,
        environment={
            **runtime_identity,
            "runtime": "python",
            "device_claim": "NONE",
        },
        repetitions=7,
        warmup=1,
    )
    rejoin = qualify_partition_rejoin(
        requirement=rejoin_requirement,
        software_commit=software_commit,
        executed_utc=executed_utc,
        operator=operator,
    )

    store = EvidenceStore(out / "echo_store")
    for name, bundle in {"edge": edge, "ddil_rejoin": rejoin}.items():
        _write(out / f"{name}_qualification_bundle.json", bundle)
        index["bundle_digests"][name] = bundle["bundle_digest"]
        index["custody_digests"][name] = store.put_bundle(bundle)
        index["failures"][name] = [
            record["test_id"] for record in bundle["evidence"] if record["result"] != "PASS"
        ]

    readiness = build_readiness_ledger(index["bundle_digests"])
    horizons = build_horizon_portfolio()
    _write(out / "capability_readiness_ledger.json", readiness)
    _write(out / "capability_horizons.json", horizons)

    bundle_manifest = {
        "schema": "WS-PRE-BUNDLE-MANIFEST-V1",
        "software_commit": software_commit,
        "bundle_digests": dict(sorted(index["bundle_digests"].items())),
    }
    components = [
        _installed_component("worldshepherd-sara", supplier="Worldshepherd internal"),
        _installed_component("fastapi"),
        _installed_component("uvicorn"),
        _installed_component("pydantic"),
    ]
    provenance = BuildProvenance(
        provenance_id="WS-PRE-BLOOM-BUILD-V1",
        source_repository="Bdavis1390/Sara_pro",
        source_commit=software_commit,
        builder_id=operator,
        build_environment_digest=canonical_digest(
            {
                "builder": operator,
                "runtime_identity": runtime_identity,
                "components": [component.model_dump(mode="json") for component in components],
            }
        ),
        output_artifact_digest=canonical_digest(bundle_manifest),
        components=components,
        metadata={
            "attested_object": "WS-PRE-BUNDLE-MANIFEST-V1",
            "runtime_identity": runtime_identity,
        },
    )
    provenance_value = provenance.model_dump(mode="json")
    provenance_value["provenance_digest"] = provenance.digest()
    provenance_value["claims_boundary"] = provenance.claims_boundary()
    _write(out / "software_provenance.json", provenance_value)

    index["custody_verification"] = store.verify_all()
    index["readiness_ledger_digest"] = readiness["ledger_digest"]
    index["horizon_portfolio_digest"] = horizons["portfolio_digest"]
    index["software_provenance_digest"] = provenance.digest()
    index["bloom_extensions"] = [
        "edge_host_benchmark",
        "ddil_partition_rejoin",
        "capability_readiness_ledger",
        "0-90D_3-12M_12-24M_PLUS_horizons",
        "internal_unsigned_software_provenance",
    ]
    index["claims_boundary"].extend(
        [
            "Edge benchmark metrics are host/runtime specific and do not establish target-device performance.",
            "DDIL rejoin evidence validates a synthetic conflict policy, not distributed consensus or operational network resilience.",
            "Capability horizons schedule preparation only and never upgrade readiness claims.",
            "Software provenance is INTERNAL_UNSIGNED unless a later attestation explicitly records signing/verification evidence.",
        ]
    )
    _write(out / "qualification_index.json", index)
    return index


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Worldshepherd PRE full-bloom evidence")
    parser.add_argument("--fixtures", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--software-commit", default=os.getenv("GITHUB_SHA", "UNKNOWN"))
    parser.add_argument("--executed-utc", required=True)
    parser.add_argument("--operator", default="worldshepherd-pre-bloom-cli")
    args = parser.parse_args()
    index = build_bloom(
        fixtures=args.fixtures,
        out=args.out,
        software_commit=args.software_commit,
        executed_utc=args.executed_utc,
        operator=args.operator,
    )
    failed = any(index["failures"].values()) or not all(index["custody_verification"].values())
    print(json.dumps(index, sort_keys=True))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

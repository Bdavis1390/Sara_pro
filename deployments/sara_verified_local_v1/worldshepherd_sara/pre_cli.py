from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .ade_qualification import qualify_synthetic_discovery
from .apnt_qualification import qualify_synthetic_apnt_timeline
from .ddil import Envelope
from .ddil_campaign import run_ddil_campaign
from .evidence_store import EvidenceStore
from .ietm import qualify_synthetic_ietm
from .mbse_benchmark import qualify_synthetic_mbse
from .qualification import (
    CapabilityStatus,
    DemandClass,
    ForecastHorizon,
    RequirementDeltaRecord,
    SourceRecord,
    SourceStatus,
    canonical_digest,
)


def _requirement(
    *,
    requirement_id: str,
    title: str,
    agency: str,
    url: str,
    topic: str,
    statement: str,
    lanes: list[str],
    missing: list[str],
    claims: list[str],
    source_status: SourceStatus = SourceStatus.GOVERNMENT_SECONDARY_VERIFIED,
) -> RequirementDeltaRecord:
    return RequirementDeltaRecord(
        requirement_delta_id=requirement_id,
        demand_class=DemandClass.CONFIRMED_DEMAND,
        source=SourceRecord(
            title=title,
            agency=agency,
            url=url,
            solicitation_or_topic=topic,
            source_status=source_status,
            retrieved_utc="2026-08-26T00:00:00Z",
        ),
        statement=statement,
        recurrence="Release-5 capture and reusable PRE readiness requirement",
        forecast_horizon=ForecastHorizon.D0_90,
        affected_lanes=lanes,
        existing_capability=["claims-controlled software qualification scaffold"],
        capability_status=[CapabilityStatus.IMPLEMENTED_IN_SOFTWARE],
        missing_capability=missing,
        experiment_or_demonstration_needed=["frozen synthetic reproducible benchmark"],
        evidence_target=["machine-readable qualification bundle"],
        claims_boundary=claims,
    )


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, value: dict) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def build_all(
    *, fixtures: Path, out: Path, software_commit: str, executed_utc: str, operator: str
) -> dict:
    out.mkdir(parents=True, exist_ok=True)

    apnt_fixture = _load(fixtures / "apnt_destroyer_strait_v1.json")
    mbse_fixture = _load(fixtures / "mbse_legacy_fixture_v1.json")
    ietm_fixture = _load(fixtures / "ietm_synthetic_v1.json")
    ade_fixture = _load(fixtures / "ade_symbolic_v1.json")

    apnt_requirement = _requirement(
        requirement_id="PRE-RD-2026-0001",
        title="NAVWAR APNT operational awareness and decision-support target",
        agency="NAVWAR",
        url="https://navysbir.us/n26_5/DON26BX05-NP004.htm",
        topic="DON26BX05-NP004",
        statement="Demonstrate modular APNT operational-awareness software using representative synthetic data while retaining source confidence/provenance and bounded recovery decision support.",
        lanes=["APNT", "C2", "mission assurance", "DDIL"],
        missing=["ASPN/pntOS/GPNTS validation", "Navy operator validation"],
        claims=["No physical APNT, shipboard, sensor-accuracy, or Navy operator-performance claim"],
    )
    mbse_requirement = _requirement(
        requirement_id="PRE-RD-2026-0002",
        title="NAVSEA AI-to-MBSE reconstruction target",
        agency="NAVSEA",
        url="https://navysbir.us/n26_5/DON26BX05-NP003.htm",
        topic="DON26BX05-NP003",
        statement="Transform heterogeneous legacy artifacts into a source-traceable system model and measure reconstruction quality against known ground truth.",
        lanes=["MBSE", "digital engineering", "configuration provenance"],
        missing=["general document understanding", "SysML/Cameo interoperability", "Navy data validation"],
        claims=["No Navy/Aegis, Cameo/MagicDraw, classified-system, or production reconstruction claim"],
    )
    ietm_requirement = _requirement(
        requirement_id="PRE-RD-2026-0003",
        title="NAVAIR technical-data/IETM transformation target",
        agency="NAVAIR",
        url="https://navysbir.us/n26_5/DON26BZ05-NV078.htm",
        topic="DON26BZ05-NV078",
        statement="Transform technical data while preserving source structure and distribution markings through a governed, testable conversion pipeline.",
        lanes=["technical data", "IETM", "provenance", "configuration custody"],
        missing=["S1000D/MIL-standard validation", "Navy viewer compatibility", "production accuracy"],
        claims=["No S1000D, MIL-standard, Navy viewer, or production conversion claim"],
    )
    ade_requirement = _requirement(
        requirement_id="PRE-RD-2026-0012",
        title="DARPA SPEED DIAL automated algorithm-discovery readiness target",
        agency="DARPA",
        url="https://www.darpa.mil/research/programs/speed-dial",
        topic="DPA26TZ05-DV003",
        statement="Develop measurable automated interpretable algorithm-discovery capability while preserving the distinction between a synthetic internal benchmark and the topic's pre-existing D2P2/SOTA evidence gate.",
        lanes=["ADE-G", "AI governance", "digital engineering", "simulation governance"],
        missing=["SOTA benchmark", "real engineering workflow integration", "D2P2 prior discovery evidence", "research-institution partner"],
        claims=["No SOTA, scientific novelty, real-engineering superiority, or SPEED DIAL D2P2 eligibility claim"],
        source_status=SourceStatus.OFFICIAL_SOURCE_VERIFIED,
    )

    apnt = qualify_synthetic_apnt_timeline(
        fixture=apnt_fixture,
        requirement=apnt_requirement,
        software_commit=software_commit,
        executed_utc=executed_utc,
        operator=operator,
    )
    mbse = qualify_synthetic_mbse(
        fixture=mbse_fixture,
        requirement=mbse_requirement,
        software_commit=software_commit,
        executed_utc=executed_utc,
        operator=operator,
    )
    ietm = qualify_synthetic_ietm(
        fixture=ietm_fixture,
        requirement=ietm_requirement,
        software_commit=software_commit,
        executed_utc=executed_utc,
        operator=operator,
    )
    ade = qualify_synthetic_discovery(
        fixture=ade_fixture,
        requirement=ade_requirement,
        software_commit=software_commit,
        executed_utc=executed_utc,
        operator=operator,
    )
    ddil_messages = [
        Envelope(
            sequence=i,
            source="synthetic-apnt-node",
            payload={"state_index": i},
            timestamp_ms=i * 100,
        )
        for i in range(1, 7)
    ]
    ddil = run_ddil_campaign(
        messages=ddil_messages,
        requirement=apnt_requirement,
        software_commit=software_commit,
        executed_utc=executed_utc,
        operator=operator,
    )

    bundles = {
        "apnt": apnt,
        "mbse": mbse,
        "ietm": ietm,
        "ade": ade,
        "ddil": ddil,
    }
    custody_store = EvidenceStore(out / "echo_store")
    custody_digests: dict[str, str] = {}
    for name, bundle in bundles.items():
        _write(out / f"{name}_qualification_bundle.json", bundle)
        custody_digests[name] = custody_store.put_bundle(bundle)

    failures = {
        name: [record["test_id"] for record in bundle["evidence"] if record["result"] != "PASS"]
        for name, bundle in bundles.items()
    }
    index = {
        "schema": "WS-PRE-QUALIFICATION-INDEX-V1",
        "software_commit": software_commit,
        "executed_utc": executed_utc,
        "operator": operator,
        "bundle_digests": {name: bundle["bundle_digest"] for name, bundle in bundles.items()},
        "custody_digests": custody_digests,
        "custody_verification": custody_store.verify_all(),
        "fixture_digests": {
            "apnt": canonical_digest(apnt_fixture),
            "mbse": canonical_digest(mbse_fixture),
            "ietm": canonical_digest(ietm_fixture),
            "ade": canonical_digest(ade_fixture),
        },
        "failures": failures,
        "claims_boundary": [
            "This index records synthetic/internal software evidence only.",
            "The hash-addressed ECHO-style store provides local integrity/custody behavior only; it is not a government records system or legal chain-of-custody service.",
            "ADE-G evidence in this index is a bounded synthetic interpretability/discovery benchmark and does not establish SOTA or SPEED DIAL D2P2 eligibility.",
            "No physical, platform, government, certification, compliance, clearance, or operational readiness is inferred from these passing bundles.",
        ],
    }
    _write(out / "qualification_index.json", index)
    return index


def main() -> int:
    parser = argparse.ArgumentParser(description="Build claims-controlled PRE qualification evidence")
    parser.add_argument("--fixtures", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--software-commit", default=os.getenv("GITHUB_SHA", "UNKNOWN"))
    parser.add_argument("--executed-utc", required=True)
    parser.add_argument("--operator", default="worldshepherd-pre-cli")
    args = parser.parse_args()

    index = build_all(
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

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .ade_qualification import qualify_synthetic_discovery
from .apnt_qualification import qualify_synthetic_apnt_timeline
from .cbm_qualification import qualify_synthetic_cbm
from .ddil import Envelope
from .ddil_campaign import run_ddil_campaign
from .evidence_store import EvidenceStore
from .ietm import qualify_synthetic_ietm
from .manufacturing_qualification import qualify_synthetic_manufacturing_thread
from .mbse_benchmark import qualify_synthetic_mbse
from .mission_qualification import qualify_synthetic_mission_replay
from .rf_validation import qualify_synthetic_rf_discrepancy
from .sensor_fusion_qualification import qualify_synthetic_sensor_fusion
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
    *, requirement_id: str, title: str, agency: str, url: str, topic: str,
    statement: str, lanes: list[str], missing: list[str], claims: list[str],
    source_status: SourceStatus = SourceStatus.GOVERNMENT_SECONDARY_VERIFIED,
    demand_class: DemandClass = DemandClass.CONFIRMED_DEMAND,
    capability_status: CapabilityStatus = CapabilityStatus.IMPLEMENTED_IN_SOFTWARE,
) -> RequirementDeltaRecord:
    return RequirementDeltaRecord(
        requirement_delta_id=requirement_id, demand_class=demand_class,
        source=SourceRecord(title=title, agency=agency, url=url,
            solicitation_or_topic=topic, source_status=source_status,
            retrieved_utc="2026-08-26T00:00:00Z"),
        statement=statement,
        recurrence="Release-5 capture and reusable PRE readiness requirement",
        forecast_horizon=ForecastHorizon.D0_90, affected_lanes=lanes,
        existing_capability=["claims-controlled software qualification scaffold"],
        capability_status=[capability_status],
        missing_capability=missing,
        experiment_or_demonstration_needed=["frozen synthetic reproducible benchmark"],
        evidence_target=["machine-readable qualification bundle"],
        claims_boundary=claims,
    )


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def build_all(*, fixtures: Path, out: Path, software_commit: str, executed_utc: str, operator: str) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    apnt_fixture = _load(fixtures / "apnt_destroyer_strait_v1.json")
    mbse_fixture = _load(fixtures / "mbse_legacy_fixture_v1.json")
    ietm_fixture = _load(fixtures / "ietm_synthetic_v1.json")
    ade_fixture = _load(fixtures / "ade_symbolic_v1.json")
    mission_fixture = _load(fixtures / "mission_replay_synthetic_v1.json")
    fusion_fixture = _load(fixtures / "sensor_fusion_synthetic_v1.json")
    rf_fixture = _load(fixtures / "rf_sparams_synthetic_v1.json")
    cbm_fixture = _load(fixtures / "cbm_twin_synthetic_v1.json")
    mfg_fixture = _load(fixtures / "manufacturing_thread_synthetic_v1.json")

    apnt_requirement = _requirement(requirement_id="PRE-RD-2026-0001", title="NAVWAR APNT operational awareness and decision-support target", agency="NAVWAR", url="https://navysbir.us/n26_5/DON26BX05-NP004.htm", topic="DON26BX05-NP004", statement="Demonstrate modular APNT operational-awareness software using representative synthetic data while retaining source confidence/provenance and bounded recovery decision support.", lanes=["APNT","C2","mission assurance","DDIL"], missing=["ASPN/pntOS/GPNTS validation","Navy operator validation"], claims=["No physical APNT, shipboard, sensor-accuracy, or Navy operator-performance claim"])
    mbse_requirement = _requirement(requirement_id="PRE-RD-2026-0002", title="NAVSEA AI-to-MBSE reconstruction target", agency="NAVSEA", url="https://navysbir.us/n26_5/DON26BX05-NP003.htm", topic="DON26BX05-NP003", statement="Transform heterogeneous legacy artifacts into a source-traceable system model and measure reconstruction quality against known ground truth.", lanes=["MBSE","digital engineering","configuration provenance"], missing=["general document understanding","SysML/Cameo interoperability","Navy data validation"], claims=["No Navy/Aegis, Cameo/MagicDraw, classified-system, or production reconstruction claim"])
    ietm_requirement = _requirement(requirement_id="PRE-RD-2026-0003", title="NAVAIR technical-data/IETM transformation target", agency="NAVAIR", url="https://navysbir.us/n26_5/DON26BZ05-NV078.htm", topic="DON26BZ05-NV078", statement="Transform technical data while preserving source structure and distribution markings through a governed, testable conversion pipeline.", lanes=["technical data","IETM","provenance","configuration custody"], missing=["S1000D/MIL-standard validation","Navy viewer compatibility","production accuracy"], claims=["No S1000D, MIL-standard, Navy viewer, or production conversion claim"])
    ade_requirement = _requirement(requirement_id="PRE-RD-2026-0012", title="DARPA SPEED DIAL automated algorithm-discovery readiness target", agency="DARPA", url="https://www.darpa.mil/research/programs/speed-dial", topic="DPA26TZ05-DV003", statement="Develop measurable automated interpretable algorithm-discovery capability while preserving the distinction between a synthetic internal benchmark and the topic's pre-existing D2P2/SOTA evidence gate.", lanes=["ADE-G","AI governance","digital engineering","simulation governance"], missing=["SOTA benchmark","real engineering workflow integration","D2P2 prior discovery evidence","research-institution partner"], claims=["No SOTA, scientific novelty, real-engineering superiority, or SPEED DIAL D2P2 eligibility claim"], source_status=SourceStatus.OFFICIAL_SOURCE_VERIFIED)
    mission_requirement = _requirement(requirement_id="PRE-RD-2026-0013", title="Navy automated post-mission debrief and replanning readiness target", agency="Navy", url="https://www.sbir.gov/", topic="DON26BZ05-NV074", statement="Preserve mission events, reconstruct evidence, derive bounded findings, and generate traceable follow-on COA proposals that remain subject to identified human authorization.", lanes=["OVERWATCH","ECHO","PRIME","autonomy governance","mission replay"], missing=["operational CCA/UAS mission data","validated causal reasoning","operator effectiveness","platform integration"], claims=["No operational CCA/UAS, causal-AI, autonomous replanning, or Navy mission-performance claim"])
    fusion_requirement = _requirement(requirement_id="PRE-RD-2026-0014", title="Distributed sensing and multi-sensor fusion readiness target", agency="Worldshepherd PRE", url="internal://pre/sensor-fusion-v1", topic="PREDICTIVE-DISTRIBUTED-SENSING", statement="Establish a deterministic source-traceable multi-sensor fusion baseline reusable across distributed sensing, edge AI and autonomy opportunities.", lanes=["distributed sensing","sensor fusion","ECHO","edge AI","mission assurance"], missing=["operational sensor data","validated multi-target association","edge deployment","partner sensor interfaces"], claims=["Synthetic 2-D point observations only; no operational sensor-fusion claim"], source_status=SourceStatus.PRIMARY_TECHNICAL_SOURCE, demand_class=DemandClass.EMERGING_DEMAND)
    rf_requirement = _requirement(requirement_id="PRE-RD-2026-0015", title="RF/metasurface simulation-to-measurement readiness target", agency="Worldshepherd PRE", url="internal://pre/rf-discrepancy-v1", topic="PREDICTIVE-RF-VALIDATION", statement="Quantify simulation-to-measurement discrepancy and uncertainty before any physical RF or metasurface performance claim.", lanes=["RF","metasurfaces","simulation governance","qualification evidence"], missing=["fabricated coupon","VNA/chamber measurement","independent physical validation"], claims=["Synthetic S11-like values only; no physical RF performance claim"], source_status=SourceStatus.PRIMARY_TECHNICAL_SOURCE, demand_class=DemandClass.EMERGING_DEMAND, capability_status=CapabilityStatus.SIMULATED_ONLY)
    cbm_requirement = _requirement(requirement_id="PRE-RD-2026-0016", title="CBM+ and digital-twin readiness target", agency="Worldshepherd PRE", url="internal://pre/cbm-v1", topic="PREDICTIVE-CBM", statement="Establish source-traceable synthetic health-state classification before predictive-maintenance or RUL claims.", lanes=["CBM+","digital twins","maintenance","ECHO"], missing=["real asset telemetry","failure labels","RUL validation","maintainer validation"], claims=["Synthetic telemetry only; no predictive-maintenance claim"], source_status=SourceStatus.PRIMARY_TECHNICAL_SOURCE, demand_class=DemandClass.EMERGING_DEMAND)
    mfg_requirement = _requirement(requirement_id="PRE-RD-2026-0017", title="DED/manufacturing digital-thread readiness target", agency="Worldshepherd PRE", url="internal://pre/mfg-thread-v1", topic="PREDICTIVE-MFG-QUALIFICATION", statement="Establish machine-readable material/process/build/specimen provenance before physical manufacturing qualification claims.", lanes=["DED","additive manufacturing","digital thread","manufacturing provenance"], missing=["physical coupon","machine calibration evidence","property measurement","partner lab validation"], claims=["Digital thread only; no alloy/process/property claim"], source_status=SourceStatus.PRIMARY_TECHNICAL_SOURCE, demand_class=DemandClass.EMERGING_DEMAND)

    bundles = {
        "apnt": qualify_synthetic_apnt_timeline(fixture=apnt_fixture, requirement=apnt_requirement, software_commit=software_commit, executed_utc=executed_utc, operator=operator),
        "mbse": qualify_synthetic_mbse(fixture=mbse_fixture, requirement=mbse_requirement, software_commit=software_commit, executed_utc=executed_utc, operator=operator),
        "ietm": qualify_synthetic_ietm(fixture=ietm_fixture, requirement=ietm_requirement, software_commit=software_commit, executed_utc=executed_utc, operator=operator),
        "ade": qualify_synthetic_discovery(fixture=ade_fixture, requirement=ade_requirement, software_commit=software_commit, executed_utc=executed_utc, operator=operator),
        "mission": qualify_synthetic_mission_replay(fixture=mission_fixture, requirement=mission_requirement, software_commit=software_commit, executed_utc=executed_utc, operator=operator),
        "fusion": qualify_synthetic_sensor_fusion(fixture=fusion_fixture, requirement=fusion_requirement, software_commit=software_commit, executed_utc=executed_utc, operator=operator),
        "rf": qualify_synthetic_rf_discrepancy(fixture=rf_fixture, requirement=rf_requirement, software_commit=software_commit, executed_utc=executed_utc, operator=operator),
        "cbm": qualify_synthetic_cbm(fixture=cbm_fixture, requirement=cbm_requirement, software_commit=software_commit, executed_utc=executed_utc, operator=operator),
        "manufacturing": qualify_synthetic_manufacturing_thread(fixture=mfg_fixture, requirement=mfg_requirement, software_commit=software_commit, executed_utc=executed_utc, operator=operator),
    }
    ddil_messages = [Envelope(sequence=i, source="synthetic-apnt-node", payload={"state_index": i}, timestamp_ms=i*100) for i in range(1,7)]
    bundles["ddil"] = run_ddil_campaign(messages=ddil_messages, requirement=apnt_requirement, software_commit=software_commit, executed_utc=executed_utc, operator=operator)

    custody_store = EvidenceStore(out / "echo_store")
    custody_digests: dict[str,str] = {}
    for name, bundle in bundles.items():
        _write(out / f"{name}_qualification_bundle.json", bundle)
        custody_digests[name] = custody_store.put_bundle(bundle)

    failures = {name:[record["test_id"] for record in bundle["evidence"] if record["result"] != "PASS"] for name,bundle in bundles.items()}
    fixture_values = {"apnt":apnt_fixture,"mbse":mbse_fixture,"ietm":ietm_fixture,"ade":ade_fixture,"mission":mission_fixture,"fusion":fusion_fixture,"rf":rf_fixture,"cbm":cbm_fixture,"manufacturing":mfg_fixture}
    index = {
        "schema":"WS-PRE-QUALIFICATION-INDEX-V1",
        "software_commit":software_commit,"executed_utc":executed_utc,"operator":operator,
        "bundle_digests":{name:bundle["bundle_digest"] for name,bundle in bundles.items()},
        "custody_digests":custody_digests,"custody_verification":custody_store.verify_all(),
        "fixture_digests":{name:canonical_digest(value) for name,value in fixture_values.items()},
        "failures":failures,
        "claims_boundary":["This index records synthetic/internal software evidence only.","The ECHO-style store is a local integrity/custody mechanism, not a government records system or legal chain-of-custody service.","RF evidence uses synthetic prediction/measurement values and remains SIMULATED_ONLY.","CBM+ evidence does not establish predictive maintenance or RUL performance.","Manufacturing evidence establishes digital lineage only and no physical material/process performance.","Passing bundles do not establish physical, platform, government, certification, compliance, clearance, operational, SOTA, or partner validation."],
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
    index = build_all(fixtures=args.fixtures,out=args.out,software_commit=args.software_commit,executed_utc=args.executed_utc,operator=args.operator)
    failed = any(index["failures"].values()) or not all(index["custody_verification"].values())
    print(json.dumps(index, sort_keys=True))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

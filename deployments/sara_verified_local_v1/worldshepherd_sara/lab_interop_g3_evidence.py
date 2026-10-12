from __future__ import annotations
import hashlib, json
from dataclasses import dataclass, asdict
from typing import Any

QUALIFICATION_ID = "WS-LAB-INTEROP-01"
QUALIFICATION_VERSION = "G3-R1"
CAPABILITY_STATUS = "PRE_PHYSICAL_HIL_READINESS"

@dataclass(frozen=True)
class FaultPlan:
    fault_id: str
    description: str
    injection_mode: str
    physical_injection_allowed: bool
    expected_disposition: str

SAFE_FAULT_MATRIX = (
    FaultPlan("G3F1","sensor disconnect","switchable",True,"SAFE_HALT_OR_BOUNDED_RECOVERY"),
    FaultPlan("G3F2","actuator stuck-on","emulated_only",False,"SAFE_HALT"),
    FaultPlan("G3F3","actuator stuck-off","emulated_only",False,"SAFE_HALT_OR_RECOVERY"),
    FaultPlan("G3F4","command saturation","software_limit",True,"DENY_OR_CLAMP_WITH_EVIDENCE"),
    FaultPlan("G3F5","measurement bias","software_or_calibrator",True,"DETECT_OR_FLAG_UNCERTAIN"),
    FaultPlan("G3F6","timestamp drift","software_clock_offset",True,"DETECT_AND_QUARANTINE"),
    FaultPlan("G3F7","communications loss during partial execution","transport_fault",True,"SAFE_HALT"),
    FaultPlan("G3F8","adapter restart","process_restart",True,"RESYNC_BEFORE_RESUME"),
    FaultPlan("G3F9","power interruption","emulated_only",False,"SAFE_STATE_ON_RESTORE"),
    FaultPlan("G3F10","unit/semantic mismatch","software_payload",True,"DENY"),
)

def _digest(value: Any) -> str:
    raw=json.dumps(value,sort_keys=True,separators=(",",":")).encode()
    return "sha256:"+hashlib.sha256(raw).hexdigest()

def new_run_record(*,run_id:str,operator_id:str,hardware_ids:list[str],software_commit:str,calibration_ids:list[str],manifest_digest:str)->dict[str,Any]:
    return {
        "qualification_id":QUALIFICATION_ID,
        "qualification_version":QUALIFICATION_VERSION,
        "capability_status":CAPABILITY_STATUS,
        "run_id":run_id,"operator_id":operator_id,"hardware_ids":hardware_ids,
        "software_commit":software_commit,"calibration_ids":calibration_ids,
        "manifest_digest":manifest_digest,"events":[],"faults_executed":[],
        "estop_tested":False,"physical_io_observed":False,"run_complete":False,
        "claims":{"bounded_local_physical_evidence":False,"external_validation":False,
                  "opc_ua_lads_conformance":False,"sila2_conformance":False,
                  "production_security":False},
    }

def append_event(record:dict[str,Any],*,kind:str,payload:dict[str,Any])->None:
    record["events"].append({"kind":kind,"payload":payload})

def record_fault_result(record:dict[str,Any],*,fault_id:str,observed_disposition:str,evidence:dict[str,Any])->None:
    plan=next((p for p in SAFE_FAULT_MATRIX if p.fault_id==fault_id),None)
    if plan is None:
        raise ValueError(f"unknown fault_id: {fault_id}")
    record["faults_executed"].append({
        "fault_id":fault_id,
        "expected_disposition":plan.expected_disposition,
        "observed_disposition":observed_disposition,
        "evidence":evidence,
    })

def finalize_run(record:dict[str,Any],*,estop_tested:bool,physical_io_observed:bool)->dict[str,Any]:
    record["estop_tested"]=estop_tested
    record["physical_io_observed"]=physical_io_observed
    record["run_complete"]=True
    checks={
        "hardware_ids":bool(record["hardware_ids"]),
        "calibration_ids":bool(record["calibration_ids"]),
        "manifest_digest":str(record["manifest_digest"]).startswith("sha256:"),
        "events":bool(record["events"]),
        "estop_tested":estop_tested,
        "physical_io_observed":physical_io_observed,
    }
    bounded=all(checks.values())
    record["claims"]["bounded_local_physical_evidence"]=bounded
    record["mandatory_checks"]=checks
    record["evidence_digest"]=_digest(record)
    return record

def readiness_only_record()->dict[str,Any]:
    record=new_run_record(run_id="DRY-RUN",operator_id="none",hardware_ids=[],software_commit="unbound",calibration_ids=[],manifest_digest="")
    append_event(record,kind="readiness_check",payload={"physical_execution":False})
    return finalize_run(record,estop_tested=False,physical_io_observed=False)

def fault_matrix()->list[dict[str,Any]]:
    return [asdict(x) for x in SAFE_FAULT_MATRIX]

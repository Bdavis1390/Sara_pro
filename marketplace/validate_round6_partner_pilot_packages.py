#!/usr/bin/env python3
import argparse, json
from pathlib import Path

EXPECTED_IDS = ["WS-MKT-035", "WS-MKT-036", "WS-MKT-037", "WS-MKT-038", "WS-MKT-039"]
REQUIRED_GATES = [
    "target_authorized_data_access_record",
    "target_authorized_bounded_pilot_record",
    "measured_effect_size_against_partner_defined_ground_truth",
    "security_compliance_applicability_review",
    "independent_reproduction_or_review",
]
REQUIRED_METRICS = {
    "injected_failure_detection_recall_pct",
    "false_release_pct",
    "in_scope_trace_coverage_pct",
    "evidence_retrieval_p95_seconds",
    "known_discrepancy_detection_pct",
    "clean_environment_reproduction_pct",
}


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--registry", required=True)
    ap.add_argument("--output", required=True)
    args=ap.parse_args()
    d=json.loads(Path(args.registry).read_text())
    errors=[]

    if d.get("schema") != "WS-MARKETPLACE-ROUND6-PARTNER-PILOT-PACKAGES-V1": errors.append("schema")
    if d.get("status") != "INTERNAL_PREPARATION_ONLY": errors.append("status")
    if d.get("contact_gate_effect") != "NONE": errors.append("contact_gate_effect")
    if d.get("required_external_gate_evidence") != REQUIRED_GATES: errors.append("required_external_gate_evidence")
    metrics=d.get("common_acceptance_targets") or {}
    if set(metrics) != REQUIRED_METRICS: errors.append("common_acceptance_targets")
    for name, spec in metrics.items():
        if spec.get("status") != "TARGET_DEFINITION_NOT_ACHIEVED_CLAIM":
            errors.append(f"metric_claim_status:{name}")

    pkgs=d.get("packages") or []
    ids=[p.get("target_id") for p in pkgs]
    if ids != EXPECTED_IDS: errors.append("target_ids")
    if len(ids) != len(set(ids)): errors.append("duplicate_ids")

    for p in pkgs:
        tid=p.get("target_id", "unknown")
        required=["organization","public_problem_hypothesis","partner_data_minimum","control_mapping","pilot_scope","injected_failures","target_specific_metrics","no_go","current_external_gate_state"]
        for key in required:
            if not p.get(key): errors.append(f"{tid}:missing:{key}")
        if p.get("current_external_gate_state") != "OPEN": errors.append(f"{tid}:external_gate_state")
        if len(p.get("partner_data_minimum") or []) < 6: errors.append(f"{tid}:partner_data_minimum")
        if len(p.get("control_mapping") or {}) < 4: errors.append(f"{tid}:control_mapping")
        if len(p.get("injected_failures") or []) < 7: errors.append(f"{tid}:injected_failures")
        if len(p.get("target_specific_metrics") or []) < 4: errors.append(f"{tid}:target_specific_metrics")
        if len(p.get("no_go") or []) < 4: errors.append(f"{tid}:no_go")

    report={
        "schema":"WS-MARKETPLACE-ROUND6-PARTNER-PILOT-PACKAGE-REPORT-V1",
        "result":"PASS" if not errors else "FAIL",
        "target_count":len(pkgs),
        "target_ids":ids,
        "common_acceptance_target_count":len(metrics),
        "required_external_gate_evidence_count":len(d.get("required_external_gate_evidence") or []),
        "external_gate_closures":0,
        "contact_gate_effect":d.get("contact_gate_effect"),
        "errors":errors,
        "claims_boundary":"PASS validates pilot-package completeness and claims controls only. Acceptance thresholds are definitions for future target-authorized measurement, not achieved target results, remediation probability, compliance, safety, performance or contact authorization."
    }
    Path(args.output).parent.mkdir(parents=True,exist_ok=True)
    Path(args.output).write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))
    raise SystemExit(0 if not errors else 1)

if __name__=="__main__": main()

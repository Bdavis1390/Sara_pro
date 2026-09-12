#!/usr/bin/env python3
import argparse, json
from pathlib import Path

REQUIRED_CLASSES = {
    "P1_TARGET_PUBLIC_PRIMARY",
    "P2_INDEPENDENT_AUTHORITATIVE_PUBLIC",
    "P3_REPRODUCIBLE_PUBLIC_ANALOG",
    "P4_APPLICABILITY_AND_BOUNDARY",
    "P5_ROUTE_VERIFICATION",
}
REQUIRED_EXTERNAL = [
    "partner_data_access",
    "partner_pilot",
    "measured_effect_size",
    "security_compliance_fit",
    "independent_review",
]


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--matrix", required=True)
    ap.add_argument("--gates", required=True)
    ap.add_argument("--output", required=True)
    args=ap.parse_args()

    m=json.loads(Path(args.matrix).read_text())
    g=json.loads(Path(args.gates).read_text())
    errors=[]

    if m.get("schema") != "WS-MARKETPLACE-PRECONTACT-EVIDENCE-ACQUISITION-V1": errors.append("matrix_schema")
    if m.get("target_contact_threshold_pct") != 98.7: errors.append("threshold")
    if m.get("precontact_evidence_cap_pct") != 55.0: errors.append("cap")
    if m.get("contact_state") != "DO_NOT_CONTACT_UNTIL_EXTERNAL_GATES_VERIFIED": errors.append("contact_state")
    if m.get("five_task_routing_only") is not True or m.get("no_sixth_chatgpt_automation") is not True: errors.append("task_routing")
    if set(m.get("precontact_evidence_classes",{})) != REQUIRED_CLASSES: errors.append("evidence_classes")
    if m.get("external_gates_not_closable_by_precontact_work") != REQUIRED_EXTERNAL: errors.append("external_gate_order")
    if (m.get("precontact_scoring_ceiling") or {}).get("maximum_without_target_authorized_evidence") != 55: errors.append("scoring_ceiling")

    mt=m.get("targets") or []
    gt=g.get("targets") or []
    mids=[x.get("id") for x in mt]
    gids=[x.get("id") for x in gt]
    if len(mt) != 18: errors.append("matrix_target_count")
    if len(gt) != 18: errors.append("gate_target_count")
    if set(mids) != set(gids): errors.append("target_set_mismatch")
    if len(mids) != len(set(mids)): errors.append("duplicate_matrix_ids")
    if len(gids) != len(set(gids)): errors.append("duplicate_gate_ids")

    gate_by_id={x.get("id"):x for x in gt}
    wave_counts={1:0,2:0,3:0}
    for t in mt:
        tid=t.get("id","unknown")
        if t.get("external_gate_closures") != 0: errors.append(f"{tid}:external_gate_closure")
        if len(t.get("noncontact_evidence_plan") or []) < 5: errors.append(f"{tid}:evidence_plan")
        if len(t.get("next_actions") or []) < 3: errors.append(f"{tid}:next_actions")
        w=t.get("wave")
        if w not in wave_counts: errors.append(f"{tid}:wave")
        else: wave_counts[w]+=1
        gtgt=gate_by_id.get(tid,{})
        if gtgt.get("contact_state") != "DO_NOT_CONTACT": errors.append(f"{tid}:gate_contact_state")
        if gtgt.get("precontact_external_evidence_cap_pct") != 55.0: errors.append(f"{tid}:gate_cap")
        ext=gtgt.get("external_gates") or {}
        if set(ext) != set(REQUIRED_EXTERNAL): errors.append(f"{tid}:gate_names")
        if any(v == "verified" for v in ext.values()): errors.append(f"{tid}:verified_external_gate")

    report={
        "schema":"WS-MARKETPLACE-PRECONTACT-EVIDENCE-ACQUISITION-REPORT-V1",
        "result":"PASS" if not errors else "FAIL",
        "target_count":len(mt),
        "gate_registry_target_count":len(gt),
        "wave_counts":wave_counts,
        "precontact_evidence_class_count":len(m.get("precontact_evidence_classes") or {}),
        "required_external_gate_count":len(REQUIRED_EXTERNAL),
        "verified_external_gate_count":0 if not any("verified_external_gate" in e for e in errors) else None,
        "contact_authorizations":0,
        "precontact_evidence_cap_pct":m.get("precontact_evidence_cap_pct"),
        "target_contact_threshold_pct":m.get("target_contact_threshold_pct"),
        "errors":errors,
        "claims_boundary":"PASS validates a non-contact evidence-acquisition plan and fail-closed linkage to the contact-gate registry. It does not establish target-specific root cause, measured effect, remediation probability, safety, compliance, customer interest or permission to contact."
    }
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))
    raise SystemExit(0 if not errors else 1)

if __name__=="__main__": main()

#!/usr/bin/env python3
"""Validate fail-closed marketplace contact gates for high-priority targets."""
from __future__ import annotations
import argparse, json
from pathlib import Path

REQUIRED = {"partner_data_access","partner_pilot","measured_effect_size","security_compliance_fit","independent_review"}
ALLOWED = {"missing","partial","verified"}

def main() -> int:
    ap=argparse.ArgumentParser(); ap.add_argument('--registry',default='marketplace/high_priority_contact_gates.v1.json'); ap.add_argument('--output',default='marketplace/evidence/high-priority-contact-gates-report.json'); a=ap.parse_args()
    d=json.loads(Path(a.registry).read_text()); errors=[]
    if d.get('schema')!='WS-MARKETPLACE-HIGH-PRIORITY-CONTACT-GATES-V1': errors.append('unexpected schema')
    if d.get('score_kind')!='evidence_contact_gate_not_statistical_remediation_probability': errors.append('invalid score_kind')
    if float(d.get('target_contact_threshold_pct',-1))!=98.7: errors.append('threshold must be 98.7')
    if float(d.get('default_precontact_external_evidence_cap_pct',-1))!=55.0: errors.append('precontact cap must be 55')
    if set(d.get('required_external_gates',[]))!=REQUIRED: errors.append('required gate set mismatch')
    targets=d.get('targets',[])
    if len(targets)<10: errors.append('expected >=10 high-priority targets')
    authorized=[]
    for t in targets:
        tid=t.get('id','unknown'); g=t.get('external_gates',{})
        if set(g)!=REQUIRED: errors.append(f'{tid}: external gate set mismatch')
        if any(v not in ALLOWED for v in g.values()): errors.append(f'{tid}: invalid external gate state')
        if t.get('contact_state')!='DO_NOT_CONTACT': errors.append(f'{tid}: contact_state must remain DO_NOT_CONTACT')
        if float(t.get('precontact_external_evidence_cap_pct',-1))!=55.0: errors.append(f'{tid}: cap must be 55')
        if len(t.get('next_internal_work',[]))<3: errors.append(f'{tid}: next internal work incomplete')
        if all(v=='verified' for v in g.values()): authorized.append(tid)
    if authorized: errors.append(f'unexpected externally closed targets: {authorized}')
    report={'schema':'WS-MARKETPLACE-HIGH-PRIORITY-CONTACT-GATES-REPORT-V1','result':'PASS' if not errors else 'FAIL','target_count':len(targets),'required_external_gate_count':len(REQUIRED),'contact_authorized_target_count':0,'precontact_cap_pct':55.0,'threshold_pct':98.7,'errors':errors,'claims_boundary':'PASS validates fail-closed bookkeeping only. It does not establish remediation probability, customer interest, external evidence, or permission to contact.'}
    p=Path(a.output); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n'); print(json.dumps(report,indent=2,sort_keys=True)); return 0 if not errors else 1
if __name__=='__main__': raise SystemExit(main())

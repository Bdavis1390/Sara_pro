#!/usr/bin/env python3
import argparse, json
from pathlib import Path
EXPECTED_IDS=["WS-MKT-003","WS-MKT-020","WS-MKT-021","WS-MKT-027","WS-MKT-016","WS-MKT-037","WS-MKT-038","WS-MKT-039"]
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--registry',required=True); ap.add_argument('--gates',required=True); ap.add_argument('--output',required=True); a=ap.parse_args()
    r=json.loads(Path(a.registry).read_text()); g=json.loads(Path(a.gates).read_text()); errors=[]
    if r.get('schema')!='WS-MARKETPLACE-WAVE23-OFFICIAL-ROUTE-REGISTRY-V1': errors.append('schema')
    if r.get('route_used_count')!=0: errors.append('route_used_count')
    if r.get('contact_gate_effect')!='NONE': errors.append('contact_gate_effect')
    if r.get('precontact_evidence_class')!='P5_ROUTE_VERIFICATION': errors.append('evidence_class')
    ts=r.get('targets') or []; ids=[x.get('id') for x in ts]
    if ids!=EXPECTED_IDS: errors.append('ids')
    gb={x.get('id'):x for x in (g.get('targets') or [])}
    for t in ts:
        tid=t.get('id','unknown')
        if t.get('verified_official_route') is not True: errors.append(f'{tid}:not_verified')
        if t.get('route_used') is not False: errors.append(f'{tid}:route_used')
        if not str(t.get('route_url','')).startswith('https://'): errors.append(f'{tid}:route_url')
        if not t.get('route_evidence'): errors.append(f'{tid}:route_evidence')
        gt=gb.get(tid)
        if not gt: errors.append(f'{tid}:not_in_gate_registry'); continue
        if gt.get('contact_state')!='DO_NOT_CONTACT': errors.append(f'{tid}:contact_state')
        if any(v=='verified' for v in (gt.get('external_gates') or {}).values()): errors.append(f'{tid}:external_gate_verified')
    out={'schema':'WS-MARKETPLACE-WAVE23-OFFICIAL-ROUTE-REPORT-V1','result':'PASS' if not errors else 'FAIL','route_target_count':len(ts),'verified_official_route_count':sum(1 for t in ts if t.get('verified_official_route') is True),'route_used_count':sum(1 for t in ts if t.get('route_used') is True),'external_gate_closures':0,'contact_gate_effect':r.get('contact_gate_effect'),'errors':errors,'claims_boundary':'PASS verifies official public route records and non-use only. It does not authorize outreach, establish supplier/partner eligibility, target interest, remediation probability or close any external gate.'}
    Path(a.output).parent.mkdir(parents=True,exist_ok=True); Path(a.output).write_text(json.dumps(out,indent=2)+'\n'); print(json.dumps(out,indent=2)); raise SystemExit(0 if not errors else 1)
if __name__=='__main__': main()

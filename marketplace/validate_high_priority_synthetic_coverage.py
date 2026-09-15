#!/usr/bin/env python3
import argparse,json
from pathlib import Path

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--coverage',required=True); ap.add_argument('--gates',required=True); ap.add_argument('--output',required=True); a=ap.parse_args()
    c=json.loads(Path(a.coverage).read_text()); g=json.loads(Path(a.gates).read_text()); errors=[]
    if c.get('schema')!='WS-MARKETPLACE-HIGH-PRIORITY-SYNTHETIC-COVERAGE-V1': errors.append('schema')
    if c.get('contact_gate_effect')!='NONE': errors.append('contact_gate_effect')
    if c.get('external_gate_closures')!=0: errors.append('external_gate_closures')
    suites=c.get('suites') or []; ids=[]; fixtures=0; passes=0
    for s in suites:
        ids.extend(s.get('target_ids') or []); fixtures+=s.get('fixture_count',0); passes+=s.get('pass_count',0)
        if s.get('fixture_count')!=s.get('pass_count'): errors.append(f"{s.get('suite_id')}:not_all_pass")
        for h in ['fixtures_sha256','results_sha256','report_sha256']:
            if len(str(s.get(h,'')))!=64: errors.append(f"{s.get('suite_id')}:{h}")
    gate_ids=[x.get('id') for x in (g.get('targets') or [])]
    if len(ids)!=18 or len(set(ids))!=18: errors.append('coverage_target_count')
    if set(ids)!=set(gate_ids): errors.append('coverage_gate_set_mismatch')
    if fixtures!=162 or passes!=162: errors.append('fixture_totals')
    sm=c.get('summary') or {}
    expected={'target_count':18,'covered_target_count':18,'fixture_count':162,'pass_count':162,'per_target_fixture_count':9,'coverage_pct':100.0}
    for k,v in expected.items():
        if sm.get(k)!=v: errors.append(f'summary:{k}')
    for t in (g.get('targets') or []):
        if t.get('contact_state')!='DO_NOT_CONTACT': errors.append(f"{t.get('id')}:contact_state")
        if any(v=='verified' for v in (t.get('external_gates') or {}).values()): errors.append(f"{t.get('id')}:external_gate_verified")
    out={'schema':'WS-MARKETPLACE-HIGH-PRIORITY-SYNTHETIC-COVERAGE-REPORT-V1','result':'PASS' if not errors else 'FAIL','target_count':18,'covered_target_count':len(set(ids)),'fixture_count':fixtures,'pass_count':passes,'coverage_pct':100.0 if len(set(ids))==18 else round(len(set(ids))/18*100,2),'external_gate_closures':0,'contact_authorizations':0,'contact_gate_effect':c.get('contact_gate_effect'),'errors':errors,'claims_boundary':'PASS validates deterministic internal fixture coverage bookkeeping only. It does not measure target systems or establish remediation probability, production effectiveness, safety, compliance, customer interest or permission to contact.'}
    Path(a.output).parent.mkdir(parents=True,exist_ok=True); Path(a.output).write_text(json.dumps(out,indent=2)+'\n'); print(json.dumps(out,indent=2)); raise SystemExit(0 if not errors else 1)
if __name__=='__main__': main()

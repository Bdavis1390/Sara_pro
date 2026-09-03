#!/usr/bin/env python3
"""Fail-closed validator for marketplace scan round 5."""
from __future__ import annotations
import argparse, json
from pathlib import Path

ALLOWED = {"DO_NOT_CONTACT_NEW_LANE", "WATCH_ONLY"}

def main() -> int:
    ap=argparse.ArgumentParser(); ap.add_argument('--registry',default='marketplace/market_scan_round5_20260903.json'); ap.add_argument('--output',default='marketplace/evidence/marketplace-round5-report.json'); a=ap.parse_args()
    d=json.loads(Path(a.registry).read_text()); errors=[]
    if d.get('schema')!='WS-MARKETPLACE-SCAN-ROUND5-V1': errors.append('unexpected schema')
    if d.get('score_kind')!='market_prioritization_not_probability_of_remediation_or_award': errors.append('invalid score_kind')
    if float(d.get('default_contact_threshold_pct',-1))!=98.7: errors.append('threshold must be 98.7')
    if float(d.get('default_precontact_cap_pct',-1))!=55.0: errors.append('precontact cap must be 55')
    if 'do not create a sixth' not in d.get('task_routing','').lower(): errors.append('must remain in five existing tasks')
    targets=d.get('new_targets',[])
    if not isinstance(targets,list) or len(targets)!=5: errors.append('round5 must contain exactly five targets'); targets=targets if isinstance(targets,list) else []
    seen=set(); active=watch=0; high=[]
    for t in targets:
        tid=str(t.get('id',''))
        if not tid or tid in seen: errors.append(f'invalid/duplicate id {tid!r}')
        seen.add(tid)
        score=t.get('market_priority_score')
        if not isinstance(score,(int,float)) or not 0<=float(score)<=100: errors.append(f'{tid}: invalid priority score')
        elif float(score)>=90: high.append(tid)
        state=t.get('contact_state')
        if state not in ALLOWED: errors.append(f'{tid}: invalid contact state')
        elif state=='WATCH_ONLY': watch+=1
        else: active+=1
        if float(t.get('precontact_cap_pct',-1))!=55.0: errors.append(f'{tid}: cap must remain 55')
        if len(t.get('solution_wedge',[]))<5: errors.append(f'{tid}: solution wedge incomplete')
        if not t.get('public_sources'): errors.append(f'{tid}: public sources required')
        if not str(t.get('notes','')).strip(): errors.append(f'{tid}: notes required')
    boundary=d.get('claims_boundary','').lower()
    for term in ['scores rank attention only','do not establish production','no new target is contact-authorized']:
        if term not in boundary: errors.append(f'claims boundary missing {term!r}')
    report={'schema':'WS-MARKETPLACE-ROUND5-REPORT-V1','result':'PASS' if not errors else 'FAIL','target_count':len(targets),'active_solution_development_target_count':active,'watch_only_target_count':watch,'high_priority_90_plus_ids':high,'new_contact_authorizations':0,'default_contact_threshold_pct':d.get('default_contact_threshold_pct'),'default_precontact_cap_pct':d.get('default_precontact_cap_pct'),'errors':errors,'claims_boundary':'PASS validates scan structure/contact controls only; it does not establish target-specific root cause, production effectiveness, remediation probability, interest, contracting, adoption, compliance or permission to contact.'}
    p=Path(a.output); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n'); print(json.dumps(report,indent=2,sort_keys=True)); return 0 if not errors else 1
if __name__=='__main__': raise SystemExit(main())

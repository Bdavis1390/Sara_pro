#!/usr/bin/env python3
import argparse, hashlib, json
from pathlib import Path

TARGETS = ["WS-MKT-035","WS-MKT-036","WS-MKT-037","WS-MKT-038","WS-MKT-039"]

BASE = {
    "approved": True,
    "sod_conflict": False,
    "stale_config": False,
    "source_known": True,
    "change_authorized": True,
    "digest_present": True,
    "authority_valid": True,
    "restore_verified": True,
}

CASES = {
    "valid_baseline": ({}, True, "accept"),
    "missing_approval": ({"approved": False}, False, "reject"),
    "sod_conflict": ({"sod_conflict": True}, False, "reject"),
    "stale_configuration": ({"stale_config": True}, False, "reject"),
    "unknown_source": ({"source_known": False}, False, "reject"),
    "unauthorized_change": ({"change_authorized": False}, False, "reject"),
    "missing_digest": ({"digest_present": False}, False, "reject"),
    "invalid_authority": ({"authority_valid": False}, False, "reject"),
    "verified_restore": ({}, True, "accept"),
}

def evaluate(r):
    return bool(
        r["approved"] and
        not r["sod_conflict"] and
        not r["stale_config"] and
        r["source_known"] and
        r["change_authorized"] and
        r["digest_present"] and
        r["authority_valid"] and
        r["restore_verified"]
    )

def stable_hash(obj):
    b=json.dumps(obj,sort_keys=True,separators=(",",":")).encode()
    return hashlib.sha256(b).hexdigest()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",required=True)
    args=ap.parse_args()

    fixtures=[]
    results=[]
    by_target={}
    for tid in TARGETS:
        passed=0
        for cname,(mods,expected,expected_action) in CASES.items():
            rec=dict(BASE)
            rec.update(mods)
            rec["target_id"]=tid
            rec["case"]=cname
            fixtures.append(rec)
            actual=evaluate(rec)
            action="accept" if actual else "reject"
            ok=(actual==expected and action==expected_action)
            passed += int(ok)
            results.append({"target_id":tid,"case":cname,"expected":expected_action,"actual":action,"pass":ok})
        by_target[tid]={"fixture_count":len(CASES),"pass_count":passed}

    fixture_count=len(fixtures)
    pass_count=sum(1 for r in results if r["pass"])
    report={
        "schema":"WS-MARKETPLACE-ROUND6-SYNTHETIC-STRESS-V1",
        "result":"PASS" if pass_count==fixture_count else "FAIL",
        "target_count":len(TARGETS),
        "fixture_count":fixture_count,
        "pass_count":pass_count,
        "by_target":by_target,
        "fixtures_sha256":stable_hash(fixtures),
        "results_sha256":stable_hash(results),
        "contact_gate_effect":"NONE",
        "external_gate_updates":{tid:"none" for tid in TARGETS},
        "claims_boundary":"Synthetic stress validates deterministic fail-closed behavior of the encoded evidence-control pattern only. It does not establish target-specific production effectiveness, remediation probability, safety, cybersecurity, compliance, customer interest or permission to contact."
    }
    Path(args.output).parent.mkdir(parents=True,exist_ok=True)
    Path(args.output).write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))
    raise SystemExit(0 if report["result"]=="PASS" else 1)

if __name__=="__main__":
    main()

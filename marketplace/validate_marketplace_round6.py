#!/usr/bin/env python3
import argparse, json
from pathlib import Path

EXPECTED_SCHEMA = "WS-MARKETPLACE-SCAN-ROUND6-V1"
ALLOWED_CONTACT_STATES = {"DO_NOT_CONTACT_NEW_LANE", "WATCH_ONLY"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--registry", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    data = json.loads(Path(args.registry).read_text())
    errors = []

    if data.get("schema") != EXPECTED_SCHEMA:
        errors.append("schema")
    if data.get("default_contact_threshold_pct") != 98.7:
        errors.append("contact_threshold")
    if data.get("default_precontact_cap_pct") != 55.0:
        errors.append("precontact_cap")

    targets = data.get("new_targets") or []
    if len(targets) != 5:
        errors.append("target_count")

    ids = [t.get("id") for t in targets]
    if len(ids) != len(set(ids)):
        errors.append("duplicate_ids")
    if ids != ["WS-MKT-035", "WS-MKT-036", "WS-MKT-037", "WS-MKT-038", "WS-MKT-039"]:
        errors.append("target_ids")

    active = 0
    watch = 0
    high = []
    contact_auth = 0
    for t in targets:
        required = ["id", "organization", "sector", "signal_class", "market_priority_score", "observed_signal", "solution_wedge", "public_sources", "contact_state", "precontact_cap_pct", "notes"]
        missing = [k for k in required if k not in t]
        if missing:
            errors.append(f"{t.get('id','unknown')}:missing:{','.join(missing)}")
            continue
        if t["contact_state"] not in ALLOWED_CONTACT_STATES:
            errors.append(f"{t['id']}:contact_state")
        if t["precontact_cap_pct"] != 55.0:
            errors.append(f"{t['id']}:cap")
        if not isinstance(t["market_priority_score"], (int, float)) or not 0 <= t["market_priority_score"] <= 100:
            errors.append(f"{t['id']}:score")
        if t["market_priority_score"] >= 90:
            high.append(t["id"])
        if t["contact_state"] == "WATCH_ONLY":
            watch += 1
        else:
            active += 1
        if "CONTACT_AUTHORIZED" in t["contact_state"]:
            contact_auth += 1
        if len(t["solution_wedge"]) < 4:
            errors.append(f"{t['id']}:solution_wedge")
        if len(t["public_sources"]) < 1:
            errors.append(f"{t['id']}:sources")

    report = {
        "schema": "WS-MARKETPLACE-ROUND6-REPORT-V1",
        "result": "PASS" if not errors else "FAIL",
        "target_count": len(targets),
        "active_solution_development_target_count": active,
        "watch_only_target_count": watch,
        "high_priority_90_plus_ids": high,
        "new_contact_authorizations": contact_auth,
        "default_contact_threshold_pct": data.get("default_contact_threshold_pct"),
        "default_precontact_cap_pct": data.get("default_precontact_cap_pct"),
        "errors": errors,
        "claims_boundary": "PASS validates scan structure/contact controls only; it does not establish target-specific root cause, production effectiveness, remediation probability, interest, contracting, adoption, compliance or permission to contact."
    }
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if not errors else 1)

if __name__ == "__main__":
    main()

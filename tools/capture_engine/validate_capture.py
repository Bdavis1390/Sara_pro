#!/usr/bin/env python3
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def parse_deadline(value):
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        dt = datetime.fromisoformat(text + "T23:59:59")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def deadline_flag(deadline, now, critical_days, urgent_days):
    if deadline is None:
        return "NONE"
    delta = (deadline - now).total_seconds() / 86400.0
    if delta < 0:
        return "PAST_DUE"
    if delta <= critical_days:
        return "CRITICAL"
    if delta <= urgent_days:
        return "URGENT"
    return "NORMAL"


def validate(policy, ledger, now):
    required = policy["required_fields"]
    critical_days = policy["deadline_flags"]["CRITICAL_DAYS"]
    urgent_days = policy["deadline_flags"]["URGENT_DAYS"]
    valid_tiers = set(policy["capture_tiers"])
    valid_routes = set(policy["routing_states"])

    errors = []
    rows = []

    for index, opportunity in enumerate(ledger.get("opportunities", []), start=1):
        opportunity_id = opportunity.get("opportunity_id", "UNKNOWN")
        missing = [key for key in required if key not in opportunity]
        if missing:
            errors.append(f"{index}:{opportunity_id}: missing {missing}")

        score = opportunity.get("capture_score")
        if not isinstance(score, (int, float)) or not 0 <= score <= 100:
            errors.append(f"{index}:{opportunity_id}: invalid capture_score")

        if opportunity.get("capture_tier") not in valid_tiers:
            errors.append(f"{index}:{opportunity_id}: invalid capture_tier")

        if opportunity.get("routing_state") not in valid_routes:
            errors.append(f"{index}:{opportunity_id}: invalid routing_state")

        deadline = parse_deadline(opportunity.get("deadline"))
        rows.append(
            {
                "opportunity_id": opportunity_id,
                "capture_tier": opportunity.get("capture_tier"),
                "capture_score": score,
                "routing_state": opportunity.get("routing_state"),
                "deadline_flag": deadline_flag(deadline, now, critical_days, urgent_days),
                "deadline": opportunity.get("deadline"),
            }
        )

    urgency_order = {"CRITICAL": 0, "URGENT": 1, "NORMAL": 2, "NONE": 3, "PAST_DUE": 4}
    rows.sort(
        key=lambda row: (
            0 if row["capture_tier"] == "TIER_0" else 1,
            urgency_order.get(row["deadline_flag"], 5),
            -(row["capture_score"] or 0),
        )
    )
    return errors, rows


def main():
    parser = argparse.ArgumentParser(description="Validate and prioritize a Worldshepherd capture ledger.")
    parser.add_argument("ledger")
    parser.add_argument("--policy", default="config/worldshepherd_capture_engine_v1_1.json")
    parser.add_argument("--now", help="ISO-8601 time used for deterministic deadline classification")
    args = parser.parse_args()

    policy = json.loads(Path(args.policy).read_text())
    ledger = json.loads(Path(args.ledger).read_text())
    now = parse_deadline(args.now) if args.now else datetime.now(timezone.utc)

    errors, queue = validate(policy, ledger, now)
    print(json.dumps({"valid": not errors, "errors": errors, "queue": queue}, indent=2))
    raise SystemExit(0 if not errors else 2)


if __name__ == "__main__":
    main()

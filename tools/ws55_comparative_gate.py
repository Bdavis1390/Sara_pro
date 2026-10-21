#!/usr/bin/env python3
"""WS-55 reproducible comparative gate. Standard library only; fail closed."""
import argparse
import json
import math
import sys

METRICS = {
    "throughput_per_second": "higher",
    "p95_latency_ms": "lower",
    "task_completion_seconds": "lower",
    "operator_error_rate": "lower",
    "confirmed_weaknesses": "lower",
}
REQUIRED_GATES = ("authorization", "receipt_integrity", "replay_protection",
                  "concurrency", "privacy", "critical_regressions_absent")

def assess(data):
    if data.get("schema_version") != "ws55-v1":
        raise ValueError("unsupported schema_version")
    if not data.get("baseline_revision") or not data.get("candidate_revision"):
        raise ValueError("both revisions required")
    if data["baseline_revision"] == data["candidate_revision"]:
        raise ValueError("revisions must differ")
    if not data.get("matched_environment") or not data.get("matched_workload"):
        raise ValueError("matched environment and workload must be documented")
    gates = data.get("security_gates", {})
    if any(gates.get(k) is not True for k in REQUIRED_GATES):
        raise ValueError("all security gates must explicitly pass")
    results = {}
    for name, direction in METRICS.items():
        values = data.get("metrics", {}).get(name)
        if not isinstance(values, dict):
            raise ValueError("missing metric: " + name)
        b, c = values.get("baseline"), values.get("candidate")
        if any(isinstance(x, bool) or not isinstance(x, (int, float))
               or not math.isfinite(x) or x < 0 for x in (b, c)):
            raise ValueError("invalid metric: " + name)
        if b == 0:
            raise ValueError("zero baseline cannot support percentage claim: " + name)
        improvement = ((c / b - 1) if direction == "higher" else (1 - c / b)) * 100
        results[name] = {"baseline": b, "candidate": c,
                         "improvement_percent": round(improvement, 4),
                         "target_met": improvement >= 55}
    return {"classification": "INTERNAL_COMPARATIVE_EVIDENCE_ONLY",
            "all_targets_met": all(v["target_met"] for v in results.values()),
            "metrics": results, "external_validation": False}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("input_json")
    args = p.parse_args()
    try:
        with open(args.input_json, encoding="utf-8") as f:
            result = assess(json.load(f))
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["all_targets_met"] else 2
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        print("WS55 FAIL CLOSED: " + str(exc), file=sys.stderr)
        return 3

if __name__ == "__main__":
    sys.exit(main())

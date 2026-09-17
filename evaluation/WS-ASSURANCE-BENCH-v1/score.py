from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


class BenchmarkError(ValueError):
    pass


def load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_records(paths: list[str]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in paths:
        payload = load_json(path)
        if isinstance(payload, list):
            records.extend(payload)
        elif isinstance(payload, dict) and "records" in payload:
            bundled = payload["records"]
            if not isinstance(bundled, list):
                raise BenchmarkError(f"records bundle must be a list: {path}")
            records.extend(bundled)
        elif isinstance(payload, dict):
            records.append(payload)
        else:
            raise BenchmarkError(f"unsupported record payload in {path}")
    return records


def score_record(benchmark: dict[str, Any], record: dict[str, Any]) -> dict[str, Any]:
    levels = benchmark["evidence_levels"]
    criteria = benchmark["criteria"]
    assertions = record.get("criteria", {})
    known_ids = {item["id"] for item in criteria}

    unknown = sorted(set(assertions) - known_ids)
    if unknown:
        raise BenchmarkError(f"unknown criteria in {record.get('entity')}: {unknown}")

    rows: list[dict[str, Any]] = []
    total = 0.0
    for criterion in criteria:
        cid = criterion["id"]
        assertion = assertions.get(cid, {"level": "not_evidenced", "sources": []})
        level = assertion.get("level", "not_evidenced")
        if level not in levels:
            raise BenchmarkError(
                f"invalid evidence level {level!r} for {record.get('entity')} {cid}"
            )
        coverage = float(assertion.get("coverage", 1.0))
        if not 0.0 <= coverage <= 1.0:
            raise BenchmarkError(
                f"coverage must be between 0 and 1 for {record.get('entity')} {cid}"
            )
        sources = assertion.get("sources", [])
        if level != "not_evidenced" and not sources:
            raise BenchmarkError(
                f"nonzero evidence requires at least one source for {record.get('entity')} {cid}"
            )
        multiplier = float(levels[level])
        weighted = float(criterion["weight"]) * multiplier * coverage
        total += weighted
        rows.append(
            {
                "id": cid,
                "weight": criterion["weight"],
                "level": level,
                "coverage": coverage,
                "multiplier": multiplier,
                "score": round(weighted, 3),
                "sources": sources,
                "notes": assertion.get("notes", ""),
            }
        )

    return {
        "entity": record["entity"],
        "record_date": record.get("record_date"),
        "profile": benchmark["profile"],
        "score": round(total, 3),
        "criteria": rows,
        "record_non_claims": record.get("non_claims", []),
    }


def leadership_result(
    benchmark: dict[str, Any],
    scored: list[dict[str, Any]],
    focal_entity: str,
    methodology_review: dict[str, Any],
) -> dict[str, Any]:
    by_entity = {item["entity"]: item for item in scored}
    if focal_entity not in by_entity:
        raise BenchmarkError(f"missing focal entity {focal_entity!r}")
    focal = by_entity[focal_entity]
    competitors = [item for item in scored if item["entity"] != focal_entity]
    if not competitors:
        raise BenchmarkError("leadership result requires at least one competitor")
    strongest = max(competitors, key=lambda item: item["score"])
    margin = round(focal["score"] - strongest["score"], 3)
    gate = benchmark["leadership_gate"]

    focal_rows = {row["id"]: row for row in focal["criteria"]}
    required_missing = [
        cid
        for cid in gate["required_worldshepherd_criteria"]
        if focal_rows[cid]["score"] <= 0
    ]
    critical_zero = [
        cid for cid in gate["critical_zero_blocks"] if focal_rows[cid]["score"] <= 0
    ]
    score_gate_passed = (
        margin >= float(gate["minimum_margin_points"])
        and not required_missing
        and not critical_zero
    )
    externally_reviewed = bool(
        methodology_review.get("external_methodology_reviewed", False)
    )
    review_required = bool(
        gate.get("public_claim_requires_external_methodology_review", False)
    )
    public_claim_ready = score_gate_passed and (
        externally_reviewed or not review_required
    )

    return {
        "focal_entity": focal_entity,
        "focal_score": focal["score"],
        "strongest_competitor": strongest["entity"],
        "strongest_competitor_score": strongest["score"],
        "margin_points": margin,
        "minimum_margin_points": gate["minimum_margin_points"],
        "required_missing": required_missing,
        "critical_zero": critical_zero,
        "internal_profile_score_gate_passed": score_gate_passed,
        "external_methodology_reviewed": externally_reviewed,
        "public_claim_ready": public_claim_ready,
        "allowed_public_wording": (
            gate["wording_when_passed"] if public_claim_ready else None
        ),
        "prohibited_wording": gate["prohibited_wording"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", required=True)
    parser.add_argument("--records", nargs="+", required=True)
    parser.add_argument("--methodology-review", required=True)
    parser.add_argument("--focal-entity", default="Worldshepherd WS-SARA-EVAL-v1.1")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    benchmark = load_json(args.benchmark)
    if not isinstance(benchmark, dict):
        raise BenchmarkError("benchmark must be a JSON object")
    methodology_review = load_json(args.methodology_review)
    if not isinstance(methodology_review, dict):
        raise BenchmarkError("methodology review must be a JSON object")
    records = load_records(args.records)
    scored = [score_record(benchmark, record) for record in records]
    scored.sort(key=lambda item: (-item["score"], item["entity"].lower()))
    result = {
        "benchmark_schema": benchmark["schema"],
        "as_of": benchmark["as_of"],
        "profile": benchmark["profile"],
        "ranking": scored,
        "leadership": leadership_result(
            benchmark, scored, args.focal_entity, methodology_review
        ),
        "methodology_review": methodology_review,
        "benchmark_non_claims": benchmark["non_claims"],
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

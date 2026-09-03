#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import pathlib
import sys

STATUS_FACTOR = {
    "verified": 1.0,
    "complete": 1.0,
    "documented": 0.90,
    "partial": 0.60,
    "planned": 0.35,
    "missing": 0.0,
}

REQUIRED_GATES = [
    "requirements_use_case",
    "models_engineering_basis",
    "assumptions_uncertainty_limits",
    "hazards_regulatory_dependencies",
    "data_provenance_custody",
    "simulation_baseline",
    "test_plan_acceptance",
    "partner_facility_interface",
    "claims_release_controls",
    "reproducibility_evidence_package",
]

FORBIDDEN_TARGET_EQUIVALENCES = {
    "physical_validation",
    "flight_qualified",
    "clinically_validated",
    "certified",
    "regulatory_approved",
    "independently_replicated",
}


def load_json(path: pathlib.Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit("readiness registry must be a JSON object")
    return data


def score_workstream(ws: dict, weights: dict) -> float:
    gates = ws.get("internal_gates", {})
    score = 0.0
    total = 0.0
    for gate in REQUIRED_GATES:
        weight = float(weights[gate])
        total += weight
        status = gates.get(gate, "missing")
        if status not in STATUS_FACTOR:
            raise ValueError(f"{ws.get('id')}: invalid status {status!r} for {gate}")
        score += weight * STATUS_FACTOR[status]
    if total <= 0:
        raise ValueError("gate weights sum to zero")
    return round((score / total) * 100.0, 2)


def validate(data: dict) -> tuple[list[dict], list[str]]:
    errors: list[str] = []
    if data.get("schema") != "WS-READINESS-PORTFOLIO-V1":
        errors.append("unexpected readiness schema")

    target = float(data.get("target_internal_partner_readiness_pct", 0))
    if abs(target - 98.7) > 1e-9:
        errors.append(f"target must remain exactly 98.7, got {target}")

    weights = data.get("gate_weights", {})
    if set(weights) != set(REQUIRED_GATES):
        errors.append("gate_weights must contain exactly the required readiness gates")
    elif abs(sum(float(v) for v in weights.values()) - 100.0) > 1e-9:
        errors.append("gate weights must sum to 100")

    caps = data.get("evidence_maturity_caps_pct", {})
    rows: list[dict] = []
    seen: set[str] = set()

    for ws in data.get("workstreams", []):
        wsid = ws.get("id")
        if not wsid or wsid in seen:
            errors.append(f"missing or duplicate workstream id: {wsid!r}")
            continue
        seen.add(wsid)

        maturity = ws.get("evidence_maturity")
        if maturity not in caps:
            errors.append(f"{wsid}: unknown evidence_maturity {maturity!r}")
            continue

        try:
            score = score_workstream(ws, weights)
        except ValueError as exc:
            errors.append(str(exc))
            continue

        claimed = ws.get("claimed_external_maturity_pct")
        cap = float(caps[maturity])
        if claimed is not None and float(claimed) > cap + 1e-9:
            errors.append(
                f"{wsid}: claimed_external_maturity_pct={claimed} exceeds {maturity} cap={cap}"
            )

        target_kind = str(ws.get("target_kind", "internal_partner_readiness"))
        if target_kind in FORBIDDEN_TARGET_EQUIVALENCES:
            errors.append(
                f"{wsid}: 98.7 target cannot be redefined as {target_kind}; use internal_partner_readiness"
            )

        rows.append({
            "id": wsid,
            "name": ws.get("name", wsid),
            "internal_partner_readiness_pct": score,
            "target_pct": target,
            "gap_pct": round(max(0.0, target - score), 2),
            "target_met": score >= target,
            "evidence_maturity": maturity,
            "external_maturity_cap_pct": cap,
            "open_external_gate_count": len(ws.get("open_external_gates", [])),
            "open_external_gates": ws.get("open_external_gates", []),
        })

    return rows, errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--registry",
        default="readiness/portfolio.v1.json",
        help="Path to WS readiness registry",
    )
    parser.add_argument(
        "--output",
        default="readiness/portfolio-report.json",
        help="Output report path",
    )
    parser.add_argument(
        "--enforce-target",
        action="store_true",
        help="Fail if any workstream is below the 98.7 internal/partner-readiness target",
    )
    args = parser.parse_args()

    registry = pathlib.Path(args.registry)
    output = pathlib.Path(args.output)
    data = load_json(registry)
    rows, errors = validate(data)

    target = float(data.get("target_internal_partner_readiness_pct", 98.7))
    report = {
        "schema": "WS-READINESS-REPORT-V1",
        "target_internal_partner_readiness_pct": target,
        "workstreams": rows,
        "target_met_count": sum(1 for row in rows if row["target_met"]),
        "workstream_count": len(rows),
        "errors": errors,
        "claims_boundary": (
            "A 98.7 internal/partner-readiness score never upgrades physical, clinical, flight, RF, "
            "propulsion, regulatory, certification, or independent-validation evidence maturity."
        ),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    for row in sorted(rows, key=lambda x: (x["gap_pct"], x["id"]), reverse=True):
        print(
            f"{row['id']}: {row['internal_partner_readiness_pct']:.2f}% "
            f"(gap {row['gap_pct']:.2f} pp; evidence={row['evidence_maturity']}; "
            f"external cap={row['external_maturity_cap_pct']:.1f}%)"
        )

    if errors:
        print("Readiness registry validation errors:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 2

    if args.enforce_target:
        below = [r for r in rows if not r["target_met"]]
        if below:
            print(
                f"Target enforcement failed: {len(below)} workstream(s) remain below {target:.1f}% internal/partner readiness.",
                file=sys.stderr,
            )
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

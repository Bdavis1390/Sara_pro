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

REQUIRED_PACKAGE_FIELDS = [
    "use_case",
    "engineering_basis",
    "assumptions_limits",
    "hazards",
    "data_package",
    "baseline",
    "test_campaign",
    "acceptance",
    "partner_interface",
    "external_safe_statement",
    "reproducibility_outputs",
]

CORE_SERVICE_LANES = {"WS-CORE", "SARA", "PRE", "REVENUE-E2E"}

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
        raise SystemExit(f"{path}: expected JSON object")
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


def package_complete(package: dict | None) -> bool:
    if not isinstance(package, dict):
        return False
    for field in REQUIRED_PACKAGE_FIELDS:
        value = package.get(field)
        if isinstance(value, str):
            if not value.strip():
                return False
        elif isinstance(value, list):
            if not value:
                return False
        else:
            return False
    return True


def validate(data: dict, packages_data: dict | None = None) -> tuple[list[dict], list[str]]:
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
    package_map = {}
    if packages_data is not None:
        if packages_data.get("schema") != "WS-PARTNER-READINESS-PACKAGES-V1":
            errors.append("unexpected partner-readiness package schema")
        package_map = packages_data.get("packages", {})
        if not isinstance(package_map, dict):
            errors.append("packages must be a JSON object")
            package_map = {}

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

        pkg = package_map.get(wsid) if package_map else None
        pkg_ok = package_complete(pkg) if package_map else False
        package_required = wsid not in CORE_SERVICE_LANES
        if package_map and package_required and score >= target and not pkg_ok:
            errors.append(
                f"{wsid}: cannot meet 98.7 internal/partner readiness without a complete domain package"
            )

        rows.append({
            "id": wsid,
            "name": ws.get("name", wsid),
            "internal_partner_readiness_pct": score,
            "target_pct": target,
            "gap_pct": round(max(0.0, target - score), 2),
            "target_met": score >= target,
            "partner_package_required": package_required,
            "partner_package_complete": pkg_ok,
            "evidence_maturity": maturity,
            "external_maturity_cap_pct": cap,
            "open_external_gate_count": len(ws.get("open_external_gates", [])),
            "open_external_gates": ws.get("open_external_gates", []),
        })

    if package_map:
        unknown_packages = sorted(set(package_map) - seen)
        if unknown_packages:
            errors.append(f"partner packages exist for unknown workstreams: {unknown_packages}")

    return rows, errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", default="readiness/portfolio.v1.json")
    parser.add_argument("--packages", default="readiness/partner-packages.v1.json")
    parser.add_argument("--output", default="readiness/portfolio-report.json")
    parser.add_argument(
        "--enforce-target",
        action="store_true",
        help="Fail if any workstream is below the 98.7 internal/partner-readiness target",
    )
    args = parser.parse_args()

    data = load_json(pathlib.Path(args.registry))
    packages_path = pathlib.Path(args.packages)
    packages_data = load_json(packages_path) if packages_path.exists() else None
    rows, errors = validate(data, packages_data)

    target = float(data.get("target_internal_partner_readiness_pct", 98.7))
    report = {
        "schema": "WS-READINESS-REPORT-V1",
        "target_internal_partner_readiness_pct": target,
        "workstreams": rows,
        "target_met_count": sum(1 for row in rows if row["target_met"]),
        "package_complete_count": sum(1 for row in rows if row["partner_package_complete"]),
        "workstream_count": len(rows),
        "errors": errors,
        "claims_boundary": (
            "A 98.7 internal/partner-readiness score never upgrades physical, clinical, flight, RF, "
            "propulsion, regulatory, certification, or independent-validation evidence maturity."
        ),
    }
    output = pathlib.Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    for row in sorted(rows, key=lambda x: (x["gap_pct"], x["id"]), reverse=True):
        if row["partner_package_required"]:
            package_flag = "pkg=complete" if row["partner_package_complete"] else "pkg=open"
        else:
            package_flag = "pkg=n/a-core"
        print(
            f"{row['id']}: {row['internal_partner_readiness_pct']:.2f}% "
            f"(gap {row['gap_pct']:.2f} pp; {package_flag}; evidence={row['evidence_maturity']}; "
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

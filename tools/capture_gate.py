#!/usr/bin/env python3
"""Fail-closed capture readiness gate for Curious NerdworX.

This tool consumes a public, non-sensitive JSON configuration and reports
whether a named capture route is ready for:
- DEVELOPMENT: technical/capture work may continue;
- SUBMISSION: every hard eligibility gate is VERIFIED or NOT_APPLICABLE.

It does not replace a solicitation, contracting officer, government system of
record, attorney, security officer, or program-specific eligibility review.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ALLOWED_STATUSES = {
    "VERIFIED",
    "IN_PROGRESS",
    "PENDING_EXTERNAL",
    "NOT_STARTED",
    "NOT_APPLICABLE",
}
PASSING_STATUSES = {"VERIFIED", "NOT_APPLICABLE"}
SCHEMA = "CNX-CAPTURE-GATE-V0.1"


class CaptureGateError(ValueError):
    """Raised when the capture-gate configuration is invalid."""


@dataclass(frozen=True)
class GateResult:
    gate: str
    status: str
    passing: bool
    note: str


@dataclass(frozen=True)
class OpportunityResult:
    opportunity: str
    route: str
    development_ready: bool
    submission_ready: bool
    hard_gates: tuple[GateResult, ...]
    development_gates: tuple[GateResult, ...]
    note: str

    @property
    def hard_blockers(self) -> tuple[GateResult, ...]:
        return tuple(result for result in self.hard_gates if not result.passing)

    @property
    def development_blockers(self) -> tuple[GateResult, ...]:
        return tuple(
            result for result in self.development_gates if not result.passing
        )


def load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        config = json.load(handle)
    validate_config(config)
    return config


def validate_config(config: dict[str, Any]) -> None:
    if config.get("schema") != SCHEMA:
        raise CaptureGateError(
            f"schema must be exactly {SCHEMA!r}"
        )

    vocabulary = set(config.get("status_vocabulary", []))
    if vocabulary != ALLOWED_STATUSES:
        raise CaptureGateError(
            "status_vocabulary must exactly match the canonical capture statuses"
        )

    gates = config.get("gates")
    opportunities = config.get("opportunities")
    if not isinstance(gates, dict) or not isinstance(opportunities, dict):
        raise CaptureGateError("gates and opportunities must be objects")

    for gate_name, gate in gates.items():
        status = gate.get("status")
        if status not in ALLOWED_STATUSES:
            raise CaptureGateError(
                f"gate {gate_name!r} uses invalid status {status!r}"
            )

        passing_statuses = gate.get("passing_statuses")
        if passing_statuses is not None:
            if (
                not isinstance(passing_statuses, list)
                or not passing_statuses
                or any(item not in PASSING_STATUSES for item in passing_statuses)
            ):
                raise CaptureGateError(
                    f"gate {gate_name!r} has invalid passing_statuses"
                )

    for opportunity_name, opportunity in opportunities.items():
        for collection in ("hard_gates", "development_gates"):
            if collection not in opportunity:
                raise CaptureGateError(
                    f"{opportunity_name}.{collection} is required"
                )
            names = opportunity[collection]
            if not isinstance(names, list):
                raise CaptureGateError(
                    f"{opportunity_name}.{collection} must be a list"
                )
            missing = [gate_name for gate_name in names if gate_name not in gates]
            if missing:
                raise CaptureGateError(
                    f"{opportunity_name}.{collection} references unknown gates: "
                    + ", ".join(sorted(missing))
                )


def _gate_result(config: dict[str, Any], gate_name: str) -> GateResult:
    gate = config["gates"][gate_name]
    status = gate["status"]
    passing_statuses = set(gate.get("passing_statuses", PASSING_STATUSES))
    return GateResult(
        gate=gate_name,
        status=status,
        passing=status in passing_statuses,
        note=gate.get("public_note", ""),
    )


def evaluate(config: dict[str, Any], opportunity_name: str) -> OpportunityResult:
    try:
        opportunity = config["opportunities"][opportunity_name]
    except KeyError as exc:
        raise CaptureGateError(
            f"unknown opportunity {opportunity_name!r}"
        ) from exc

    hard = tuple(
        _gate_result(config, gate_name)
        for gate_name in opportunity["hard_gates"]
    )
    development = tuple(
        _gate_result(config, gate_name)
        for gate_name in opportunity["development_gates"]
    )

    return OpportunityResult(
        opportunity=opportunity_name,
        route=opportunity.get("route", "unspecified"),
        development_ready=all(item.passing for item in development),
        submission_ready=all(item.passing for item in hard)
        and all(item.passing for item in development),
        hard_gates=hard,
        development_gates=development,
        note=opportunity.get("note", ""),
    )


def to_dict(result: OpportunityResult) -> dict[str, Any]:
    def serialize(items: tuple[GateResult, ...]) -> list[dict[str, Any]]:
        return [
            {
                "gate": item.gate,
                "status": item.status,
                "passing": item.passing,
                "note": item.note,
            }
            for item in items
        ]

    return {
        "opportunity": result.opportunity,
        "route": result.route,
        "development_ready": result.development_ready,
        "submission_ready": result.submission_ready,
        "hard_blockers": [item.gate for item in result.hard_blockers],
        "development_blockers": [
            item.gate for item in result.development_blockers
        ],
        "hard_gates": serialize(result.hard_gates),
        "development_gates": serialize(result.development_gates),
        "note": result.note,
    }


def render_text(result: OpportunityResult) -> str:
    lines = [
        f"opportunity: {result.opportunity}",
        f"route: {result.route}",
        f"development_ready: {str(result.development_ready).lower()}",
        f"submission_ready: {str(result.submission_ready).lower()}",
    ]

    if result.development_blockers:
        lines.append(
            "development_blockers: "
            + ", ".join(item.gate for item in result.development_blockers)
        )
    if result.hard_blockers:
        lines.append(
            "hard_blockers: "
            + ", ".join(item.gate for item in result.hard_blockers)
        )

    for heading, items in (
        ("development_gates", result.development_gates),
        ("hard_gates", result.hard_gates),
    ):
        lines.append(f"{heading}:")
        if not items:
            lines.append("  - none")
        for item in items:
            lines.append(
                f"  - {item.gate}: {item.status} "
                f"({'PASS' if item.passing else 'BLOCK'})"
            )

    if result.note:
        lines.append(f"note: {result.note}")

    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "opportunity",
        help="Opportunity key from config/cnx_capture_gates_v0_1.json",
    )
    parser.add_argument(
        "--config",
        default="config/cnx_capture_gates_v0_1.json",
        type=Path,
        help="Path to capture-gate JSON",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON",
    )
    parser.add_argument(
        "--require-submission-ready",
        action="store_true",
        help="Exit nonzero unless the opportunity is submission-ready",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    config = load_config(args.config)
    result = evaluate(config, args.opportunity)

    if args.json:
        print(json.dumps(to_dict(result), indent=2, sort_keys=True))
    else:
        print(render_text(result))

    if args.require_submission_ready and not result.submission_ready:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

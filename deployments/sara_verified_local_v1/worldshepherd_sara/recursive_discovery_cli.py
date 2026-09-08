from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .recursive_discovery import (
    DiscoveryEvidenceState,
    DiscoveryKind,
    ExpansionProposal,
    RecursiveDiscoveryPolicy,
    RecursiveDiscoveryState,
    initialize_state,
    make_seed,
    run_recursive_cycle,
    state_digest,
    verify_cycle_report,
)


def _read_json(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write_json(path: str, payload: dict[str, Any]) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _cmd_init(args: argparse.Namespace) -> int:
    payload = _read_json(args.seeds)
    seeds = []
    for raw in payload.get("seeds", []):
        seeds.append(
            make_seed(
                kind=DiscoveryKind(raw["kind"]),
                domain=raw["domain"],
                statement=raw["statement"],
                source_refs=raw.get("source_refs", []),
                confidence=float(raw.get("confidence", 0.0)),
                evidence_state=DiscoveryEvidenceState(raw.get("evidence_state", "UNVERIFIED")),
                cross_domain_tags=raw.get("cross_domain_tags", []),
                falsification_tests=raw.get("falsification_tests", []),
            )
        )
    state = initialize_state(seeds, max_active_frontier=args.max_active_frontier)
    output = state.model_dump(mode="json")
    output["state_digest"] = state_digest(state)
    _write_json(args.out, output)
    return 0


def _cmd_cycle(args: argparse.Namespace) -> int:
    state_payload = _read_json(args.state)
    state_payload.pop("state_digest", None)
    state = RecursiveDiscoveryState.model_validate(state_payload)
    proposal_payload = _read_json(args.proposals)
    proposals = [ExpansionProposal.model_validate(item) for item in proposal_payload.get("proposals", [])]

    policy_payload = proposal_payload.get("policy") or {}
    policy = RecursiveDiscoveryPolicy.model_validate(policy_payload)
    next_state, report = run_recursive_cycle(state, proposals, policy=policy)

    next_payload = next_state.model_dump(mode="json")
    next_payload["state_digest"] = state_digest(next_state)
    _write_json(args.out_state, next_payload)
    _write_json(args.out_report, report.model_dump(mode="json"))
    return 0


def _cmd_verify(args: argparse.Namespace) -> int:
    payload = _read_json(args.state)
    claimed = payload.pop("state_digest", None)
    state = RecursiveDiscoveryState.model_validate(payload)
    actual = state_digest(state)
    if claimed is not None and claimed != actual:
        raise SystemExit(f"state digest mismatch: claimed={claimed} actual={actual}")

    if args.report:
        from .recursive_discovery import RecursiveCycleReport

        report = RecursiveCycleReport.model_validate(_read_json(args.report))
        if not verify_cycle_report(report):
            raise SystemExit("cycle report digest mismatch")
        if report.state_after_digest != actual:
            raise SystemExit("report state_after_digest does not match state")

    print(actual)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ws-omega-recursion",
        description="Governed, resumable recursive discovery frontier for Worldshepherd SARA.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="initialize a governed discovery frontier")
    init.add_argument("--seeds", required=True)
    init.add_argument("--out", required=True)
    init.add_argument("--max-active-frontier", type=int, default=4096)
    init.set_defaults(func=_cmd_init)

    cycle = sub.add_parser("cycle", help="advance one bounded recursive cycle")
    cycle.add_argument("--state", required=True)
    cycle.add_argument("--proposals", required=True)
    cycle.add_argument("--out-state", required=True)
    cycle.add_argument("--out-report", required=True)
    cycle.set_defaults(func=_cmd_cycle)

    verify = sub.add_parser("verify", help="verify state and optional cycle report digests")
    verify.add_argument("--state", required=True)
    verify.add_argument("--report")
    verify.set_defaults(func=_cmd_verify)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())

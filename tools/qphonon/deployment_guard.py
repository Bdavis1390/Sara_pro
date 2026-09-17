#!/usr/bin/env python3
"""Deployment guard for WS-QPHONON V0.3.

This CLI is intentionally non-networked. It verifies ECHO events and human
execution approvals against durable local state. It does not actuate hardware.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from durable_state import DurableStateStore, ZERO_DIGEST
from execution_gate import evaluate_execution
from security_controls import compute_event_digest, sha256_json, verify_echo_event
from ssh_attestation import verify_approval_signature


def _load_json(path: str) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def verify_and_commit_event(args: argparse.Namespace) -> tuple[int, dict[str, Any]]:
    event = _load_json(args.event)
    store = DurableStateStore(args.state_db)
    stream_state = store.get_stream(args.stream)

    expected_previous = ZERO_DIGEST if stream_state is None else stream_state.event_digest
    seen = {event.get("event_id")} if store.has_consumed("event", str(event.get("event_id"))) else set()

    decision = verify_echo_event(
        event,
        expected_config_digest=args.config_digest,
        expected_previous_event_digest=expected_previous,
        seen_event_ids=seen,
        now=datetime.now(timezone.utc),
    )
    if not decision.passed:
        return 2, {"stage": "integrity", **asdict(decision)}

    committed, reason = store.commit_event(
        stream=args.stream,
        event_id=str(event["event_id"]),
        event_digest=str(event["event_digest"]),
        sequence=int(event["event_sequence"]),
        previous_event_digest=str(event["previous_event_digest"]),
    )
    if not committed:
        return 2, {
            "stage": "durable_state",
            "passed": False,
            "disposition": "REJECT_EVIDENCE",
            "reasons": [reason],
        }

    return 0, {
        "stage": "durable_state",
        "passed": True,
        "disposition": "EVIDENCE_COMMITTED",
        "event_digest": event["event_digest"],
        "stream": args.stream,
    }


def verify_and_consume_approval(args: argparse.Namespace) -> tuple[int, dict[str, Any]]:
    approval = _load_json(args.approval)
    prime = _load_json(args.prime_decision)
    store = DurableStateStore(args.state_db)

    attestation = verify_approval_signature(
        approval,
        signature_path=args.signature,
        allowed_signers_path=args.allowed_signers,
        principal=args.principal,
    )
    if not attestation.verified:
        return 2, {
            "stage": "attestation",
            "executable": False,
            "disposition": "EXECUTION_BLOCKED",
            "reasons": [attestation.reason],
        }

    trusted_approval = dict(approval)
    trusted_approval["approval_attestation_verified"] = True
    decision = evaluate_execution(
        prime,
        trusted_approval,
        experiment_digest=args.experiment_digest,
        config_digest=args.config_digest,
        seen_approval_ids=(),
        now=datetime.now(timezone.utc),
    )
    if not decision.executable:
        return 2, {"stage": "execution_gate", **asdict(decision)}

    approval_id = str(approval["approval_id"])
    if not store.consume_once("approval", approval_id, attestation.payload_digest):
        return 2, {
            "stage": "durable_state",
            "executable": False,
            "disposition": "EXECUTION_BLOCKED",
            "reasons": ["APPROVAL_REPLAY_DETECTED"],
        }

    return 0, {
        "stage": "execution_gate",
        "executable": True,
        "disposition": "EXECUTION_ALLOWED",
        "approval_id": approval_id,
        "principal": attestation.principal,
        "approval_payload_digest": attestation.payload_digest,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--state-db",
        default="/var/lib/worldshepherd/qphonon-state.sqlite3",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    event = sub.add_parser("verify-event")
    event.add_argument("--event", required=True)
    event.add_argument("--stream", required=True)
    event.add_argument("--config-digest", required=True)

    approval = sub.add_parser("verify-approval")
    approval.add_argument("--approval", required=True)
    approval.add_argument("--prime-decision", required=True)
    approval.add_argument("--signature", required=True)
    approval.add_argument("--allowed-signers", required=True)
    approval.add_argument("--principal", required=True)
    approval.add_argument("--experiment-digest", required=True)
    approval.add_argument("--config-digest", required=True)

    args = parser.parse_args()

    if args.command == "verify-event":
        code, output = verify_and_commit_event(args)
    else:
        code, output = verify_and_consume_approval(args)

    print(json.dumps(output, sort_keys=True, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())

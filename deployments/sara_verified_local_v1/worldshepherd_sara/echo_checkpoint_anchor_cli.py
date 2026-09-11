from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .echo_checkpoint_anchor import (
    EXTERNAL_READ_BACK_MODE,
    EchoCheckpointAnchorError,
    TEST_PROVIDER,
    TEST_PROVIDER_MODE,
    build_anchor_receipt,
    build_anchor_request,
    build_test_anchor_evidence,
    verify_anchor_receipt,
)


def _read_json(path: str) -> Any:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EchoCheckpointAnchorError(f"unable to read JSON artifact: {path}") from exc


def _write_json(value: Any, path: str | None) -> None:
    text = json.dumps(value, indent=2, sort_keys=True) + "\n"
    if path:
        Path(path).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ws-echo-anchor",
        description="Build and verify bounded ECHO checkpoint anchor artifacts.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    request = sub.add_parser("request", help="build a deterministic anchor request")
    request.add_argument("--checkpoint", required=True)
    request.add_argument("--expected-fingerprint", required=True)
    request.add_argument("--output")

    simulate = sub.add_parser("simulate", help="build CI-only simulated anchor evidence and receipt")
    simulate.add_argument("--checkpoint", required=True)
    simulate.add_argument("--expected-fingerprint", required=True)
    simulate.add_argument("--provider-reference", required=True)
    simulate.add_argument("--observed-at", required=True)
    simulate.add_argument("--output")

    verify = sub.add_parser("verify", help="verify receipt, evidence, and checkpoint as one anchor evidence set")
    verify.add_argument("--checkpoint", required=True)
    verify.add_argument("--evidence", required=True)
    verify.add_argument("--receipt", required=True)
    verify.add_argument("--expected-fingerprint", required=True)
    verify.add_argument("--expected-provider", required=True)
    verify.add_argument(
        "--expected-mode",
        choices=[TEST_PROVIDER_MODE, EXTERNAL_READ_BACK_MODE],
        required=True,
    )
    verify.add_argument(
        "--provider-document",
        help="retrieved provider JSON; mandatory for EXTERNAL_READ_BACK verification",
    )
    verify.add_argument("--output")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        checkpoint = _read_json(args.checkpoint)
        if args.command == "request":
            result = build_anchor_request(checkpoint, args.expected_fingerprint)
        elif args.command == "simulate":
            request = build_anchor_request(checkpoint, args.expected_fingerprint)
            evidence = build_test_anchor_evidence(
                request,
                provider_reference=args.provider_reference,
                observed_at=args.observed_at,
            )
            receipt = build_anchor_receipt(
                request,
                evidence,
                expected_provider=TEST_PROVIDER,
                expected_mode=TEST_PROVIDER_MODE,
            )
            result = {"request": request, "evidence": evidence, "receipt": receipt}
        else:
            evidence = _read_json(args.evidence)
            receipt = _read_json(args.receipt)
            provider_document = None
            if args.expected_mode == EXTERNAL_READ_BACK_MODE:
                if not args.provider_document:
                    raise EchoCheckpointAnchorError(
                        "EXTERNAL_READ_BACK verification requires --provider-document"
                    )
                provider_document = _read_json(args.provider_document)
            result = verify_anchor_receipt(
                receipt,
                evidence,
                checkpoint,
                args.expected_fingerprint,
                expected_provider=args.expected_provider,
                expected_mode=args.expected_mode,
                provider_document=provider_document,
            )
        _write_json(result, args.output)
        return 0
    except (EchoCheckpointAnchorError, OSError) as exc:
        sys.stderr.write(f"ERROR: {exc}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

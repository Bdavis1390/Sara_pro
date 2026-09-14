from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from .hmaa_authorized_session import (
    HMAAAuthorizedReadSessionRequest,
    export_authorized_read_session,
    run_authorized_read_session,
)
from .hmaa_lattice_capture import SandboxReadCapturePlan
from .hmaa_preflight import HMAAPreflightRequest, evaluate_preflight


def _load_json_object(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SystemExit(f"{path} must contain one JSON object")
    return value


def _runtime_env() -> dict[str, str | None]:
    names = (
        "LATTICE_ENDPOINT",
        "ENVIRONMENT_TOKEN",
        "LATTICE_CLIENT_ID",
        "LATTICE_CLIENT_SECRET",
        "SANDBOXES_TOKEN",
    )
    return {name: os.getenv(name) for name in names}


def _render(value: Any) -> str:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    return json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Preflight or execute the bounded WS-HMAA authorized read-only "
            "Lattice Sandbox evidence session"
        )
    )
    parser.add_argument("--mission-id", required=True)
    parser.add_argument(
        "--execute-network",
        action="store_true",
        help="perform the bounded Sandbox read; absent this flag, preflight is zero-network",
    )
    parser.add_argument(
        "--authorization-confirmed",
        action="store_true",
        help="explicitly confirm authorization for the requested Sandbox read",
    )
    parser.add_argument("--capture-attempts", type=int, default=3)
    parser.add_argument("--max-entity-messages", type=int, default=2)
    parser.add_argument("--max-task-messages", type=int, default=2)
    parser.add_argument(
        "--entity-request-json",
        type=Path,
        help="optional JSON object containing documented entity-stream request fields",
    )
    parser.add_argument(
        "--task-request-json",
        type=Path,
        help="optional JSON object containing documented task-stream request fields",
    )
    parser.add_argument(
        "--out",
        type=Path,
        help="new output directory for execution evidence, or preflight-report.json parent",
    )
    args = parser.parse_args()

    plan = SandboxReadCapturePlan(
        entity_request=_load_json_object(args.entity_request_json),
        task_request=_load_json_object(args.task_request_json),
        max_entity_messages=args.max_entity_messages,
        max_task_messages=args.max_task_messages,
    )
    env = _runtime_env()

    if not args.execute_network:
        report = evaluate_preflight(
            HMAAPreflightRequest(
                mission_id=args.mission_id,
                network_enabled=False,
                authorization_confirmed=False,
                capture_plan=plan,
            ),
            env=env,
        )
        text = _render(report)
        if args.out is None:
            print(text, end="")
        else:
            args.out.mkdir(parents=True, exist_ok=False)
            (args.out / "preflight-report.json").write_text(text, encoding="utf-8")
            print(report.report_sha256)
        return

    if not args.authorization_confirmed:
        raise SystemExit(
            "network execution requires --authorization-confirmed; no network call was made"
        )
    if args.out is None:
        raise SystemExit(
            "network execution requires --out so the evidence session is retained locally"
        )
    if args.out.exists():
        raise SystemExit(
            "network execution requires a new --out directory; no network call was made"
        )

    run = run_authorized_read_session(
        HMAAAuthorizedReadSessionRequest(
            mission_id=args.mission_id,
            authorization_confirmed=True,
            capture_plan=plan,
            capture_attempts=args.capture_attempts,
        ),
        env=env,
    )
    manifest = export_authorized_read_session(run, args.out)
    print(manifest.package_sha256)


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import json
import os
from typing import Any

from .registry_monotonic_witness import RegistryWitnessError
from .registry_witness_gate import prepare_registry_witness_precondition
from .registry_witness_runtime import (
    RegistryWitnessRuntimeConfigError,
    load_registry_witness_client_from_environment,
)
from .storage import DurableStore


CLI_SCHEMA = "WS-SARA-REGISTRY-WITNESS-CLI-V1"


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, indent=2) + "\n"


def witness_status(store: DurableStore) -> dict[str, Any]:
    client = load_registry_witness_client_from_environment()
    local = store.checkpoint_status()
    assessment = client.check(local, require_head=True)
    return {
        "schema": CLI_SCHEMA,
        "operation": "status",
        "local_checkpoint": local,
        "witness_assessment": assessment,
        "external_witnessed": False,
        "independence_verified": False,
        "claims_boundary": (
            "Status verifies configured cryptographic witness state. It does not establish "
            "deployment independence or infrastructure immutability."
        ),
    }


def witness_advance(store: DurableStore) -> dict[str, Any]:
    """Explicitly advance the configured witness to the current local checkpoint."""

    client = load_registry_witness_client_from_environment()
    local = store.checkpoint_status()
    assessment = client.advance_and_verify(local)
    return {
        "schema": CLI_SCHEMA,
        "operation": "advance",
        "local_checkpoint": local,
        "witness_assessment": assessment,
        "external_witnessed": False,
        "independence_verified": False,
        "claims_boundary": (
            "Advance proves the configured witness signed this exact checkpoint. It does not "
            "establish independent administration, WORM retention, or post-action finalization."
        ),
    }


def witness_precondition(store: DurableStore) -> dict[str, Any]:
    client = load_registry_witness_client_from_environment()
    precondition = prepare_registry_witness_precondition(store, client)
    return {
        "schema": CLI_SCHEMA,
        "operation": "precondition",
        "precondition": precondition.evidence(),
        "external_witnessed": False,
        "independence_verified": False,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="worldshepherd-registry-witness",
        description=(
            "Inspect or explicitly advance the configured MAG-1.6R registry witness. "
            "This command never infers independent deployment status."
        ),
    )
    parser.add_argument(
        "operation",
        choices=("status", "advance", "precondition"),
        help="status checks the head, advance performs the remote witness write, precondition emits exact gate evidence",
    )
    parser.add_argument(
        "--data-dir",
        default=None,
        help="SARA data directory; defaults to SARA_DATA_DIR or ./data",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.data_dir is not None:
        os.environ["SARA_DATA_DIR"] = args.data_dir
    try:
        store = DurableStore(args.data_dir)
        if args.operation == "status":
            result = witness_status(store)
        elif args.operation == "advance":
            result = witness_advance(store)
        else:
            result = witness_precondition(store)
    except (RegistryWitnessRuntimeConfigError, RegistryWitnessError, RuntimeError, ValueError) as exc:
        print(
            _json(
                {
                    "schema": CLI_SCHEMA,
                    "status": "FAIL",
                    "operation": args.operation,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            ),
            end="",
        )
        return 2
    print(_json(result), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

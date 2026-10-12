"""Aggregate WS-CAE crypto-system patches into a read-only portfolio view."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from .cli import InputError, _json
from .crypto_system import READINESS_ORDER, assess_system
from .crypto_system_cli import parse_system_patch


def build(paths: list[Path]) -> dict:
    if not paths:
        raise InputError("at least one crypto-system patch path is required")

    assets = []
    blocker_roles: Counter[str] = Counter()
    all_valid = True
    weakest_value = max(READINESS_ORDER.values())

    for path in paths:
        patch = parse_system_patch(_json(path, "crypto-system patch"))
        result = assess_system(patch)
        all_valid = all_valid and result.valid
        if result.valid:
            weakest_value = min(weakest_value, READINESS_ORDER[result.weakest_readiness_state])
        for blocker in result.blocking_components:
            role = blocker.split(":", 1)[0]
            blocker_roles[role] += 1
        assets.append(
            {
                "asset": patch.asset,
                "valid": result.valid,
                "system_state": result.system_state,
                "weakest_readiness_state": result.weakest_readiness_state,
                "blocking_components": list(result.blocking_components),
            }
        )

    if not all_valid:
        portfolio_state = "CRYPTO_PORTFOLIO_PATCH_INVALID"
        weakest = "UNASSESSED"
    else:
        weakest = next(k for k, v in READINESS_ORDER.items() if v == weakest_value)
        if weakest_value <= READINESS_ORDER["CLASSICAL_DEPENDENCY"]:
            portfolio_state = "PORTFOLIO_HAS_CRITICAL_MIGRATION_BLOCKERS"
        elif weakest_value < READINESS_ORDER["PQ_DEPLOYED"]:
            portfolio_state = "PORTFOLIO_PARTIAL_PQ_READINESS"
        else:
            portfolio_state = "ALL_DECLARED_PORTFOLIO_DEPENDENCIES_PQ_DEPLOYED"

    return {
        "spec": "WS-CAE-CRYPTO-PORTFOLIO-1",
        "asset_count": len(assets),
        "all_valid": all_valid,
        "portfolio_state": portfolio_state,
        "weakest_readiness_state": weakest,
        "blocking_role_counts": dict(sorted(blocker_roles.items())),
        "assets": assets,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a WS-CAE crypto-system portfolio view")
    parser.add_argument("patches", nargs="+", type=Path)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)
    try:
        output = build(args.patches)
    except InputError as exc:
        print(json.dumps({"spec": "WS-CAE-CRYPTO-PORTFOLIO-1", "input_error": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(output, indent=2 if args.pretty else None, sort_keys=True))
    return 0 if output["all_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

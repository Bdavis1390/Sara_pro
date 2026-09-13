"""Standalone read-only CLI for WS-CAE crypto-system dependency patches."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .cli import InputError, _json
from .crypto_system import (
    COMPONENT_ROLES,
    READINESS_ORDER,
    ComponentState,
    CryptoSystemPatch,
    assess_system,
)

PATCH_FIELDS = {"spec", "asset", "components"}
COMPONENT_FIELDS = {"role", "name", "readiness_state", "critical", "evidence_documented"}


def parse_system_patch(raw: Any) -> CryptoSystemPatch:
    if not isinstance(raw, dict):
        raise InputError("crypto-system patch must be an object")
    unknown = sorted(set(raw) - PATCH_FIELDS)
    if unknown:
        raise InputError("unknown crypto-system patch field(s): " + ", ".join(unknown))
    missing = sorted(PATCH_FIELDS - set(raw))
    if missing:
        raise InputError("missing crypto-system patch field(s): " + ", ".join(missing))
    if raw["spec"] != "WS-CAE-CRYPTO-SYSTEM-PATCH-1":
        raise InputError("spec must be WS-CAE-CRYPTO-SYSTEM-PATCH-1")
    if not isinstance(raw["asset"], str) or not raw["asset"].strip():
        raise InputError("asset must be a non-empty string")
    if not isinstance(raw["components"], list) or not raw["components"]:
        raise InputError("components must be a non-empty array")

    components = []
    for index, item in enumerate(raw["components"]):
        if not isinstance(item, dict):
            raise InputError(f"component[{index}] must be an object")
        unknown_component = sorted(set(item) - COMPONENT_FIELDS)
        if unknown_component:
            raise InputError(
                f"unknown component[{index}] field(s): " + ", ".join(unknown_component)
            )
        missing_component = sorted(COMPONENT_FIELDS - set(item))
        if missing_component:
            raise InputError(
                f"missing component[{index}] field(s): " + ", ".join(missing_component)
            )
        role = item["role"]
        state = item["readiness_state"]
        name = item["name"]
        if role not in COMPONENT_ROLES:
            raise InputError(f"component[{index}] role is not recognized")
        if state not in READINESS_ORDER:
            raise InputError(f"component[{index}] readiness_state is not recognized")
        if not isinstance(name, str) or not name.strip():
            raise InputError(f"component[{index}] name must be a non-empty string")
        if type(item["critical"]) is not bool or type(item["evidence_documented"]) is not bool:
            raise InputError(f"component[{index}] critical/evidence_documented must be boolean")
        components.append(
            ComponentState(role, name, state, item["critical"], item["evidence_documented"])
        )
    return CryptoSystemPatch(raw["asset"], tuple(components))


def run(path: Path) -> dict:
    raw = _json(path, "crypto-system patch")
    patch = parse_system_patch(raw)
    assessment = assess_system(patch)
    return {
        "spec": "WS-CAE-CRYPTO-SYSTEM-PATCH-1",
        "asset": patch.asset,
        "assessment": assessment.to_dict(),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="WS-CAE crypto-system dependency checker")
    parser.add_argument("patch", type=Path)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)
    try:
        output = run(args.patch)
    except InputError as exc:
        print(json.dumps({"spec": "WS-CAE-CRYPTO-SYSTEM-PATCH-1", "input_error": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(output, indent=2 if args.pretty else None, sort_keys=True))
    return 0 if output["assessment"]["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

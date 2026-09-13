"""WS-CAE command-line conformance checker.

Read-only defensive tooling. This CLI parses authority-state profile documents,
runs the WS-CAE reference assessment, and emits deterministic JSON. It performs
no signing, key generation, wallet access, transaction construction, broadcast,
or asset movement.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from ws_cae_reference_conformance import WSCAEReferenceProfile, assess_reference_profile


REQUIRED_FIELDS = (
    "ecosystem",
    "adapter_class",
    "implementation_maturity",
    "stable_authority_id",
    "authenticator_replaceable",
    "pq_authorization_state",
    "policy_state_documented",
    "recovery_state_documented",
    "domain_binding_documented",
    "evidence_state_documented",
)

OPTIONAL_FIELDS = ("consensus_pq_state",)
ALLOWED_FIELDS = set(REQUIRED_FIELDS + OPTIONAL_FIELDS)


class ProfileInputError(ValueError):
    """Raised when an input document cannot be converted into WS-CAE profiles."""


def _expect_bool(value: Any, field: str) -> bool:
    if type(value) is not bool:
        raise ProfileInputError(f"{field} must be boolean")
    return value


def parse_profile(raw: Any) -> WSCAEReferenceProfile:
    if not isinstance(raw, dict):
        raise ProfileInputError("profile must be a JSON object")

    missing = [field for field in REQUIRED_FIELDS if field not in raw]
    if missing:
        raise ProfileInputError("missing required field(s): " + ", ".join(sorted(missing)))

    unknown = sorted(set(raw) - ALLOWED_FIELDS)
    if unknown:
        raise ProfileInputError("unknown field(s): " + ", ".join(unknown))

    for field in ("ecosystem", "adapter_class", "implementation_maturity", "pq_authorization_state"):
        if not isinstance(raw[field], str) or not raw[field].strip():
            raise ProfileInputError(f"{field} must be a non-empty string")

    bool_fields = (
        "stable_authority_id",
        "authenticator_replaceable",
        "policy_state_documented",
        "recovery_state_documented",
        "domain_binding_documented",
        "evidence_state_documented",
    )
    for field in bool_fields:
        _expect_bool(raw[field], field)

    consensus = raw.get("consensus_pq_state", "CLASSICAL_OR_UNPROVEN")
    if not isinstance(consensus, str) or not consensus.strip():
        raise ProfileInputError("consensus_pq_state must be a non-empty string")

    return WSCAEReferenceProfile(
        ecosystem=raw["ecosystem"],
        adapter_class=raw["adapter_class"],
        implementation_maturity=raw["implementation_maturity"],
        stable_authority_id=raw["stable_authority_id"],
        authenticator_replaceable=raw["authenticator_replaceable"],
        pq_authorization_state=raw["pq_authorization_state"],
        policy_state_documented=raw["policy_state_documented"],
        recovery_state_documented=raw["recovery_state_documented"],
        domain_binding_documented=raw["domain_binding_documented"],
        evidence_state_documented=raw["evidence_state_documented"],
        consensus_pq_state=consensus,
    )


def load_profiles(path: Path) -> list[WSCAEReferenceProfile]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ProfileInputError(f"cannot read {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ProfileInputError(f"invalid JSON in {path}: {exc}") from exc

    if isinstance(raw, dict) and "profiles" in raw:
        if set(raw) != {"profiles"}:
            raise ProfileInputError("batch document may contain only the top-level 'profiles' field")
        if not isinstance(raw["profiles"], list) or not raw["profiles"]:
            raise ProfileInputError("profiles must be a non-empty array")
        return [parse_profile(item) for item in raw["profiles"]]

    return [parse_profile(raw)]


def assess_path(path: Path) -> dict[str, Any]:
    profiles = load_profiles(path)
    results = []
    all_valid = True
    for profile in profiles:
        assessment = assess_reference_profile(profile)
        all_valid = all_valid and assessment.valid
        results.append(
            {
                "ecosystem": profile.ecosystem,
                "adapter_class": profile.adapter_class,
                "assessment": assessment.to_dict(),
            }
        )

    return {
        "spec": "WS-CAE-1",
        "tool": "ws-cae-reference-cli",
        "input": str(path),
        "profile_count": len(results),
        "all_valid": all_valid,
        "results": results,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ws-cae",
        description="Read-only WS-CAE cross-chain authority conformance checker",
    )
    parser.add_argument("profile", type=Path, help="JSON profile or batch document")
    parser.add_argument("--pretty", action="store_true", help="pretty-print JSON output")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = assess_path(args.profile)
    except ProfileInputError as exc:
        print(json.dumps({"spec": "WS-CAE-1", "input_error": str(exc)}, sort_keys=True))
        return 2

    indent = 2 if args.pretty else None
    print(json.dumps(result, indent=indent, sort_keys=True))
    return 0 if result["all_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

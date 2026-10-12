"""WS-CAE command-line conformance checker.

Read-only defensive tooling. This CLI parses authority-state profile documents,
runs the WS-CAE reference assessment, optionally applies a relying-party policy,
and emits deterministic JSON. It performs no signing, key generation, wallet
access, transaction construction, broadcast, or asset movement.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from ws_cae_consumer_policy import WSCAEConsumerPolicy, assess_consumer_policy
from ws_cae_reference_conformance import (
    CONSENSUS_STATES,
    PQ_AUTH_STATES,
    WSCAEReferenceProfile,
    assess_reference_profile,
)


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

POLICY_ALLOWED_FIELDS = {
    "name",
    "minimum_maturity",
    "accepted_pq_authorization_states",
    "accepted_consensus_states",
    "require_stable_authority_id",
    "require_authenticator_replaceable",
    "require_policy_state_documented",
    "require_recovery_state_documented",
    "require_domain_binding_documented",
    "require_evidence_state_documented",
}


class ProfileInputError(ValueError):
    """Raised when an input document cannot be converted into WS-CAE profiles or policy."""


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


def _string_list(raw: Any, field: str) -> tuple[str, ...]:
    if not isinstance(raw, list) or not raw or any(not isinstance(item, str) or not item for item in raw):
        raise ProfileInputError(f"{field} must be a non-empty array of strings")
    return tuple(raw)


def parse_policy(raw: Any) -> WSCAEConsumerPolicy:
    if not isinstance(raw, dict):
        raise ProfileInputError("policy must be a JSON object")
    unknown = sorted(set(raw) - POLICY_ALLOWED_FIELDS)
    if unknown:
        raise ProfileInputError("unknown policy field(s): " + ", ".join(unknown))

    name = raw.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ProfileInputError("policy name must be a non-empty string")

    bool_defaults = {
        "require_stable_authority_id": False,
        "require_authenticator_replaceable": False,
        "require_policy_state_documented": False,
        "require_recovery_state_documented": False,
        "require_domain_binding_documented": True,
        "require_evidence_state_documented": True,
    }
    bool_values = {}
    for field, default in bool_defaults.items():
        value = raw.get(field, default)
        _expect_bool(value, field)
        bool_values[field] = value

    pq_states = _string_list(
        raw.get("accepted_pq_authorization_states", sorted(PQ_AUTH_STATES)),
        "accepted_pq_authorization_states",
    )
    consensus_states = _string_list(
        raw.get("accepted_consensus_states", sorted(CONSENSUS_STATES)),
        "accepted_consensus_states",
    )
    minimum_maturity = raw.get("minimum_maturity", "ROADMAP")
    if not isinstance(minimum_maturity, str) or not minimum_maturity:
        raise ProfileInputError("minimum_maturity must be a non-empty string")

    return WSCAEConsumerPolicy(
        name=name,
        minimum_maturity=minimum_maturity,
        accepted_pq_authorization_states=pq_states,
        accepted_consensus_states=consensus_states,
        **bool_values,
    )


def _load_json(path: Path, label: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ProfileInputError(f"cannot read {label} {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ProfileInputError(f"invalid JSON in {label} {path}: {exc}") from exc


def load_profiles(path: Path) -> list[WSCAEReferenceProfile]:
    raw = _load_json(path, "profile")
    if isinstance(raw, dict) and "profiles" in raw:
        if set(raw) != {"profiles"}:
            raise ProfileInputError("batch document may contain only the top-level 'profiles' field")
        if not isinstance(raw["profiles"], list) or not raw["profiles"]:
            raise ProfileInputError("profiles must be a non-empty array")
        return [parse_profile(item) for item in raw["profiles"]]
    return [parse_profile(raw)]


def load_policy(path: Path) -> WSCAEConsumerPolicy:
    return parse_policy(_load_json(path, "policy"))


def assess_path(path: Path, policy_path: Path | None = None) -> dict[str, Any]:
    profiles = load_profiles(path)
    policy = load_policy(policy_path) if policy_path else None
    results = []
    all_valid = True
    all_policy_pass = True

    for profile in profiles:
        assessment = assess_reference_profile(profile)
        all_valid = all_valid and assessment.valid
        item: dict[str, Any] = {
            "ecosystem": profile.ecosystem,
            "adapter_class": profile.adapter_class,
            "assessment": assessment.to_dict(),
        }
        if policy is not None:
            policy_result = assess_consumer_policy(profile, assessment, policy)
            item["policy"] = policy_result.to_dict()
            all_policy_pass = all_policy_pass and policy_result.passed
        results.append(item)

    output: dict[str, Any] = {
        "spec": "WS-CAE-1",
        "tool": "ws-cae-reference-cli",
        "input": str(path),
        "profile_count": len(results),
        "all_valid": all_valid,
        "results": results,
    }
    if policy is not None:
        output["policy_input"] = str(policy_path)
        output["policy_name"] = policy.name
        output["all_policy_pass"] = all_policy_pass
    return output


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ws-cae",
        description="Read-only WS-CAE cross-chain authority conformance checker",
    )
    parser.add_argument("profile", type=Path, help="JSON profile or batch document")
    parser.add_argument("--policy", type=Path, help="optional relying-party policy JSON")
    parser.add_argument("--pretty", action="store_true", help="pretty-print JSON output")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = assess_path(args.profile, args.policy)
    except ProfileInputError as exc:
        print(json.dumps({"spec": "WS-CAE-1", "input_error": str(exc)}, sort_keys=True))
        return 2

    indent = 2 if args.pretty else None
    print(json.dumps(result, indent=indent, sort_keys=True))
    passed = result["all_valid"] and result.get("all_policy_pass", True)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

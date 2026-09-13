"""Standalone WS-CAE read-only conformance CLI."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .policy import Policy, evaluate
from .reference import CONSENSUS_STATES, PQ_AUTH_STATES, Profile, assess

PROFILE_FIELDS = {
    "ecosystem", "adapter_class", "implementation_maturity", "stable_authority_id",
    "authenticator_replaceable", "pq_authorization_state", "policy_state_documented",
    "recovery_state_documented", "domain_binding_documented", "evidence_state_documented",
    "consensus_pq_state",
}
PROFILE_REQUIRED = PROFILE_FIELDS - {"consensus_pq_state"}
POLICY_FIELDS = {
    "name", "minimum_maturity", "accepted_pq_authorization_states", "accepted_consensus_states",
    "require_stable_authority_id", "require_authenticator_replaceable",
    "require_policy_state_documented", "require_recovery_state_documented",
    "require_domain_binding_documented", "require_evidence_state_documented",
}


class InputError(ValueError):
    pass


def _json(path: Path, label: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise InputError(f"cannot read {label} {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise InputError(f"invalid JSON in {label} {path}: {exc}") from exc


def _bool(raw: dict, field: str, default: bool | None = None) -> bool:
    if field not in raw:
        if default is None:
            raise InputError(f"missing required field: {field}")
        return default
    value = raw[field]
    if type(value) is not bool:
        raise InputError(f"{field} must be boolean")
    return value


def parse_profile(raw: Any) -> Profile:
    if not isinstance(raw, dict):
        raise InputError("profile must be an object")
    missing = sorted(PROFILE_REQUIRED - set(raw))
    if missing:
        raise InputError("missing required field(s): " + ", ".join(missing))
    unknown = sorted(set(raw) - PROFILE_FIELDS)
    if unknown:
        raise InputError("unknown profile field(s): " + ", ".join(unknown))
    for field in ("ecosystem", "adapter_class", "implementation_maturity", "pq_authorization_state"):
        if not isinstance(raw[field], str) or not raw[field].strip():
            raise InputError(f"{field} must be a non-empty string")
    consensus = raw.get("consensus_pq_state", "CLASSICAL_OR_UNPROVEN")
    if not isinstance(consensus, str) or not consensus:
        raise InputError("consensus_pq_state must be a non-empty string")
    return Profile(
        ecosystem=raw["ecosystem"], adapter_class=raw["adapter_class"],
        implementation_maturity=raw["implementation_maturity"],
        stable_authority_id=_bool(raw, "stable_authority_id"),
        authenticator_replaceable=_bool(raw, "authenticator_replaceable"),
        pq_authorization_state=raw["pq_authorization_state"],
        policy_state_documented=_bool(raw, "policy_state_documented"),
        recovery_state_documented=_bool(raw, "recovery_state_documented"),
        domain_binding_documented=_bool(raw, "domain_binding_documented"),
        evidence_state_documented=_bool(raw, "evidence_state_documented"),
        consensus_pq_state=consensus,
    )


def parse_policy(raw: Any) -> Policy:
    if not isinstance(raw, dict):
        raise InputError("policy must be an object")
    unknown = sorted(set(raw) - POLICY_FIELDS)
    if unknown:
        raise InputError("unknown policy field(s): " + ", ".join(unknown))
    name = raw.get("name")
    if not isinstance(name, str) or not name.strip():
        raise InputError("policy name must be a non-empty string")
    pq = raw.get("accepted_pq_authorization_states", sorted(PQ_AUTH_STATES))
    consensus = raw.get("accepted_consensus_states", sorted(CONSENSUS_STATES))
    if not isinstance(pq, list) or not pq or any(not isinstance(x, str) for x in pq):
        raise InputError("accepted_pq_authorization_states must be a non-empty string array")
    if not isinstance(consensus, list) or not consensus or any(not isinstance(x, str) for x in consensus):
        raise InputError("accepted_consensus_states must be a non-empty string array")
    return Policy(
        name=name,
        minimum_maturity=raw.get("minimum_maturity", "ROADMAP"),
        accepted_pq_authorization_states=tuple(pq),
        accepted_consensus_states=tuple(consensus),
        require_stable_authority_id=_bool(raw, "require_stable_authority_id", False),
        require_authenticator_replaceable=_bool(raw, "require_authenticator_replaceable", False),
        require_policy_state_documented=_bool(raw, "require_policy_state_documented", False),
        require_recovery_state_documented=_bool(raw, "require_recovery_state_documented", False),
        require_domain_binding_documented=_bool(raw, "require_domain_binding_documented", True),
        require_evidence_state_documented=_bool(raw, "require_evidence_state_documented", True),
    )


def load_profiles(path: Path) -> list[Profile]:
    raw = _json(path, "profile")
    if isinstance(raw, dict) and "profiles" in raw:
        if set(raw) != {"profiles"} or not isinstance(raw["profiles"], list) or not raw["profiles"]:
            raise InputError("batch must contain only a non-empty profiles array")
        return [parse_profile(item) for item in raw["profiles"]]
    return [parse_profile(raw)]


def run(profile_path: Path, policy_path: Path | None = None) -> dict:
    profiles = load_profiles(profile_path)
    policy = parse_policy(_json(policy_path, "policy")) if policy_path else None
    results = []
    all_valid = True
    all_policy_pass = True
    for profile in profiles:
        ref = assess(profile)
        all_valid = all_valid and ref.valid
        item = {"ecosystem": profile.ecosystem, "adapter_class": profile.adapter_class, "assessment": ref.to_dict()}
        if policy:
            p = evaluate(profile, ref, policy)
            item["policy"] = p.to_dict()
            all_policy_pass = all_policy_pass and p.passed
        results.append(item)
    output = {"spec": "WS-CAE-1", "tool": "ws-cae-standalone", "profile_count": len(results), "all_valid": all_valid, "results": results}
    if policy:
        output.update({"policy_name": policy.name, "all_policy_pass": all_policy_pass})
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only WS-CAE authority conformance checker")
    parser.add_argument("profile", type=Path)
    parser.add_argument("--policy", type=Path)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)
    try:
        output = run(args.profile, args.policy)
    except InputError as exc:
        print(json.dumps({"spec": "WS-CAE-1", "input_error": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(output, indent=2 if args.pretty else None, sort_keys=True))
    return 0 if output["all_valid"] and output.get("all_policy_pass", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())

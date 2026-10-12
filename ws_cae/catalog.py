from __future__ import annotations

import argparse
import json
from pathlib import Path

from .cli import InputError, _json, parse_policy
from .patch_cli import parse_patch
from .patch_diff import fingerprint
from .policy import evaluate
from .reference import assess


def build(paths: list[Path], policy_path: Path | None = None) -> dict:
    if not paths:
        raise InputError("at least one patch path is required")
    policy = parse_policy(_json(policy_path, "policy")) if policy_path else None
    rows = []
    seen = set()
    for path in paths:
        raw = _json(path, "patch")
        patch = parse_patch(raw)
        key = patch.chain.strip().lower()
        if key in seen:
            raise InputError(f"duplicate chain in catalog: {patch.chain}")
        seen.add(key)
        ref = assess(patch.profile)
        row = {
            "chain": patch.chain,
            "adapter_class": patch.profile.adapter_class,
            "implementation_maturity": patch.profile.implementation_maturity,
            "protocol_commitment_state": patch.profile.protocol_commitment_state,
            "pq_authorization_state": patch.profile.pq_authorization_state,
            "consensus_pq_state": patch.profile.consensus_pq_state,
            "stable_authority_id": patch.profile.stable_authority_id,
            "authenticator_replaceable": patch.profile.authenticator_replaceable,
            "profile_valid": ref.valid,
            "patch_sha256": fingerprint(raw),
            "evidence_count": len(patch.evidence),
        }
        if policy:
            policy_result = evaluate(patch.profile, ref, policy)
            row["policy_pass"] = policy_result.passed
            row["policy_failures"] = list(policy_result.failures)
        rows.append(row)
    rows.sort(key=lambda item: item["chain"].lower())
    output = {
        "spec": "WS-CAE-CHAIN-CATALOG-1",
        "chain_count": len(rows),
        "chains": rows,
    }
    if policy:
        output["policy_name"] = policy.name
        output["all_policy_pass"] = all(row["policy_pass"] for row in rows)
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a normalized catalog from WS-CAE chain patches")
    parser.add_argument("patches", nargs="+", type=Path)
    parser.add_argument("--policy", type=Path)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = build(args.patches, args.policy)
    except InputError as exc:
        print(json.dumps({"spec": "WS-CAE-CHAIN-CATALOG-1", "input_error": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(result, indent=2 if args.pretty else None, sort_keys=True))
    return 0 if result.get("all_policy_pass", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())

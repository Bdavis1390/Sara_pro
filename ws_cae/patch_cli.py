from __future__ import annotations

import argparse
import json
from pathlib import Path

from .cli import InputError, _json, parse_policy, parse_profile
from .patch import ChainPatch, EvidenceRef, assess_patch
from .policy import evaluate
from .reference import assess

PATCH_FIELDS = {"spec", "chain", "profile", "evidence"}
EVIDENCE_FIELDS = {"label", "url", "claim"}


def parse_patch(raw: object) -> ChainPatch:
    if not isinstance(raw, dict):
        raise InputError("patch must be an object")
    unknown = sorted(set(raw) - PATCH_FIELDS)
    if unknown:
        raise InputError("unknown patch field(s): " + ", ".join(unknown))
    missing = sorted(PATCH_FIELDS - set(raw))
    if missing:
        raise InputError("missing patch field(s): " + ", ".join(missing))
    if not isinstance(raw["spec"], str) or not isinstance(raw["chain"], str):
        raise InputError("spec and chain must be strings")
    profile = parse_profile(raw["profile"])
    if not isinstance(raw["evidence"], list):
        raise InputError("evidence must be an array")
    refs = []
    for index, item in enumerate(raw["evidence"]):
        if not isinstance(item, dict):
            raise InputError(f"evidence[{index}] must be an object")
        unknown_evidence = sorted(set(item) - EVIDENCE_FIELDS)
        if unknown_evidence:
            raise InputError(
                f"unknown evidence[{index}] field(s): " + ", ".join(unknown_evidence)
            )
        missing_evidence = sorted(EVIDENCE_FIELDS - set(item))
        if missing_evidence:
            raise InputError(
                f"missing evidence[{index}] field(s): " + ", ".join(missing_evidence)
            )
        if any(not isinstance(item[field], str) for field in EVIDENCE_FIELDS):
            raise InputError(f"evidence[{index}] fields must be strings")
        refs.append(EvidenceRef(item["label"], item["url"], item["claim"]))
    return ChainPatch(raw["spec"], raw["chain"], profile, tuple(refs))


def run(patch_path: Path, policy_path: Path | None = None) -> dict:
    patch = parse_patch(_json(patch_path, "patch"))
    patch_result = assess_patch(patch)
    output = {
        "spec": patch.spec,
        "chain": patch.chain,
        "patch": patch_result.to_dict(),
    }
    if policy_path:
        policy = parse_policy(_json(policy_path, "policy"))
        reference = assess(patch.profile)
        policy_result = evaluate(patch.profile, reference, policy)
        output["policy"] = policy_result.to_dict()
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="WS-CAE chain patch checker")
    parser.add_argument("patch", type=Path)
    parser.add_argument("--policy", type=Path)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)
    try:
        output = run(args.patch, args.policy)
    except InputError as exc:
        print(json.dumps({"spec": "WS-CAE-CHAIN-PATCH-1", "input_error": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(output, indent=2 if args.pretty else None, sort_keys=True))
    valid = output["patch"]["valid"]
    policy_passed = output.get("policy", {}).get("passed", True)
    return 0 if valid and policy_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

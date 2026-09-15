from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from .cli import InputError, _json
from .patch_cli import parse_patch

RISK_FIELDS = {
    "implementation_maturity",
    "stable_authority_id",
    "authenticator_replaceable",
    "pq_authorization_state",
    "policy_state_documented",
    "recovery_state_documented",
    "domain_binding_documented",
    "evidence_state_documented",
    "consensus_pq_state",
    "protocol_commitment_state",
}


def fingerprint(raw: object) -> str:
    canonical = json.dumps(raw, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def compare(old_path: Path, new_path: Path) -> dict:
    old_raw = _json(old_path, "old patch")
    new_raw = _json(new_path, "new patch")
    old_patch = parse_patch(old_raw)
    new_patch = parse_patch(new_raw)
    if old_patch.chain.strip().lower() != new_patch.chain.strip().lower():
        raise InputError("patch comparison requires the same chain")

    old_profile = asdict(old_patch.profile)
    new_profile = asdict(new_patch.profile)
    changes = []
    for field in sorted(set(old_profile) | set(new_profile)):
        before = old_profile.get(field)
        after = new_profile.get(field)
        if before != after:
            changes.append(
                {
                    "field": field,
                    "before": before,
                    "after": after,
                    "risk_relevant": field in RISK_FIELDS,
                }
            )

    old_urls = {ref.url for ref in old_patch.evidence}
    new_urls = {ref.url for ref in new_patch.evidence}
    return {
        "spec": "WS-CAE-CHAIN-PATCH-DIFF-1",
        "chain": old_patch.chain,
        "old_sha256": fingerprint(old_raw),
        "new_sha256": fingerprint(new_raw),
        "changed": bool(changes or old_urls != new_urls),
        "profile_changes": changes,
        "evidence_added": sorted(new_urls - old_urls),
        "evidence_removed": sorted(old_urls - new_urls),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compare two WS-CAE chain patches")
    parser.add_argument("old", type=Path)
    parser.add_argument("new", type=Path)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = compare(args.old, args.new)
    except InputError as exc:
        print(json.dumps({"spec": "WS-CAE-CHAIN-PATCH-DIFF-1", "input_error": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(result, indent=2 if args.pretty else None, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

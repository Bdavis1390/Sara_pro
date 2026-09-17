from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from .cli import InputError, _json
from .continuity_adapter import from_chain_patch
from .continuity_manifest import envelope
from .patch_cli import parse_patch


def _snapshot_id(content_ids: list[str]) -> str:
    payload = json.dumps(sorted(content_ids), separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def build(paths: list[Path], *, version: str, as_of: str) -> dict:
    if not paths:
        raise InputError("at least one patch path is required")
    rows = []
    seen = set()
    for path in paths:
        patch = parse_patch(_json(path, "patch"))
        key = patch.chain.strip().lower()
        if key in seen:
            raise InputError(f"duplicate chain: {patch.chain}")
        seen.add(key)
        item = envelope(from_chain_patch(patch, version=version, as_of=as_of))
        rows.append({
            "subject": patch.chain,
            "content_id": item["content_id"],
            "valid": item["valid"],
            "implementation_maturity": patch.profile.implementation_maturity,
            "protocol_commitment_state": patch.profile.protocol_commitment_state,
            "pq_authorization_state": patch.profile.pq_authorization_state,
            "consensus_pq_state": patch.profile.consensus_pq_state,
        })
    rows.sort(key=lambda row: row["subject"].lower())
    ids = [row["content_id"] for row in rows]
    return {
        "spec": "WS-CAE-CONTINUITY-SNAPSHOT-1",
        "as_of": as_of,
        "manifest_count": len(rows),
        "snapshot_id": _snapshot_id(ids),
        "all_valid": all(row["valid"] for row in rows),
        "manifests": rows,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a deterministic WS-CAE continuity snapshot")
    parser.add_argument("patches", nargs="+", type=Path)
    parser.add_argument("--version", default="1")
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = build(args.patches, version=args.version, as_of=args.as_of)
    except InputError as exc:
        print(json.dumps({"spec":"WS-CAE-CONTINUITY-SNAPSHOT-1","input_error":str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(result, indent=2 if args.pretty else None, sort_keys=True))
    return 0 if result["all_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

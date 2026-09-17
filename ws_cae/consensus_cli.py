from __future__ import annotations

import argparse
import json
from pathlib import Path

from .consensus_continuity import (
    ConsensusContinuityProfile,
    ConsensusEvidenceRef,
    envelope,
)


class ConsensusInputError(ValueError):
    pass


def parse_profile(raw: object) -> ConsensusContinuityProfile:
    if not isinstance(raw, dict):
        raise ConsensusInputError("profile must be an object")
    required = {
        "subject_id", "consensus_family", "mechanism_name", "resource_proof",
        "finality_model", "participant_auth_primitive", "participant_key_agility",
        "local_validation_mode", "consensus_pq_state", "resource_proof_agility",
        "poc_subtype", "evidence",
    }
    unknown = sorted(set(raw) - required)
    missing = sorted(required - set(raw))
    if unknown:
        raise ConsensusInputError("unknown field(s): " + ", ".join(unknown))
    if missing:
        raise ConsensusInputError("missing field(s): " + ", ".join(missing))
    if not isinstance(raw["evidence"], list):
        raise ConsensusInputError("evidence must be an array")
    refs = []
    for index, item in enumerate(raw["evidence"]):
        if not isinstance(item, dict) or set(item) != {"label", "url", "claim"}:
            raise ConsensusInputError(f"evidence[{index}] must contain label, url, claim")
        if any(not isinstance(item[k], str) for k in ("label", "url", "claim")):
            raise ConsensusInputError(f"evidence[{index}] values must be strings")
        refs.append(ConsensusEvidenceRef(item["label"], item["url"], item["claim"]))
    scalar_fields = required - {"evidence"}
    if any(not isinstance(raw[k], str) for k in scalar_fields):
        raise ConsensusInputError("all non-evidence fields must be strings")
    return ConsensusContinuityProfile(
        subject_id=raw["subject_id"],
        consensus_family=raw["consensus_family"],
        mechanism_name=raw["mechanism_name"],
        resource_proof=raw["resource_proof"],
        finality_model=raw["finality_model"],
        participant_auth_primitive=raw["participant_auth_primitive"],
        participant_key_agility=raw["participant_key_agility"],
        local_validation_mode=raw["local_validation_mode"],
        consensus_pq_state=raw["consensus_pq_state"],
        resource_proof_agility=raw["resource_proof_agility"],
        poc_subtype=raw["poc_subtype"],
        evidence=tuple(refs),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a WS-CAE consensus-continuity profile")
    parser.add_argument("profile", type=Path)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)
    try:
        raw = json.loads(args.profile.read_text(encoding="utf-8"))
        result = envelope(parse_profile(raw))
    except (OSError, json.JSONDecodeError, ConsensusInputError) as exc:
        print(json.dumps({"spec": "WS-CAE-CONSENSUS-CONTINUITY-1", "input_error": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(result, indent=2 if args.pretty else None, sort_keys=True))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

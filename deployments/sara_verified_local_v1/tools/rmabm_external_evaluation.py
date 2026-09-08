from __future__ import annotations

import argparse
import json
from pathlib import Path

from worldshepherd_sara.rmabm_external_evaluation import (
    build_external_evaluation_attestation,
    build_external_evaluation_challenge,
    execute_external_evaluation_challenge,
)


def _write_json(path: Path | None, payload: dict) -> None:
    text = json.dumps(payload, indent=2, sort_keys=True)
    if path is None:
        print(text)
        return
    path.write_text(text + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Generate and execute an evaluator-seeded W-RMABM synthetic reproduction challenge. "
            "This tool provides no targeting, fire-control, launch, intercept, or engagement authority."
        )
    )
    parser.add_argument("--challenge-id", required=True)
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument(
        "--requested-action",
        default="advisory_dissemination",
        choices=["advisory_dissemination", "fire_control_cue", "weapon_cue", "engage", "intercept", "launch", "target_designation"],
    )
    parser.add_argument(
        "--human-authority",
        default="independent-evaluator",
        help="Identified evaluator authority label. Use --no-human-authority to test the HOLD gate.",
    )
    parser.add_argument("--no-human-authority", action="store_true")
    parser.add_argument("--observation-count", type=int, default=4)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    authority = None if args.no_human_authority else args.human_authority
    challenge = build_external_evaluation_challenge(
        challenge_id=args.challenge_id,
        evaluator_seed=args.seed,
        requested_action=args.requested_action,
        human_authority=authority,
        observation_count=args.observation_count,
    )
    result = execute_external_evaluation_challenge(challenge)
    attestation = build_external_evaluation_attestation(challenge=challenge, result=result)

    payload = {
        "challenge": challenge.model_dump(mode="json"),
        "result": result.model_dump(mode="json"),
        "attestation": attestation.model_dump(mode="json"),
    }
    _write_json(args.output, payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

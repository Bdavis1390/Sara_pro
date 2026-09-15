from __future__ import annotations

import hashlib
import json
import random
from typing import Any, Literal

from pydantic import BaseModel, Field

from .rmabm import ALLOWED_ACTION, BLOCKED_ACTIONS, RMABMResult, run_synthetic_rmabm


EXTERNAL_EVALUATION_BOUNDARY = (
    "UNCLASSIFIED SYNTHETIC INDEPENDENT-REPRODUCTION CANDIDATE ONLY; A PASS SHOWS "
    "REPRODUCTION OF BOUNDED SOFTWARE BEHAVIOR, NOT GOLDEN DOME, BAE, SDA, SSC, "
    "SPACE FORCE, MDA, OR OPERATIONAL MISSILE-DEFENSE VALIDATION. NO TARGETING, "
    "FIRE-CONTROL, WEAPON-CUEING, LAUNCH, INTERCEPT, OR ENGAGEMENT AUTHORITY IS PROVIDED."
)


class ExternalEvaluationChallenge(BaseModel):
    schema_version: Literal["ws-rmabm-g4-challenge-v1"] = "ws-rmabm-g4-challenge-v1"
    challenge_id: str = Field(min_length=1)
    evaluator_seed: int
    claims_boundary: str = EXTERNAL_EVALUATION_BOUNDARY
    fixture: dict[str, Any]
    challenge_sha256: str = Field(min_length=64, max_length=64)


class ExternalEvaluationAttestation(BaseModel):
    schema_version: Literal["ws-rmabm-g4-attestation-v1"] = "ws-rmabm-g4-attestation-v1"
    challenge_id: str
    challenge_sha256: str = Field(min_length=64, max_length=64)
    result_audit_sha256: str = Field(min_length=64, max_length=64)
    replay_sha256: str = Field(min_length=64, max_length=64)
    decision_counts: dict[str, int]
    claims_boundary: str = EXTERNAL_EVALUATION_BOUNDARY
    attestation_sha256: str = Field(min_length=64, max_length=64)


def _canonical_bytes(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def _sha256(payload: Any) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _source_digest(*, challenge_id: str, seed: int, index: int, sensor_id: str) -> str:
    source_material = {
        "challenge_id": challenge_id,
        "seed": seed,
        "index": index,
        "sensor_id": sensor_id,
        "source_class": "synthetic_evaluator_surrogate",
    }
    return _sha256(source_material)


def build_external_evaluation_challenge(
    *,
    challenge_id: str,
    evaluator_seed: int,
    requested_action: str = ALLOWED_ACTION,
    human_authority: str | None = "independent-evaluator",
    observation_count: int = 4,
) -> ExternalEvaluationChallenge:
    """Build a deterministic evaluator-seeded synthetic reproduction challenge.

    The challenge is intentionally generic: two-dimensional surrogate observations only.
    It contains no real threat trajectory, interceptor model, engagement logic, or
    proprietary government/vendor interface.
    """
    normalized_action = requested_action.strip().lower()
    if normalized_action != ALLOWED_ACTION and normalized_action not in BLOCKED_ACTIONS:
        raise ValueError("requested_action must be advisory_dissemination or an explicitly blocked action")
    if observation_count < 2 or observation_count > 20:
        raise ValueError("observation_count must be between 2 and 20")

    rng = random.Random(evaluator_seed)
    observations: list[dict[str, Any]] = []
    sensor_count = max(2, min(4, observation_count))
    for index in range(observation_count):
        sensor_id = f"surrogate-sensor-{index % sensor_count + 1}"
        observations.append(
            {
                "observation_id": f"eval-{index + 1:03d}",
                "sensor_id": sensor_id,
                "t_seconds": round(98.0 + rng.uniform(0.0, 0.75), 6),
                "x": round(rng.uniform(-0.15, 0.15), 6),
                "y": round(rng.uniform(-0.15, 0.15), 6),
                "confidence": round(rng.uniform(0.94, 0.99), 6),
                "source_sha256": _source_digest(
                    challenge_id=challenge_id,
                    seed=evaluator_seed,
                    index=index,
                    sensor_id=sensor_id,
                ),
                "source_status": "synthetic",
            }
        )

    fixture = {
        "scenario_id": challenge_id,
        "scenario_time_seconds": 100.0,
        "requested_action": normalized_action,
        "human_authority": human_authority,
        "policy": {
            "min_track_confidence": 0.75,
            "min_independent_sensors": 2,
            "max_observation_age_seconds": 8.0,
            "require_identified_human_authority": True,
            "permitted_action": ALLOWED_ACTION,
        },
        "max_spatial_distance": 2.0,
        "max_time_delta_seconds": 3.0,
        "observations": observations,
        "events": [],
    }
    unsigned = {
        "schema_version": "ws-rmabm-g4-challenge-v1",
        "challenge_id": challenge_id,
        "evaluator_seed": evaluator_seed,
        "claims_boundary": EXTERNAL_EVALUATION_BOUNDARY,
        "fixture": fixture,
    }
    return ExternalEvaluationChallenge(**unsigned, challenge_sha256=_sha256(unsigned))


def verify_external_evaluation_challenge(
    challenge: ExternalEvaluationChallenge | dict[str, Any],
) -> ExternalEvaluationChallenge:
    parsed = (
        challenge
        if isinstance(challenge, ExternalEvaluationChallenge)
        else ExternalEvaluationChallenge.model_validate(challenge)
    )
    unsigned = parsed.model_dump(mode="json", exclude={"challenge_sha256"})
    expected = _sha256(unsigned)
    if expected != parsed.challenge_sha256:
        raise ValueError("external evaluation challenge integrity check failed")
    return parsed


def execute_external_evaluation_challenge(
    challenge: ExternalEvaluationChallenge | dict[str, Any],
) -> RMABMResult:
    verified = verify_external_evaluation_challenge(challenge)
    return run_synthetic_rmabm(verified.fixture)


def build_external_evaluation_attestation(
    *,
    challenge: ExternalEvaluationChallenge | dict[str, Any],
    result: RMABMResult,
) -> ExternalEvaluationAttestation:
    verified = verify_external_evaluation_challenge(challenge)
    counts = {"AUTHORIZED_ADVISORY": 0, "HOLD": 0, "BLOCK": 0}
    for decision in result.decisions:
        counts[decision.decision] += 1

    unsigned = {
        "schema_version": "ws-rmabm-g4-attestation-v1",
        "challenge_id": verified.challenge_id,
        "challenge_sha256": verified.challenge_sha256,
        "result_audit_sha256": result.audit_sha256,
        "replay_sha256": result.metrics.deterministic_replay_digest,
        "decision_counts": counts,
        "claims_boundary": EXTERNAL_EVALUATION_BOUNDARY,
    }
    return ExternalEvaluationAttestation(**unsigned, attestation_sha256=_sha256(unsigned))

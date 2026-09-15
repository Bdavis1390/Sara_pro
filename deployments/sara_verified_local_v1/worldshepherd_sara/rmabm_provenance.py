from __future__ import annotations

import base64
import copy
import hashlib
import time
from typing import Any

from pydantic import BaseModel, Field

from .rmabm import RMABMResult, run_synthetic_rmabm


class BoundSource(BaseModel):
    observation_id: str = Field(min_length=1)
    payload_b64: str = Field(min_length=1)
    claimed_sha256: str = Field(min_length=64, max_length=64)

    def payload_bytes(self) -> bytes:
        try:
            return base64.b64decode(self.payload_b64.encode("ascii"), validate=True)
        except Exception as exc:  # noqa: BLE001 - convert decoder errors to validation evidence
            raise ValueError(f"invalid base64 payload for {self.observation_id}") from exc

    def actual_sha256(self) -> str:
        return hashlib.sha256(self.payload_bytes()).hexdigest()

    def verify(self) -> None:
        if self.actual_sha256() != self.claimed_sha256.lower():
            raise ValueError(f"provenance digest mismatch for observation_id={self.observation_id!r}")


class VerifiedRMABMResult(BaseModel):
    rmabm: RMABMResult
    verified_source_count: int = Field(ge=0)
    source_manifest_sha256: str = Field(min_length=64, max_length=64)


def _manifest_digest(sources: list[BoundSource]) -> str:
    canonical = "\n".join(
        f"{source.observation_id}:{source.claimed_sha256.lower()}"
        for source in sorted(sources, key=lambda item: item.observation_id)
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def run_verified_rmabm(fixture: dict[str, Any], bound_sources: list[dict[str, Any] | BoundSource]) -> VerifiedRMABMResult:
    """Verify source bytes against claimed digests before the synthetic G1/G2 mission thread.

    This adds provenance-integrity evidence only. It does not add operational tracking,
    targeting, fire-control, or engagement functionality.
    """
    sources = [item if isinstance(item, BoundSource) else BoundSource.model_validate(item) for item in bound_sources]
    by_observation = {source.observation_id: source for source in sources}
    if len(by_observation) != len(sources):
        raise ValueError("duplicate bound-source observation identifiers")

    observations = list(fixture.get("observations", []))
    expected_ids = {str(item["observation_id"]) for item in observations}
    if set(by_observation) != expected_ids:
        missing = sorted(expected_ids - set(by_observation))
        extra = sorted(set(by_observation) - expected_ids)
        raise ValueError(f"bound-source coverage mismatch: missing={missing}, extra={extra}")

    verified_fixture = copy.deepcopy(fixture)
    for observation in verified_fixture["observations"]:
        observation_id = str(observation["observation_id"])
        source = by_observation[observation_id]
        source.verify()
        if str(observation["source_sha256"]).lower() != source.claimed_sha256.lower():
            raise ValueError(f"fixture/source manifest digest mismatch for observation_id={observation_id!r}")

    result = run_synthetic_rmabm(verified_fixture)
    return VerifiedRMABMResult(
        rmabm=result,
        verified_source_count=len(sources),
        source_manifest_sha256=_manifest_digest(sources),
    )


class SyntheticScaleResult(BaseModel):
    track_pair_count: int = Field(ge=1)
    observation_count: int = Field(ge=2)
    decision_count: int = Field(ge=0)
    authorized_advisory_count: int = Field(ge=0)
    elapsed_ms: float = Field(gt=0.0)
    audit_sha256: str = Field(min_length=64, max_length=64)


def build_synthetic_scale_fixture(*, track_pair_count: int) -> dict[str, Any]:
    """Build a deterministic, unclassified scale fixture of separated two-source clusters."""
    if track_pair_count < 1:
        raise ValueError("track_pair_count must be >= 1")

    observations: list[dict[str, Any]] = []
    for index in range(track_pair_count):
        base = float(index * 10)
        for suffix, sensor, offset, confidence, digest_char in (
            ("A", f"SYN-A-{index}", 0.0, 0.90, "a"),
            ("B", f"SYN-B-{index}", 0.25, 0.88, "b"),
        ):
            observations.append(
                {
                    "observation_id": f"SCALE-{index:05d}-{suffix}",
                    "sensor_id": sensor,
                    "t_seconds": 100.0 + offset,
                    "x": base,
                    "y": base + offset,
                    "confidence": confidence,
                    "source_sha256": digest_char * 64,
                    "source_status": "synthetic",
                }
            )

    return {
        "scenario_id": f"WS-RMABM-G2B-SCALE-{track_pair_count}",
        "scenario_time_seconds": 102.0,
        "requested_action": "advisory_dissemination",
        "human_authority": "identified-human-test-authority",
        "max_spatial_distance": 2.0,
        "max_time_delta_seconds": 3.0,
        "policy": {
            "min_track_confidence": 0.75,
            "min_independent_sensors": 2,
            "max_observation_age_seconds": 8.0,
            "require_identified_human_authority": True,
            "permitted_action": "advisory_dissemination",
        },
        "observations": observations,
        "events": [],
    }


def measure_synthetic_scale(*, track_pair_count: int) -> SyntheticScaleResult:
    fixture = build_synthetic_scale_fixture(track_pair_count=track_pair_count)
    start_ns = time.perf_counter_ns()
    result = run_synthetic_rmabm(fixture)
    elapsed_ms = max((time.perf_counter_ns() - start_ns) / 1_000_000.0, 0.000001)
    authorized = sum(1 for decision in result.decisions if decision.decision == "AUTHORIZED_ADVISORY")
    return SyntheticScaleResult(
        track_pair_count=track_pair_count,
        observation_count=len(fixture["observations"]),
        decision_count=len(result.decisions),
        authorized_advisory_count=authorized,
        elapsed_ms=elapsed_ms,
        audit_sha256=result.audit_sha256,
    )

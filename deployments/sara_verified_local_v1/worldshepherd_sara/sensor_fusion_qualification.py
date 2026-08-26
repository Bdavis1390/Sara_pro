from __future__ import annotations

from math import hypot
from typing import Any

from .qualification import (
    CapabilityStatus,
    EvidenceScope,
    QualificationEvidenceRecord,
    RequirementDeltaRecord,
    ResultStatus,
    canonical_digest,
    compile_qualification_bundle,
)
from .sensor_fusion import Observation, fuse_observations, fusion_graph


def qualify_synthetic_sensor_fusion(
    *,
    fixture: dict[str, Any],
    requirement: RequirementDeltaRecord,
    software_commit: str,
    executed_utc: str,
    operator: str,
) -> dict[str, Any]:
    observations = [Observation.model_validate(item) for item in fixture["observations"]]
    association = fixture["association"]
    tracks = fuse_observations(
        observations,
        max_spatial_distance=float(association["max_spatial_distance"]),
        max_time_delta_seconds=float(association["max_time_delta_seconds"]),
    )
    truth = sorted(fixture["truth"], key=lambda item: (float(item["x"]), float(item["y"])))
    ordered_tracks = sorted(tracks, key=lambda track: (track.x, track.y))
    position_errors = [
        hypot(track.x - float(target["x"]), track.y - float(target["y"]))
        for track, target in zip(ordered_tracks, truth)
    ]
    preserved = sorted(
        observation_id
        for track in tracks
        for observation_id in track.source_observation_ids
    ) == sorted(item["observation_id"] for item in fixture["observations"])
    max_error = max(position_errors) if position_errors else float("inf")
    expected = fixture["expected"]
    passed = (
        len(tracks) == int(expected["fused_track_count"])
        and max_error <= float(expected["max_position_error"])
        and preserved is bool(expected["all_source_observations_preserved"])
    )
    graph = fusion_graph(
        graph_id=fixture["fixture_id"], observations=observations, tracks=tracks
    )

    evidence = QualificationEvidenceRecord(
        qualification_id="WS-QE-2026-6001",
        requirement_id=requirement.requirement_delta_id,
        test_id="sensor_fusion_synthetic_v1",
        evidence_scope=EvidenceScope.SOFTWARE,
        capability_status=CapabilityStatus.PROVEN_INTERNALLY,
        environment_digest=canonical_digest(
            {"fixture_id": fixture["fixture_id"], "classification": fixture["classification"]}
        ),
        configuration_digest=canonical_digest(association),
        inputs=[{"observation_count": len(observations), "truth_count": len(truth)}],
        outputs=[
            {
                "fused_track_count": len(tracks),
                "position_errors": position_errors,
                "max_position_error": max_error,
                "source_observations_preserved": preserved,
                "tracks": [
                    {
                        "track_id": track.track_id,
                        "x": track.x,
                        "y": track.y,
                        "t_seconds": track.t_seconds,
                        "confidence": track.confidence,
                        "source_observation_ids": list(track.source_observation_ids),
                        "source_sensor_ids": list(track.source_sensor_ids),
                    }
                    for track in tracks
                ],
            }
        ],
        metrics=[
            {"name": "fused_track_count", "value": len(tracks), "expected": expected["fused_track_count"]},
            {"name": "max_position_error", "value": max_error, "target_max": expected["max_position_error"]},
            {"name": "source_observations_preserved", "value": preserved},
        ],
        uncertainty=[
            {"name": "operational_sensor_validity", "state": "NOT_EVALUATED"},
            {"name": "track_association_generalization", "state": "NOT_EVALUATED"},
        ],
        result=ResultStatus.PASS if passed else ResultStatus.FAIL,
        rationale=(
            "Deterministic synthetic association/fusion met frozen truth and provenance targets"
            if passed
            else "Synthetic fusion diverged from one or more frozen truth/provenance targets"
        ),
        negative_evidence=[] if passed else [
            {
                "observed_track_count": len(tracks),
                "max_position_error": max_error,
                "source_observations_preserved": preserved,
            }
        ],
        software_commit=software_commit,
        executed_utc=executed_utc,
        operator=operator,
    )
    bundle = compile_qualification_bundle(requirement, [evidence], graph)
    bundle.pop("bundle_digest", None)
    bundle["fixture_id"] = fixture["fixture_id"]
    bundle["scope_note"] = (
        "Synthetic deterministic 2-D sensor-fusion evidence only; no AESA, EO/IR, NAVAIR, classified-sensor, operational tracking, or field-performance claim."
    )
    bundle["bundle_digest"] = canonical_digest(bundle)
    return bundle

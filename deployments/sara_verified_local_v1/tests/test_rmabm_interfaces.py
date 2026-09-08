from __future__ import annotations

import base64
import hashlib

import pytest

from worldshepherd_sara.rmabm import run_synthetic_rmabm
from worldshepherd_sara.rmabm_interfaces import (
    InterfaceConformanceError,
    normalize_interface_batch,
    normalize_interface_record,
)


def _payload(text: str) -> tuple[str, str]:
    raw = text.encode("utf-8")
    return base64.b64encode(raw).decode("ascii"), hashlib.sha256(raw).hexdigest()


def _alpha(*, observation_id: str = "IF-A", t_seconds: float = 15.0) -> dict:
    payload_b64, digest = _payload(f"alpha|{observation_id}|{t_seconds}")
    return {
        "schema_version": "1.0",
        "id": observation_id,
        "sensor": "SYN-ALPHA-SENSOR",
        "t_seconds": t_seconds,
        "position": {"x": 10.0, "y": 10.0},
        "confidence": 0.91,
        "payload_b64": payload_b64,
        "sha256": digest,
    }


def _beta(*, observation_id: str = "IF-B", t_seconds: float = 15.5) -> dict:
    payload_b64, digest = _payload(f"beta|{observation_id}|{t_seconds}")
    return {
        "version": "2026.1",
        "event": {
            "key": observation_id,
            "source": "SYN-BETA-SENSOR",
            "seconds": t_seconds,
        },
        "coords": [10.3, 9.9],
        "quality": {"score": 0.89},
        "blob": {"b64": payload_b64, "digest_sha256": digest},
    }


def test_two_fictional_schemas_normalize_into_one_bounded_advisory_track():
    observations = normalize_interface_batch(
        [
            ("synthetic_beta", _beta()),
            ("synthetic_alpha", _alpha()),
        ]
    )
    fixture = {
        "scenario_id": "WS-RMABM-G2C-IFACE-001",
        "scenario_time_seconds": 20.0,
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
        "observations": [item.model_dump(mode="json") for item in observations],
        "events": [],
    }

    result = run_synthetic_rmabm(fixture)
    assert len(result.decisions) == 1
    assert result.decisions[0].decision == "AUTHORIZED_ADVISORY"
    assert set(result.decisions[0].source_sensor_ids) == {"SYN-ALPHA-SENSOR", "SYN-BETA-SENSOR"}


def test_unknown_alpha_schema_version_is_rejected():
    record = _alpha()
    record["schema_version"] = "9.9"
    with pytest.raises(InterfaceConformanceError, match="unsupported synthetic_alpha"):
        normalize_interface_record(record, family="synthetic_alpha")


def test_tampered_interface_payload_is_rejected_before_normalization():
    record = _beta()
    record["blob"]["b64"] = base64.b64encode(b"tampered-interface-payload").decode("ascii")
    with pytest.raises(InterfaceConformanceError, match="payload digest mismatch"):
        normalize_interface_record(record, family="synthetic_beta")


def test_duplicate_ids_across_fictional_schema_families_are_rejected():
    with pytest.raises(InterfaceConformanceError, match="globally unique"):
        normalize_interface_batch(
            [
                ("synthetic_alpha", _alpha(observation_id="DUP")),
                ("synthetic_beta", _beta(observation_id="DUP")),
            ]
        )


def test_interface_batch_order_is_deterministic():
    observations = normalize_interface_batch(
        [
            ("synthetic_beta", _beta(t_seconds=19.0)),
            ("synthetic_alpha", _alpha(t_seconds=4.0)),
        ]
    )
    assert [item.observation_id for item in observations] == ["IF-A", "IF-B"]

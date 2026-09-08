from __future__ import annotations

import base64
import copy
import hashlib
import json
from pathlib import Path

import pytest

from worldshepherd_sara.rmabm import run_synthetic_rmabm
from worldshepherd_sara.rmabm_provenance import measure_synthetic_scale, run_verified_rmabm

ROOT = Path(__file__).resolve().parents[1]


def _fixture() -> dict:
    return json.loads((ROOT / "fixtures" / "rmabm_g1_synthetic_v1.json").read_text())


def _bind_real_source_bytes(fixture: dict) -> list[dict]:
    sources: list[dict] = []
    for observation in fixture["observations"]:
        payload = (
            f"synthetic-source|{observation['observation_id']}|{observation['sensor_id']}|"
            f"{observation['t_seconds']}|{observation['x']}|{observation['y']}|{observation['confidence']}"
        ).encode("utf-8")
        digest = hashlib.sha256(payload).hexdigest()
        observation["source_sha256"] = digest
        sources.append(
            {
                "observation_id": observation["observation_id"],
                "payload_b64": base64.b64encode(payload).decode("ascii"),
                "claimed_sha256": digest,
            }
        )
    return sources


def test_bound_provenance_accepts_exact_source_bytes():
    fixture = _fixture()
    sources = _bind_real_source_bytes(fixture)
    result = run_verified_rmabm(fixture, sources)

    assert result.verified_source_count == len(fixture["observations"])
    assert len(result.source_manifest_sha256) == 64
    assert result.rmabm.metrics.provenance_completeness == 1.0


def test_bound_provenance_rejects_tampered_source_bytes():
    fixture = _fixture()
    sources = _bind_real_source_bytes(fixture)
    tampered = copy.deepcopy(sources)
    tampered_payload = b"tampered-synthetic-source"
    tampered[0]["payload_b64"] = base64.b64encode(tampered_payload).decode("ascii")

    with pytest.raises(ValueError, match="provenance digest mismatch"):
        run_verified_rmabm(fixture, tampered)


def test_source_disagreement_removes_two_source_authorization():
    fixture = _fixture()
    supporting = next(item for item in fixture["observations"] if item["observation_id"] == "OBS-B")
    supporting["x"] = 35.0
    supporting["y"] = 35.0
    supporting["source_status"] = "synthetic_fault_injected"

    result = run_synthetic_rmabm(fixture)
    assert all(decision.decision != "AUTHORIZED_ADVISORY" for decision in result.decisions)
    assert any(decision.decision == "HOLD" for decision in result.decisions)


def test_clock_skew_makes_supporting_source_stale_and_prevents_authorization():
    fixture = _fixture()
    supporting = next(item for item in fixture["observations"] if item["observation_id"] == "OBS-B")
    supporting["t_seconds"] = 2.0
    supporting["source_status"] = "synthetic_fault_injected"

    result = run_synthetic_rmabm(fixture)
    assert "OBS-B" in result.stale_observation_ids
    assert all(decision.decision != "AUTHORIZED_ADVISORY" for decision in result.decisions)


def test_synthetic_scale_measurement_reports_counts_without_hard_latency_claim():
    first = measure_synthetic_scale(track_pair_count=25)
    second = measure_synthetic_scale(track_pair_count=25)

    assert first.observation_count == 50
    assert first.decision_count == 25
    assert first.authorized_advisory_count == 25
    assert first.elapsed_ms > 0.0
    assert second.elapsed_ms > 0.0
    assert first.audit_sha256 == second.audit_sha256

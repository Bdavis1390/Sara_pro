from __future__ import annotations

import json
from pathlib import Path

import pytest

from worldshepherd_sara.sda_10x_benchmark import (
    G9_PROTOCOL_SCHEMA,
    SdaBenchmarkError,
    SdaBenchmarkMeasurementBundle,
    SdaBenchmarkProtocol,
    SdaMetricMeasurement,
    evaluate_g9,
)


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = ROOT / "fixtures" / "ws_sda_g9_benchmark_protocol_v1.json"
WORKLOAD = "sha256:324cc3d955c08b965f957667b7519e8c358af80c647acbd34611a13d8abe9a94"
ENVIRONMENT = "WS-SDA-G9-REFERENCE-ENV-V1"
BASE_SHA = "1" * 40
CANDIDATE_SHA = "2" * 40


def protocol() -> SdaBenchmarkProtocol:
    return SdaBenchmarkProtocol.model_validate(
        json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    )


def _values():
    security = {
        "unauthorized_observation_acceptance_rate": (0.50, 0.05),
        "replay_mutation_acceptance_rate": (0.40, 0.04),
        "transport_identity_bypass_rate": (0.30, 0.03),
        "release_authorization_mutation_escape_rate": (0.60, 0.06),
        "release_replay_acceptance_rate": (0.20, 0.02),
        "ddil_conflict_auto_resolution_rate": (0.50, 0.05),
        "provenance_tamper_miss_rate": (0.70, 0.07),
        "adapter_secret_exposure_rate": (0.30, 0.03),
        "adapter_network_egress_success_rate": (0.80, 0.08),
        "g8_adversarial_false_negative_rate": (0.10, 0.01),
    }
    utility = {
        "task_success_rate": (0.95, 0.94),
        "false_positive_deny_rate": (0.10, 0.10),
        "p95_ingest_latency_ms": (100.0, 120.0),
        "evidence_completeness_rate": (0.99, 0.99),
        "replay_determinism_rate": (1.0, 1.0),
    }
    return security | utility


def bundle(role: str, *, changes=None, environment=ENVIRONMENT, workload=WORKLOAD):
    changes = changes or {}
    values = _values()
    measurements = []
    for metric in protocol().metrics:
        baseline, candidate = values[metric.metric_id]
        value = baseline if role == "BASELINE" else candidate
        if metric.metric_id in changes:
            value = changes[metric.metric_id]
        measurements.append(
            SdaMetricMeasurement(
                metric_id=metric.metric_id,
                unit=metric.unit,
                value=value,
                sample_count=max(metric.min_samples, 60),
                evidence_ref=f"fixture:{role.lower()}:{metric.metric_id}",
            )
        )
    return SdaBenchmarkMeasurementBundle(
        bundle_id=f"G9-{role}-FIXTURE",
        role=role,
        source_commit=BASE_SHA if role == "BASELINE" else CANDIDATE_SHA,
        environment_id=environment,
        workload_sha256=workload,
        measurements=measurements,
    )


def test_frozen_protocol_has_ten_mandatory_security_metrics_and_five_utility_gates():
    p = protocol()
    assert p.schema == G9_PROTOCOL_SCHEMA
    security = [m for m in p.metrics if m.metric_class.value == "SECURITY" and m.mandatory]
    utility = [m for m in p.metrics if m.metric_class.value == "UTILITY" and m.mandatory]

    assert len(security) == 10
    assert len(utility) == 5
    assert all(m.max_candidate_to_baseline_ratio <= 0.10 for m in security)


def test_every_security_ratio_and_every_utility_gate_must_pass():
    report = evaluate_g9(protocol(), bundle("BASELINE"), bundle("CANDIDATE"))

    assert report.mandatory_security_passed is True
    assert report.mandatory_utility_passed is True
    assert report.ten_x_security_claim_eligible is True
    assert len(report.ten_x_improved_metrics) == 10
    assert report.preserved_zero_invariants == []
    assert all(item.passed for item in report.results)


def test_one_failed_security_metric_blocks_overall_eligibility_without_averaging():
    candidate = bundle(
        "CANDIDATE",
        changes={
            # 0.11 / 0.50 = 0.22, which fails even though the other nine pass.
            "unauthorized_observation_acceptance_rate": 0.11,
            # Make another dimension dramatically better; it cannot compensate.
            "adapter_network_egress_success_rate": 0.0,
        },
    )
    report = evaluate_g9(protocol(), bundle("BASELINE"), candidate)

    failed = {item.metric_id for item in report.results if not item.passed}
    assert failed == {"unauthorized_observation_acceptance_rate"}
    assert report.mandatory_security_passed is False
    assert report.ten_x_security_claim_eligible is False


def test_baseline_zero_is_zero_invariant_not_fake_infinite_improvement():
    baseline = bundle(
        "BASELINE",
        changes={"replay_mutation_acceptance_rate": 0.0},
    )
    candidate = bundle(
        "CANDIDATE",
        changes={"replay_mutation_acceptance_rate": 0.0},
    )

    report = evaluate_g9(protocol(), baseline, candidate)
    item = next(
        row for row in report.results if row.metric_id == "replay_mutation_acceptance_rate"
    )

    assert item.passed is True
    assert item.ratio is None
    assert item.treatment == "BASELINE_ZERO_INVARIANT"
    assert "replay_mutation_acceptance_rate" in report.preserved_zero_invariants
    assert "replay_mutation_acceptance_rate" not in report.ten_x_improved_metrics


def test_zero_baseline_regression_blocks_security_gate():
    baseline = bundle(
        "BASELINE",
        changes={"replay_mutation_acceptance_rate": 0.0},
    )
    candidate = bundle(
        "CANDIDATE",
        changes={"replay_mutation_acceptance_rate": 0.001},
    )

    report = evaluate_g9(protocol(), baseline, candidate)
    item = next(
        row for row in report.results if row.metric_id == "replay_mutation_acceptance_rate"
    )
    assert item.passed is False
    assert report.ten_x_security_claim_eligible is False


def test_utility_regression_blocks_claim_even_if_security_is_ten_x():
    candidate = bundle(
        "CANDIDATE",
        changes={"task_success_rate": 0.80},
    )
    report = evaluate_g9(protocol(), bundle("BASELINE"), candidate)

    assert report.mandatory_security_passed is True
    assert report.mandatory_utility_passed is False
    assert report.ten_x_security_claim_eligible is False


def test_environment_workload_units_samples_and_completeness_fail_closed():
    p = protocol()
    with pytest.raises(SdaBenchmarkError, match="environment IDs differ"):
        evaluate_g9(
            p,
            bundle("BASELINE"),
            bundle("CANDIDATE", environment="OTHER"),
        )

    with pytest.raises(SdaBenchmarkError, match="workloads differ"):
        evaluate_g9(
            p,
            bundle("BASELINE"),
            bundle("CANDIDATE", workload="sha256:" + "f" * 64),
        )

    baseline = bundle("BASELINE")
    candidate = bundle("CANDIDATE")
    candidate.measurements[0] = candidate.measurements[0].model_copy(
        update={"unit": "percent"}
    )
    with pytest.raises(SdaBenchmarkError, match="unit mismatch"):
        evaluate_g9(p, baseline, candidate)

    candidate = bundle("CANDIDATE")
    candidate.measurements[0] = candidate.measurements[0].model_copy(
        update={"sample_count": 1}
    )
    with pytest.raises(SdaBenchmarkError, match="sample count too small"):
        evaluate_g9(p, baseline, candidate)

    candidate = bundle("CANDIDATE")
    candidate.measurements.pop()
    with pytest.raises(SdaBenchmarkError, match="measure every protocol metric"):
        evaluate_g9(p, baseline, candidate)

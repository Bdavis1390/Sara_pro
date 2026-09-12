from __future__ import annotations

import json
from pathlib import Path

import pytest

from worldshepherd_sara.decision_program import (
    DecisionEpoch,
    DecisionSpec,
    PackageState,
    evaluate_decision,
    refresh_decision_program,
)

ROOT = Path(__file__).resolve().parents[1]


def _fixture() -> dict:
    return json.loads((ROOT / "fixtures" / "army_decision_program_demo_v1.json").read_text())


def _spec_and_epochs() -> tuple[DecisionSpec, list[DecisionEpoch], dict]:
    fixture = _fixture()
    spec = DecisionSpec.model_validate(fixture["spec"])
    epochs = [DecisionEpoch.model_validate(item) for item in fixture["epochs"]]
    return spec, epochs, fixture["expected"]


def test_point_trade_study_is_deterministic_and_never_auto_signs():
    spec, epochs, expected = _spec_and_epochs()
    first = evaluate_decision(spec, epochs[0])
    repeated = evaluate_decision(spec, epochs[0])

    assert first.package_hash == repeated.package_hash
    assert first.recommended_option_id == expected["epoch_1_recommendation"]
    assert first.package_state == PackageState.READY_FOR_HUMAN_REVIEW
    assert first.human_signoff is False
    assert all(step.state.value == "PROPOSED" for step in first.agentic_plan)
    assert all(step.authority_required == "identified-human-authority" for step in first.agentic_plan)


def test_longitudinal_refresh_preserves_prior_package_and_changes_recommendation():
    spec, epochs, expected = _spec_and_epochs()
    history = refresh_decision_program(spec, epochs)

    assert len(history.packages) == expected["history_length"]
    assert history.packages[0].recommended_option_id == expected["epoch_1_recommendation"]
    assert history.packages[1].recommended_option_id == expected["epoch_2_recommendation"]
    assert history.packages[1].parent_package_hash == history.packages[0].package_hash
    assert history.packages[1].package_hash != history.packages[0].package_hash
    assert history.packages[0].epoch_id == "EPOCH-001"
    assert history.packages[1].epoch_id == "EPOCH-002"


def test_decision_package_exposes_what_flips_the_decision():
    spec, epochs, _ = _spec_and_epochs()
    package = evaluate_decision(spec, epochs[0])

    assert package.runner_up_option_id is not None
    assert len(package.flip_conditions) == len(spec.objectives)
    assert all(condition.normalized_shift_required >= 0 for condition in package.flip_conditions)
    assert all("aggregate-score margin" in condition.explanation for condition in package.flip_conditions)


def test_unvalidated_assumption_is_retained_as_warning_not_silently_erased():
    spec, epochs, _ = _spec_and_epochs()
    package = evaluate_decision(spec, epochs[0])

    assert "UNVALIDATED_ASSUMPTION:ASM-LEADTIME" in package.warnings
    assert package.package_state == PackageState.READY_FOR_HUMAN_REVIEW


def test_contradicted_assumption_blocks_review_ready_state():
    spec, epochs, _ = _spec_and_epochs()
    payload = spec.model_dump(mode="json")
    payload["assumptions"][1]["status"] = "CONTRADICTED"
    contradicted = DecisionSpec.model_validate(payload)

    package = evaluate_decision(contradicted, epochs[0])
    assert package.package_state == PackageState.BLOCKED
    assert "CONTRADICTED_ASSUMPTION:ASM-LEADTIME" in package.blockers
    assert package.human_signoff is False


def test_failed_bias_check_blocks_package():
    spec, epochs, _ = _spec_and_epochs()
    payload = spec.model_dump(mode="json")
    payload["bias_checks"][1]["status"] = "FAIL"
    failed = DecisionSpec.model_validate(payload)

    package = evaluate_decision(failed, epochs[0])
    assert package.package_state == PackageState.BLOCKED
    assert "BIAS_CHECK_FAILED:BIAS-SOURCE-DIVERSITY" in package.blockers


def test_unknown_or_missing_evidence_fails_closed():
    spec, epochs, _ = _spec_and_epochs()
    payload = epochs[0].model_dump(mode="json")
    payload["evidence"] = payload["evidence"][:-1]
    incomplete = DecisionEpoch.model_validate(payload)

    with pytest.raises(ValueError, match="missing evidence"):
        evaluate_decision(spec, incomplete)

    bad_payload = epochs[0].model_dump(mode="json")
    bad_payload["evidence"][0]["metric_id"] = "undeclared_metric"
    unknown = DecisionEpoch.model_validate(bad_payload)
    with pytest.raises(ValueError, match="undeclared metric"):
        evaluate_decision(spec, unknown)


def test_constraint_violation_is_explicit_and_option_is_not_ranked():
    spec, epochs, _ = _spec_and_epochs()
    payload = epochs[0].model_dump(mode="json")
    for datum in payload["evidence"]:
        if datum["option_id"] == "OPTION-A" and datum["metric_id"] == "mass_kg":
            datum["value"] = 130.0
    violated = DecisionEpoch.model_validate(payload)

    package = evaluate_decision(spec, violated)
    option_a = next(item for item in package.option_evaluations if item.option_id == "OPTION-A")
    assert option_a.feasible is False
    assert "CON-MASS" in option_a.failed_constraints
    assert package.recommended_option_id != "OPTION-A"


def test_duplicate_option_metric_evidence_is_rejected_before_evaluation():
    _, epochs, _ = _spec_and_epochs()
    payload = epochs[0].model_dump(mode="json")
    duplicate = dict(payload["evidence"][0])
    duplicate["evidence_id"] = "DUPLICATE-EVIDENCE-ID-UNIQUE"
    payload["evidence"].append(duplicate)

    with pytest.raises(ValueError, match="duplicate option/metric evidence"):
        DecisionEpoch.model_validate(payload)

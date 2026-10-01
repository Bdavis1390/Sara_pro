from worldshepherd_sara.em_latent import (
    LatentAnomalyPolicy,
    LatentAssessmentState,
    LatentModelManifest,
    LatentObservationInput,
    assess_latent_observation,
    current_d4_latent_contract,
)


def _manifest(**overrides):
    data = dict(
        model_id="uc06-latent-test",
        source_evidence="local:d4-test",
        component_count=3,
        explained_variance_fraction=0.9946,
        basis_sha256="a" * 64,
        centering_vector_sha256="b" * 64,
    )
    data.update(overrides)
    return LatentModelManifest(**data)


def _policy(**overrides):
    data = dict(
        policy_id="policy-test",
        threshold_source="prereg:test",
        reconstruction_error_threshold=0.1,
        model_context_id="uc06-latent-test",
    )
    data.update(overrides)
    return LatentAnomalyPolicy(**data)


def test_current_d4_contract_has_no_anomaly_authority() -> None:
    contract = current_d4_latent_contract()
    assert contract["diagnostic_component_count_95pct"] == 2
    assert contract["diagnostic_component_count_99pct"] == 3
    assert contract["qualified_projection_basis_available"] is False
    assert contract["anomaly_threshold_available"] is False
    assert contract["anomaly_classification_authorized"] is False


def test_coarse_d4_model_is_not_evaluable_for_anomaly_claims() -> None:
    assessment = assess_latent_observation(
        manifest=_manifest(),
        policy=_policy(),
        observation=LatentObservationInput(
            observation_id="obs-1",
            model_id="uc06-latent-test",
            reconstruction_error=999.0,
        ),
    )
    assert assessment.state == LatentAssessmentState.NOT_EVALUABLE
    assert assessment.evaluable is False
    assert assessment.anomaly_claim_authorized is False
    assert "COARSE_ENSEMBLE_ONLY" in assessment.unresolved_gates
    assert "NO_POST_HOC_ANOMALY_THRESHOLD" in assessment.rationale_codes


def test_validated_preregistered_envelope_can_be_applied() -> None:
    manifest = _manifest(
        coarse_ensemble_only=False,
        held_out_simulation_validated=True,
        hardware_repeatability_validated=True,
    )
    policy = _policy(
        threshold_preregistered_before_evaluation=True,
        physical_baseline_repeatability_validated=True,
        hardware_context_id="fixture-A",
    )
    inside = assess_latent_observation(
        manifest=manifest,
        policy=policy,
        observation=LatentObservationInput(
            observation_id="obs-2",
            model_id="uc06-latent-test",
            hardware_context_id="fixture-A",
            reconstruction_error=0.05,
        ),
    )
    outside = assess_latent_observation(
        manifest=manifest,
        policy=policy,
        observation=LatentObservationInput(
            observation_id="obs-3",
            model_id="uc06-latent-test",
            hardware_context_id="fixture-A",
            reconstruction_error=0.2,
        ),
    )
    assert inside.state == LatentAssessmentState.WITHIN_VALIDATED_ENVELOPE
    assert outside.state == LatentAssessmentState.OUTSIDE_VALIDATED_ENVELOPE
    assert inside.anomaly_claim_authorized is True
    assert outside.anomaly_claim_authorized is True


def test_hardware_context_mismatch_is_not_evaluable() -> None:
    assessment = assess_latent_observation(
        manifest=_manifest(
            coarse_ensemble_only=False,
            held_out_simulation_validated=True,
            hardware_repeatability_validated=True,
        ),
        policy=_policy(
            threshold_preregistered_before_evaluation=True,
            physical_baseline_repeatability_validated=True,
            hardware_context_id="fixture-A",
        ),
        observation=LatentObservationInput(
            observation_id="obs-4",
            model_id="uc06-latent-test",
            hardware_context_id="fixture-B",
            reconstruction_error=0.2,
        ),
    )
    assert assessment.state == LatentAssessmentState.NOT_EVALUABLE
    assert "HARDWARE_CONTEXT_MISMATCH" in assessment.unresolved_gates

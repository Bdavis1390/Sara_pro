from worldshepherd_sara.qx_evidence import EvidenceVector, QualificationEnvelope, digest
from worldshepherd_sara.semcap import SemcapMeasurements, evaluate_thresholds


def test_semcap_dimensions_bind_into_qx_without_physical_promotion():
    m = SemcapMeasurements(
        baseline_bits=1_000_000, semantic_bits=80_000,
        baseline_mission_utility=1.0, semantic_mission_utility=.98,
        latency_ms=100, power_w=2, missed_critical_events=0,
        false_semantic_selections=1, reconstruction_fidelity=.97,
        provenance_completeness=1.0,
    )
    dimensions = evaluate_thresholds(
        m, min_reduction=.90, min_utility_retention=.95,
        max_latency_ms=500, max_power_w=5,
        min_reconstruction_fidelity=.90, min_provenance_completeness=.99,
    )
    env = QualificationEnvelope(
        qualification_id="WS-SEMCAP-01", qualification_version="EVIDENCE-01",
        experiment_id="synthetic-1", run_id="synthetic-1",
        claim_state_before="SIMULATED_ONLY",
        requested_claim_state_after="INTERNAL_REPRODUCIBLE_TEST",
        software_commit="test", operator_id="test",
        authorization_record="test-only",
        test_manifest_digest=digest({"profile": "WS-SEMCAP-01"}),
        raw_evidence=[{"measurements": m.__dict__}], dimensions=dimensions,
        run_complete=True,
        evidence_vector=EvidenceVector(assurance_tevv="INTERNAL_REPRODUCIBLE_TEST"),
    )
    assert env.finalize_internal()["qualified"] is True
    assert env.claims["physical_validation"] is False
    assert env.claims["external_validation"] is False
    assert env.claims["program_qualification"] is False

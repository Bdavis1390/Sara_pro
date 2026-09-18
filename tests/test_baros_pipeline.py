import json

from baros.pipeline import run_synthetic_pipeline


def test_pipeline_is_deterministic_and_passes_bounded_gate():
    first = run_synthetic_pipeline(commit_sha="TEST-SHA")
    second = run_synthetic_pipeline(commit_sha="TEST-SHA")
    assert first == second
    assert first["passed"] is True
    assert first["claim_state"] == "SIMULATED_ONLY"
    assert first["patient_care_allowed"] is False
    assert first["result"]["tumor_survival_objective"] < first["baseline"]["tumor_survival_objective"]
    assert first["constraint_failures"] == []
    assert len(first["evidence_sha256"]) == 64


def test_evidence_is_strict_json_serializable():
    evidence = run_synthetic_pipeline(commit_sha="TEST-SHA")
    payload = json.dumps(evidence, allow_nan=False, sort_keys=True)
    assert '"passed": true' in payload
    assert '"not for patient care"' in payload

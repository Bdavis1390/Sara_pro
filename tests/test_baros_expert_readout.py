import json

from baros.expert_readout import build_expert_readout, render_expert_markdown


def test_expert_readout_is_deterministic_and_bounded():
    first = build_expert_readout(commit_sha="TEST-SHA")
    second = build_expert_readout(commit_sha="TEST-SHA")
    assert first == second
    assert first["system"]["patient_care_allowed"] is False
    assert first["system"]["partner_validation_ready"] is True
    assert first["system"]["patient_care_ready"] is False
    assert first["source_evidence"]["passed"] is True
    assert len(first["readout_sha256"]) == 64


def test_expert_readout_exposes_quantitative_state_and_constraints():
    report = build_expert_readout(commit_sha="TEST-SHA")
    optimization = report["optimization"]
    dose = report["dose_readout"]
    assert optimization["final_objective"] < optimization["baseline_objective"]
    assert optimization["hard_constraints_satisfied"] is True
    assert dose["hard_constraint_margins"]
    assert all(item["satisfied"] for item in dose["hard_constraint_margins"])
    assert report["robustness"]["all_hard_constraints_satisfied"] is True


def test_expert_readout_exposes_translational_assurance_state():
    report = build_expert_readout(commit_sha="TEST-SHA")
    assert report["governance"]["intended_use_manifest_implemented"] is True
    assert report["governance"]["current_partner_validation_manifest_locked"] is False
    assert report["model_assurance"]["local_identifiability_analysis_implemented"] is True
    assert report["model_assurance"]["clinical_model_identifiability_established"] is False
    assert report["evidence_dependency_control"]["blast_radius_invalidation_implemented"] is True
    assert report["evidence_dependency_control"]["external_partner_graph_populated"] is False
    assert len(report["risk_families"]) >= 20


def test_expert_readout_preserves_external_validation_boundary():
    report = build_expert_readout(commit_sha="TEST-SHA")
    gates = {item["gate"]: item["status"] for item in report["readiness_gates"]}
    assert gates["G5"] == "OPEN_EXTERNAL"
    assert gates["G6"] == "OPEN_EXTERNAL"
    assert gates["G7"] == "OPEN_EXTERNAL"
    assert gates["G9"] == "OPEN_EXTERNAL"
    assert report["dose_readout"]["physical_dose_accuracy_claimed"] is False
    assert report["synthetic_biology_readout"]["clinical_interpretation_permitted"] is False
    json.dumps(report, allow_nan=False, sort_keys=True)


def test_expert_markdown_contains_expert_sections():
    report = build_expert_readout(commit_sha="TEST-SHA")
    rendered = render_expert_markdown(report)
    assert "# BAROS Expert Technical Readout" in rendered
    assert "## Capability/evidence matrix" in rendered
    assert "## Validation readiness gates" in rendered
    assert "## Translational governance state" in rendered
    assert "## Model-assurance state" in rendered
    assert "## Evidence-dependency control state" in rendered
    assert "## Risk families / stop conditions" in rendered
    assert "## Partner execution package" in rendered
    assert "does not establish commissioned physical dose accuracy" in rendered

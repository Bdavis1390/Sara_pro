import json
from pathlib import Path

from worldshepherd_sara.mbse_baseline import (
    extract_legacy_model,
    meets_fixture_targets,
    score_against_ground_truth,
)


ROOT = Path(__file__).resolve().parents[1]


def _fixture(name: str) -> dict:
    return json.loads((ROOT / "fixtures" / name).read_text(encoding="utf-8"))


def test_baseline_meets_original_synthetic_fixture_targets():
    fixture = _fixture("mbse_legacy_fixture_v1.json")
    model = extract_legacy_model(fixture)
    metrics = score_against_ground_truth(model, fixture)

    assert model["ai_ml_claimed"] is False
    assert model["cameo_magicdraw_interoperability_claimed"] is False
    assert meets_fixture_targets(metrics, fixture) is True
    assert metrics["unsupported_inference_count"] == 0
    assert all(entity["source_refs"] for entity in model["entities"])
    assert all(rel["source_ref"] for rel in model["relationships"])


def test_perturbed_fixture_is_retained_as_disconfirming_evidence():
    fixture = _fixture("mbse_legacy_perturbed_v1.json")
    model = extract_legacy_model(fixture)
    metrics = score_against_ground_truth(model, fixture)

    assert fixture["scoring"]["expected_baseline_result"] == "FAIL"
    assert meets_fixture_targets(metrics, fixture) is False
    assert metrics["relationship_recall"] < fixture["scoring"]["relationship_recall_target"]
    assert metrics["missed_relationship_count"] >= 1


def test_baseline_never_claims_ai_or_cameo_interoperability():
    fixture = _fixture("mbse_legacy_fixture_v1.json")
    model = extract_legacy_model(fixture)
    assert model["generator"] == "deterministic_rules_baseline"
    assert model["ai_ml_claimed"] is False
    assert model["cameo_magicdraw_interoperability_claimed"] is False

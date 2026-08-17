from pathlib import Path
import importlib.util


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "analyze_glob_raw_coverage.py"


def load_module():
    spec = importlib.util.spec_from_file_location("glob_raw_coverage", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_three_family_union_remains_208_states():
    module = load_module()
    assert len(module.active_union()) == 208


def test_every_raw_target_belongs_to_active_union():
    module = load_module()
    report = module.build_report()
    assert report["out_of_union_targets"] == []


def test_every_active_union_state_has_explicit_raw_observation():
    module = load_module()
    report = module.build_report()
    assert report["remaining_gap_count"] == 0, (
        f"raw coverage incomplete: {report['remaining_gap_count']} states remain: "
        + ",".join(report["remaining_states"])
    )


def test_multiplicity_metrics_are_present_and_bounded():
    module = load_module()
    report = module.build_report()
    metrics = report["multiplicity"]
    assert report["schema_version"] == "ws-glob-raw-coverage-report-1.1"
    assert report["raw_record_count"] >= report["covered_unique_states"] == 208
    assert metrics["mean_records_per_covered_state"] >= 1.0
    assert metrics["median_records_per_covered_state"] >= 1
    assert metrics["max_records_for_single_state"] >= metrics["median_records_per_covered_state"]
    assert metrics["mean_namespaces_per_covered_state"] >= 1.0
    assert metrics["max_namespaces_for_single_state"] >= 1
    assert metrics["single_record_state_count"] == len(report["sparse_targets"])
    assert metrics["revised_no_hit_count"] == len(report["revised_no_hit_targets"])


def test_revised_no_hits_are_auditable_not_rewritten():
    module = load_module()
    report = module.build_report()
    for target in report["revised_no_hit_targets"]:
        row = report["per_target"][target]
        assert row["no_hit_revised_by_later_occurrence"] is True
        assert "NO_HIT" in row["weights"]
        assert len(row["weights"]) >= 2

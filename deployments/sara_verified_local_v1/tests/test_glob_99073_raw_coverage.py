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

from __future__ import annotations

import csv
import importlib.util
import io
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "convert_exoatom_transition_graph.py"


def load_module():
    spec = importlib.util.spec_from_file_location("exoatom_adapter", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_parse_exoatom_and_emit_analyzer_compatible_csv() -> None:
    module = load_module()
    states_text = """
# ID E gtot J Unc configuration term parity
1 10592.485 4 1.5 0.010 confA a4P e
2 50292.354 6 2.5 0.020 confB upperA o
3 52087.110 4 1.5 0.020 confC upperB o
"""
    trans_text = """
2 1 1.000000E+06 39699.869
3 1 2.000000E+06 41494.625
99 1 1.000000E+03 1.0
bad row
"""

    states = module.parse_states(states_text)
    transitions, summary = module.parse_transitions(trans_text, states)

    assert states == {1: 10592.485, 2: 50292.354, 3: 52087.11}
    assert len(transitions) == 2
    assert summary["transition_rows_unresolved_state_id"] == 1
    assert summary["transition_rows_malformed"] == 1

    first = transitions[0]
    assert first.lower_cm1 == 10592.485
    assert first.upper_cm1 == 50292.354
    assert abs(first.energy_difference_cm1 - 39699.869) < 1e-9
    assert abs(first.reported_minus_energy_difference_cm1) < 1e-9

    handle = io.StringIO()
    module.write_csv(transitions, handle, "W II")
    handle.seek(0)
    rows = list(csv.DictReader(handle))
    assert rows[0]["Spectrum"] == "W II"
    assert float(rows[0]["Lower Level Energy"]) == 10592.485
    assert float(rows[0]["Upper Level Energy"]) == 50292.354
    assert float(rows[0]["Reported Wavenumber"]) == 39699.869


def test_adapter_output_is_consumable_by_existing_nist_analyzer(tmp_path: Path) -> None:
    adapter = load_module()

    analyzer_path = ROOT / "scripts" / "analyze_nist_asd_transition_graph.py"
    spec = importlib.util.spec_from_file_location("nist_graph_from_exoatom", analyzer_path)
    assert spec is not None and spec.loader is not None
    analyzer = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = analyzer
    spec.loader.exec_module(analyzer)

    states = adapter.parse_states("1 10592.485\n2 50292.354\n3 52087.110\n")
    transitions, _ = adapter.parse_transitions(
        "2 1 1.0e6 39699.869\n3 1 2.0e6 41494.625\n", states
    )
    handle = io.StringIO()
    adapter.write_csv(transitions, handle, "W II")

    parsed = analyzer.parse_nist_export(handle.getvalue(), "csv")
    result = analyzer.analyze(
        parsed,
        targets=[39699, 41494],
        tolerance_cm1=1.0,
        query_levels=[10592.485],
    )

    assert result["input_summary"]["transition_rows_parsed"] == 2
    assert result["level_queries"][0]["degree"] == 2
    assert result["shared_endpoint_motifs"][0]["distinct_targets_cm-1"] == [39699.0, 41494.0]

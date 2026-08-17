from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "analyze_nist_asd_transition_graph.py"


def load_module():
    spec = importlib.util.spec_from_file_location("nist_graph", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_parse_nist_pipe_ascii_and_detect_shared_endpoint() -> None:
    module = load_module()
    sample = """
NIST Atomic Spectra Database Lines Data W II
--------------------------------------------------------------------------------
Spectrum | Transition Wavenumber | Ei           Ek | Lower level | Upper level |
         |        (cm-1)         | (cm-1)     (cm-1) |             |             |
--------------------------------------------------------------------------------
W II | 39699.84 | 10592.485 - 50292.354 | a4P 3/2 | upper-a |
W II | 41494.48 | 10592.485 - 52087.110 | a4P 3/2 | upper-b |
W II | 30979.40 | 23046.000 - 54025.400 | other | upper-c |
"""
    transitions = module.parse_nist_export(sample, "ascii")
    assert len(transitions) == 3

    result = module.analyze(
        transitions,
        targets=[39699, 41494, 30979],
        tolerance_cm1=1.0,
        query_levels=[10592.485],
    )

    assert result["input_summary"]["transition_rows_parsed"] == 3
    query = result["level_queries"][0]
    assert query["nearest_level_cm-1"] == 10592.485
    assert query["degree"] == 2

    motifs = result["shared_endpoint_motifs"]
    assert len(motifs) == 1
    assert motifs[0]["endpoint_cm-1"] == 10592.485
    assert motifs[0]["distinct_targets_cm-1"] == [39699.0, 41494.0]


def test_parse_csv_formula_cells() -> None:
    module = load_module()
    sample = (
        'Spectrum,Lower Level Energy,Upper Level Energy\n'
        'W II,"=\"10592.485\"","=\"50292.354\""\n'
        'W II,"=\"10592.485\"","=\"52087.110\""\n'
    )
    transitions = module.parse_nist_export(sample, "csv")
    assert [(item.lower_cm1, item.upper_cm1) for item in transitions] == [
        (10592.485, 50292.354),
        (10592.485, 52087.11),
    ]


def test_parse_tsv_separate_energy_columns() -> None:
    module = load_module()
    sample = (
        "Spectrum\tEi\tEk\tTerm\n"
        "W II\t10592.485\t50292.354\ta4P\n"
        "W II\t10592.485\t52087.110\ta4P\n"
    )
    transitions = module.parse_nist_export(sample, "tsv")
    assert len(transitions) == 2
    assert transitions[0].ritz_wavenumber_cm1 == 39699.869


def test_registry_targets_preserve_zero_padded_states(tmp_path: Path) -> None:
    module = load_module()
    registry = {
        "orbits": [
            {"orbit": ["99073", "09379", "30979", "93970"]},
            {"orbit": ["09736", "70639", "00005"]},
        ]
    }
    path = tmp_path / "registry.json"
    path.write_text(json.dumps(registry), encoding="utf-8")

    targets = module.load_registry_targets(path)
    assert targets == [5, 9379, 9736, 30979, 70639, 93970, 99073]


def test_analyzer_keeps_numeric_matches_claim_bounded() -> None:
    module = load_module()
    transitions = [
        module.Transition(10592.485, 50292.354, 1),
        module.Transition(10592.485, 52087.110, 2),
    ]
    result = module.analyze(
        transitions,
        targets=[39699, 41494],
        tolerance_cm1=1.0,
        query_levels=[],
    )
    boundary = result["claims_boundary"].lower()
    assert "candidate" in boundary
    assert "null model" in boundary
    assert "multiple-testing" in boundary


def test_negative_tolerance_is_rejected() -> None:
    module = load_module()
    try:
        module.analyze([], targets=[], tolerance_cm1=-0.1, query_levels=[])
    except ValueError as exc:
        assert "non-negative" in str(exc)
    else:
        raise AssertionError("negative tolerance must fail")

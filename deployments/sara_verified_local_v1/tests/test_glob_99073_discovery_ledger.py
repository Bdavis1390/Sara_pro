from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESEARCH_DIR = ROOT / "data" / "research"
REGISTRY_PATH = RESEARCH_DIR / "glob_99073_registry.json"
LEDGER_GLOB = "glob_99073_discovery_ledger_*.json"


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def ledgers() -> list[tuple[Path, dict]]:
    paths = sorted(RESEARCH_DIR.glob(LEDGER_GLOB))
    assert paths, "at least one Glob 99073 discovery ledger must exist"
    return [(path, load_json(path)) for path in paths]


def test_all_discovery_ledgers_point_to_canonical_registry() -> None:
    for path, ledger in ledgers():
        assert ledger["schema_version"] == "ws-glob-discovery-ledger-1.0", path.name
        assert ledger["parent_registry"] == REGISTRY_PATH.name, path.name


def test_every_discovered_source_has_a_worldshepherd_use_and_global_unique_id() -> None:
    registry = load_json(REGISTRY_PATH)
    allowed_routes = set(registry["worldshepherd_routing"])
    canonical_ids = {source["source_id"] for source in registry["sources"]}
    source_ids = set(canonical_ids)

    for path, ledger in ledgers():
        for source in ledger["sources"]:
            source_id = source["source_id"]
            assert source_id not in source_ids, f"duplicate source_id {source_id} in {path.name}"
            source_ids.add(source_id)

            uses = source.get("use", [])
            assert uses, f"unrouted source {source_id} in {path.name}"
            assert set(uses) <= allowed_routes, f"invalid route for {source_id} in {path.name}"
            assert source.get("note"), f"missing utilization note for {source_id} in {path.name}"


def test_every_discovery_ledger_preserves_evidence_boundaries() -> None:
    for path, ledger in ledgers():
        policy = ledger["source_ingestion_policy"]
        assert "Worldshepherd use" in policy["rule"], path.name
        assert "not independent evidence" in policy["duplicates"], path.name
        assert "never Glob evidence" in policy["search_noise"], path.name


def test_historical_topology_calibration_is_numerically_coherent() -> None:
    first_path = RESEARCH_DIR / "glob_99073_discovery_ledger_20260816.json"
    ledger = load_json(first_path)
    topology = ledger["calibration_updates"]["wii_uniform_endpoint_topology_approximation"]

    same_even = topology["pair_probability_same_even_endpoint"]
    same_odd = topology["pair_probability_same_odd_endpoint"]
    either = topology["pair_probability_share_either_endpoint"]

    assert topology["even_levels"] == 62
    assert topology["odd_levels"] == 132
    assert 0.0 < same_odd < same_even < either < 1.0
    assert abs(same_even - (1 / 62)) < 1e-12
    assert abs(same_odd - (1 / 132)) < 1e-12
    expected_either = (1 / 62) + (1 / 132) - (1 / (62 * 132))
    assert abs(either - expected_either) < 1e-12


def test_current_nist_reconciliation_separates_historical_and_current_graphs() -> None:
    path = RESEARCH_DIR / "glob_99073_discovery_ledger_20260816_02.json"
    ledger = load_json(path)
    reconciliation = ledger["current_authority_reconciliation"]
    historical = reconciliation["historical_dataset"]
    current = reconciliation["current_asd"]
    relation = reconciliation["shared_level_relation"]

    assert historical["levels"] == historical["even_levels"] + historical["odd_levels"] == 194
    assert current["physical_wii_levels"] == current["even_levels"] + current["odd_levels"] == 263
    assert current["asd_output_entries"] == 264
    assert current["terminal_non_wii_entry"] == "W III ionization limit"
    assert current["classified_lines_with_level_designations"] == 2838

    topology = current["uniform_endpoint_approximation"]
    assert abs(topology["pair_probability_same_even_endpoint"] - (1 / 76)) < 1e-12
    assert abs(topology["pair_probability_same_odd_endpoint"] - (1 / 187)) < 1e-12
    expected_either = (1 / 76) + (1 / 187) - (1 / (76 * 187))
    assert abs(topology["pair_probability_share_either_endpoint"] - expected_either) < 1e-12

    assert abs((relation["upper_1_cm-1"] - relation["lower_level_cm-1"]) - relation["ritz_1_cm-1"]) < 1e-9
    assert abs((relation["upper_2_cm-1"] - relation["lower_level_cm-1"]) - relation["ritz_2_cm-1"]) < 1e-9
    assert abs((relation["ritz_2_cm-1"] - relation["ritz_1_cm-1"]) - relation["ritz_separation_cm-1"]) < 1e-9
    assert relation["status"] == "current_authority_relational_confirmation"


def test_all_ledgers_keep_statistical_or_verification_next_actions() -> None:
    for path, ledger in ledgers():
        actions = " ".join(ledger["next_actions"]).lower()
        assert "topology" in actions, path.name
        assert "multiple-testing" in actions or "false-discovery" in actions, path.name

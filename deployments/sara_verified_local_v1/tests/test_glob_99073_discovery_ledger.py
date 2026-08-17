from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "data" / "research" / "glob_99073_registry.json"
LEDGER_PATH = ROOT / "data" / "research" / "glob_99073_discovery_ledger_20260816.json"


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def test_discovery_ledger_points_to_canonical_registry() -> None:
    ledger = load_json(LEDGER_PATH)
    assert ledger["schema_version"] == "ws-glob-discovery-ledger-1.0"
    assert ledger["parent_registry"] == REGISTRY_PATH.name


def test_every_discovered_source_has_a_worldshepherd_use() -> None:
    registry = load_json(REGISTRY_PATH)
    ledger = load_json(LEDGER_PATH)
    allowed_routes = set(registry["worldshepherd_routing"])

    source_ids: set[str] = set()
    for source in ledger["sources"]:
        source_id = source["source_id"]
        assert source_id not in source_ids, source_id
        source_ids.add(source_id)

        uses = source.get("use", [])
        assert uses, source_id
        assert set(uses) <= allowed_routes, source_id
        assert source.get("note"), source_id


def test_discovery_policy_preserves_evidence_boundaries() -> None:
    ledger = load_json(LEDGER_PATH)
    policy = ledger["source_ingestion_policy"]
    assert "Worldshepherd use" in policy["rule"]
    assert "not independent evidence" in policy["duplicates"]
    assert "never Glob evidence" in policy["search_noise"]


def test_topology_calibration_is_numerically_coherent() -> None:
    ledger = load_json(LEDGER_PATH)
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


def test_next_actions_preserve_statistical_controls() -> None:
    ledger = load_json(LEDGER_PATH)
    actions = " ".join(ledger["next_actions"]).lower()
    assert "topology-preserving" in actions
    assert "multiple-testing" in actions
    assert "reconcile" in actions
    assert "re-verify" in actions

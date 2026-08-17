from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "data" / "research" / "glob_99073_registry.json"
PERMUTATION = (2, 0, 4, 3, 1)  # 12345 -> 31542
VALID_EVIDENCE_CLASSES = {"P2", "P1", "G1", "M1", "N0"}


def load_registry() -> dict:
    with REGISTRY_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def permute(value: str) -> str:
    assert len(value) == 5
    return "".join(value[index] for index in PERMUTATION)


def test_glob_registry_is_parseable_and_versioned() -> None:
    registry = load_registry()
    assert registry["schema_version"] == "ws-glob-evidence-1.0"
    assert registry["transform"]["mapping"] == "12345->31542"


def test_every_orbit_obeys_locked_permutation() -> None:
    registry = load_registry()
    for record in registry["orbits"]:
        orbit = record["orbit"]
        assert orbit, record
        assert all(len(state) == 5 and state.isdigit() for state in orbit), record
        for current, expected_next in zip(orbit, orbit[1:] + orbit[:1]):
            assert permute(current) == expected_next, record


def test_every_source_has_a_worldshepherd_use() -> None:
    registry = load_registry()
    allowed_routes = set(registry["worldshepherd_routing"])
    for source in registry["sources"]:
        uses = source.get("use", [])
        assert uses, source["source_id"]
        assert set(uses) <= allowed_routes, source["source_id"]


def test_evidence_records_are_routed_and_referentially_sound() -> None:
    registry = load_registry()
    source_ids = {source["source_id"] for source in registry["sources"]}
    allowed_routes = set(registry["worldshepherd_routing"])
    generated_states = {
        state
        for orbit_record in registry["orbits"]
        for state in orbit_record["orbit"]
    }

    for record in registry["evidence_records"]:
        assert record["evidence_class"] in VALID_EVIDENCE_CLASSES, record["record_id"]
        uses = record.get("worldshepherd_uses", [])
        assert uses, record["record_id"]
        assert set(uses) <= allowed_routes, record["record_id"]

        source_id = record.get("source_id")
        if source_id is not None:
            assert source_id in source_ids, record["record_id"]

        derived_state = record.get("derived_state")
        if derived_state is not None:
            assert derived_state in generated_states, record["record_id"]

        if record["evidence_class"] in {"P1", "P2"}:
            assert record.get("claims_boundary"), record["record_id"]
            if "observed_value" in record:
                assert record.get("units"), record["record_id"]


def test_metadata_and_incidental_collisions_never_gain_physical_weight() -> None:
    registry = load_registry()
    for record in registry["evidence_records"]:
        if record["evidence_class"] in {"M1", "N0"}:
            boundary = record.get("claims_boundary", "").lower()
            assert "evidence" in boundary or "support" in boundary or "collision" in boundary


def test_9675_is_not_silently_zero_padded() -> None:
    registry = load_registry()
    note = registry["active_unexpanded_seed_note"]
    assert note["seed"] == "9675"
    assert note["status"] == "exact_4_digit_seed_preserved"
    assert "09675" in note["rule"]

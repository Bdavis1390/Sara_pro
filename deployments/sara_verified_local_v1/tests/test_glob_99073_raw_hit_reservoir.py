import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / "data" / "research"
PATTERN = "glob_99073_raw_hit_reservoir_*.json"
ALLOWED_WEIGHTS = {
    "M1_RAW",
    "N0_RAW",
    "NO_HIT",
    "P1_THEORY",
    "P1_COMPILED",
    "P1_CARRY_FORWARD",
}
NONPHYSICAL_WEIGHTS = {"M1_RAW", "N0_RAW", "NO_HIT"}


def reservoirs():
    paths = sorted(RESEARCH.glob(PATTERN))
    assert paths, "no Glob raw-hit reservoirs found"
    return [(path, json.loads(path.read_text())) for path in paths]


def test_raw_reservoir_series_is_append_only_and_scoped():
    items = reservoirs()
    first_path, first = items[0]
    assert first_path.name.endswith("_01.json")
    assert first["search_scope"]["current_union_unique_states"] == 208
    assert "zero automatic physical-evidence weight" in first["policy"]["rule"]
    assert "P1/P2" in first["policy"]["promotion"]

    for index, (path, data) in enumerate(items, start=1):
        assert data["schema_version"] == "ws-glob-raw-hit-reservoir-1.0", path.name
        assert data["inquiry"] == "Glob 99073", path.name
        assert data["records"], path.name
        if index > 1:
            expected_parent = items[index - 2][0].name
            assert data["parent_raw_reservoir"] == expected_parent, path.name


def test_every_raw_record_is_auditable_and_routed():
    for path, data in reservoirs():
        for record in data["records"]:
            assert len(record["target"]) == 5, path.name
            assert record["target"].isdigit(), path.name
            assert record["glob_weight"] in ALLOWED_WEIGHTS, (path.name, record)
            assert record["worldshepherd_use"], (path.name, record)
            assert record["raw_hit_type"], (path.name, record)


def test_identifier_and_no_hit_records_cannot_masquerade_as_physical_hits():
    nonphysical = []
    for path, data in reservoirs():
        for record in data["records"]:
            if record["glob_weight"] in NONPHYSICAL_WEIGHTS:
                nonphysical.append((path, record))
                assert not record["glob_weight"].startswith("P1_"), (path.name, record)
    assert nonphysical


def test_physical_raw_records_remain_explicitly_subtyped():
    physical = {}
    for _, data in reservoirs():
        for record in data["records"]:
            if record["glob_weight"].startswith("P1_"):
                physical.setdefault(record["target"], set()).add(record["glob_weight"])

    assert "P1_THEORY" in physical["77596"]
    assert "P1_COMPILED" in physical["44049"]
    assert "P1_CARRY_FORWARD" in physical["60397"]


def test_append_files_preserve_raw_vs_evidence_boundary_language():
    for path, data in reservoirs():
        policy_text = " ".join(str(value) for value in data.get("policy", {}).values()).lower()
        assert "raw" in policy_text or "occurrence" in policy_text, path.name
        assert "physical" in policy_text or "p1/p2" in policy_text, path.name

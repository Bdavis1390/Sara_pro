import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESERVOIR = ROOT / "data" / "research" / "glob_99073_raw_hit_reservoir_20260816_01.json"


def load():
    return json.loads(RESERVOIR.read_text())


def test_raw_reservoir_is_separate_from_evidence_promotion():
    data = load()
    assert data["search_scope"]["current_union_unique_states"] == 208
    assert "zero automatic physical-evidence weight" in data["policy"]["rule"]
    assert "P1/P2" in data["policy"]["promotion"]


def test_every_raw_record_is_auditable_and_routed():
    data = load()
    allowed = {"M1_RAW", "N0_RAW", "NO_HIT", "P1_THEORY", "P1_COMPILED"}
    for record in data["records"]:
        assert len(record["target"]) == 5
        assert record["target"].isdigit()
        assert record["glob_weight"] in allowed
        assert record["worldshepherd_use"]


def test_identifier_and_no_hit_records_cannot_masquerade_as_physical_hits():
    data = load()
    nonphysical = [r for r in data["records"] if r["glob_weight"] in {"M1_RAW", "N0_RAW", "NO_HIT"}]
    assert nonphysical
    assert all(not r["glob_weight"].startswith("P1_") for r in nonphysical)


def test_known_physical_records_remain_explicitly_subtyped():
    data = load()
    physical = {r["target"]: r["glob_weight"] for r in data["records"] if r["glob_weight"].startswith("P1_")}
    assert physical["77596"] == "P1_THEORY"
    assert physical["44049"] == "P1_COMPILED"

import json
from pathlib import Path


RESEARCH = Path(__file__).resolve().parents[1] / "data" / "research"
FAMILY_PATH = RESEARCH / "glob_99073_permutation_13524_registry.json"
PRIMARY_PATH = RESEARCH / "glob_99073_registry.json"
ORDER = [1, 3, 5, 2, 4]


def apply_13524(value: str) -> str:
    assert len(value) == 5
    return "".join(value[index - 1] for index in ORDER)


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_generic_13524_permutation_has_period_four() -> None:
    value = "12345"
    orbit = []
    while value not in orbit:
        orbit.append(value)
        value = apply_13524(value)
    assert orbit == ["12345", "13524", "15432", "14253"]
    assert value == "12345"


def test_every_recorded_13524_orbit_is_deterministic_and_closed() -> None:
    family = load(FAMILY_PATH)
    assert family["permutation"]["mapping"] == "12345->13524"
    assert family["permutation"]["index_order_1_based"] == ORDER
    for record in family["orbits"]:
        orbit = record["orbit"]
        assert orbit[0] == record["window"]
        for current, expected_next in zip(orbit, orbit[1:]):
            assert apply_13524(current) == expected_next
        assert apply_13524(orbit[-1]) == orbit[0]


def test_family_summary_and_seed_boundaries_are_preserved() -> None:
    family = load(FAMILY_PATH)
    assert len(family["orbits"]) == 29
    states = {state for record in family["orbits"] for state in record["orbit"]}
    assert len(states) == 113
    assert family["summary"]["unique_states"] == 113
    assert family["summary"]["overlap_with_31542_unique_states"] == 35
    assert family["summary"]["new_unique_states_vs_31542"] == 78
    seed_policy = family["seed_policy"]
    assert seed_policy["exact_4_digit_seed"] == "9675"
    assert seed_policy["derived_zero_padded_normalization"]["input"] == "09675"
    assert seed_policy["derived_zero_padded_normalization"]["orbit"] == [
        "09675", "06597", "05769", "07956"
    ]


def test_parallel_family_does_not_replace_primary_31542_transform() -> None:
    primary = load(PRIMARY_PATH)
    family = load(FAMILY_PATH)
    assert primary["transform"]["mapping"] == "12345->31542"
    assert family["permutation"]["mapping"] == "12345->13524"
    assert family["permutation"]["relationship_to_existing"] == (
        "ADDITIONAL_PARALLEL_FAMILY_DO_NOT_REPLACE_12345_TO_31542"
    )


def test_core_and_first_cross_seed_orbits_are_locked() -> None:
    family = load(FAMILY_PATH)
    by_key = {
        (record["seed"], record["window_index_0"]): record["orbit"]
        for record in family["orbits"]
    }
    assert by_key[("99073", 0)] == ["99073", "90397", "93709", "97930"]
    assert by_key[("8679305", 1)] == ["67930", "69073", "60397", "63709"]

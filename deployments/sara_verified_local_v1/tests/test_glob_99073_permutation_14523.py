import json
from pathlib import Path


RESEARCH = Path(__file__).resolve().parents[1] / "data" / "research"
FAMILY_PATH = RESEARCH / "glob_99073_permutation_14523_registry.json"
PRIMARY_PATH = RESEARCH / "glob_99073_registry.json"
SECONDARY_PATH = RESEARCH / "glob_99073_permutation_13524_registry.json"
ORDER = [1, 4, 5, 2, 3]


def apply_14523(value: str) -> str:
    assert len(value) == 5
    return "".join(value[index - 1] for index in ORDER)


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def states(payload: dict) -> set[str]:
    return {state for record in payload["orbits"] for state in record["orbit"]}


def test_generic_14523_permutation_is_an_involution() -> None:
    value = "12345"
    first = apply_14523(value)
    second = apply_14523(first)
    assert first == "14523"
    assert second == value


def test_every_recorded_14523_orbit_is_deterministic_and_closed() -> None:
    family = load(FAMILY_PATH)
    assert family["permutation"]["mapping"] == "12345->14523"
    assert family["permutation"]["index_order_1_based"] == ORDER
    assert family["permutation"]["period_generic_positions"] == 2
    for record in family["orbits"]:
        orbit = record["orbit"]
        assert orbit[0] == record["window"]
        for current, expected_next in zip(orbit, orbit[1:]):
            assert apply_14523(current) == expected_next
        assert apply_14523(orbit[-1]) == orbit[0]


def test_family_summary_and_three_family_union_are_recomputed() -> None:
    family = load(FAMILY_PATH)
    primary = load(PRIMARY_PATH)
    secondary = load(SECONDARY_PATH)

    family_states = states(family)
    prior_union = states(primary) | states(secondary)
    new_states = family_states - prior_union
    overlap = family_states & prior_union
    three_family_union = prior_union | family_states

    assert len(family["orbits"]) == 29
    assert len(family_states) == family["summary"]["unique_states"] == 57
    assert len(prior_union) == family["summary"]["existing_two_family_union_unique_states"] == 190
    assert len(overlap) == family["summary"]["overlap_with_existing_two_family_union"] == 39
    assert len(new_states) == family["summary"]["new_unique_states_vs_existing_two_family_union"] == 18
    assert len(three_family_union) == family["summary"]["three_family_union_unique_states"] == 208
    assert sorted(new_states) == family["summary"]["new_states"]
    assert sorted(overlap) == family["summary"]["overlap_states"]


def test_exact_9675_remains_separate_from_derived_zero_padding() -> None:
    family = load(FAMILY_PATH)
    seed_policy = family["seed_policy"]
    assert seed_policy["exact_4_digit_seed"] == "9675"
    assert seed_policy["derived_zero_padded_normalization"]["input"] == "09675"
    assert seed_policy["derived_zero_padded_normalization"]["orbit"] == ["09675", "07596"]
    assert "Do not silently conflate" in seed_policy["exact_4_digit_rule"]


def test_parallel_family_does_not_replace_prior_transforms() -> None:
    primary = load(PRIMARY_PATH)
    secondary = load(SECONDARY_PATH)
    family = load(FAMILY_PATH)
    assert primary["transform"]["mapping"] == "12345->31542"
    assert secondary["permutation"]["mapping"] == "12345->13524"
    assert family["permutation"]["mapping"] == "12345->14523"
    relationship = family["permutation"]["relationship_to_existing"]
    assert "DO_NOT_REPLACE_12345_TO_31542" in relationship
    assert "12345_TO_13524" in relationship


def test_key_14523_orbits_are_locked() -> None:
    family = load(FAMILY_PATH)
    by_key = {
        (record["seed"], record["window_index_0"]): record["orbit"]
        for record in family["orbits"]
    }
    assert by_key[("99073", 0)] == ["99073", "97390"]
    assert by_key[("8679305", 1)] == ["67930", "63079"]
    assert by_key[("245779675000031449401", 15)] == ["44940", "44049"]

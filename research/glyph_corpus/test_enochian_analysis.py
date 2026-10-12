from enochian_analysis import (
    anti_diagonal,
    boustrophedon,
    column_major,
    main_diagonal,
    normalized_hamming,
    row_major,
    shannon_entropy,
    symbol_profile,
    symmetry_scores,
)


def test_basic_traversals():
    grid = [["A", "B"], ["C", "D"]]
    assert row_major(grid) == ["A", "B", "C", "D"]
    assert column_major(grid) == ["A", "C", "B", "D"]
    assert boustrophedon(grid) == ["A", "B", "D", "C"]
    assert main_diagonal(grid) == ["A", "D"]
    assert anti_diagonal(grid) == ["B", "C"]


def test_entropy_and_profile():
    assert shannon_entropy(["A", "A", "A"]) == 0.0
    profile = symbol_profile([["A", "B"], ["A", "B"]])
    assert profile["rows"] == 2
    assert profile["cols"] == 2
    assert profile["cells"] == 4
    assert profile["unique_symbols"] == 2
    assert profile["entropy_bits_per_symbol"] == 1.0


def test_hamming():
    assert normalized_hamming(["A", "B"], ["A", "B"]) == 0.0
    assert normalized_hamming(["A", "B"], ["B", "A"]) == 1.0


def test_symmetry_scores_are_bounded():
    scores = symmetry_scores([["A", "B"], ["C", "D"]])
    assert all(0.0 <= v <= 1.0 for v in scores.values())

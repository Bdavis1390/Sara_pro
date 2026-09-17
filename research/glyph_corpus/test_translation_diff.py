from translation_diff import blind_status, token_vector, validate_difference_classes


def test_blind_status():
    assert blind_status(False) == "BLIND"
    assert blind_status(True) == "RETROSPECTIVE_CALIBRATION"


def test_token_vector_is_not_scalar_accuracy():
    v = token_vector(
        "I reign over you says God justice",
        "I reign over you says the God of justice",
    )
    assert v.shared_tokens >= 7
    assert "the" in v.comparison_only
    assert "of" in v.comparison_only


def test_known_difference_classes():
    validate_difference_classes([
        "segmentation_variant",
        "poetic_editorial_expansion",
        "possible_copying_error",
    ])

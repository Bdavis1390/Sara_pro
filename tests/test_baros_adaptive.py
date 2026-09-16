import numpy as np
import pytest

from baros.adaptive import DoseGridGeometry, accumulate_aligned_dose


def geometry(*, frame="1.2.3", origin=(0.0, 0.0, 0.0), spacing=(2.5, 2.5, 2.5)):
    return DoseGridGeometry(
        frame_of_reference_uid=frame,
        shape=(2, 2, 2),
        origin_mm=origin,
        spacing_mm=spacing,
        direction=(1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0),
    )


def test_aligned_dose_grids_accumulate_exactly():
    first = np.ones((2, 2, 2), dtype=float)
    second = np.full((2, 2, 2), 2.5, dtype=float)
    result = accumulate_aligned_dose([first, second], [geometry(), geometry()])
    assert np.allclose(result, 3.5)


def test_frame_mismatch_fails_closed():
    with pytest.raises(ValueError, match="not aligned"):
        accumulate_aligned_dose(
            [np.ones((2, 2, 2)), np.ones((2, 2, 2))],
            [geometry(frame="1.2.3"), geometry(frame="1.2.4")],
        )


def test_origin_mismatch_fails_closed():
    with pytest.raises(ValueError, match="not aligned"):
        accumulate_aligned_dose(
            [np.ones((2, 2, 2)), np.ones((2, 2, 2))],
            [geometry(), geometry(origin=(0.1, 0.0, 0.0))],
        )


def test_array_shape_or_negative_dose_fails_closed():
    with pytest.raises(ValueError, match="array shape"):
        accumulate_aligned_dose([np.ones((2, 2))], [geometry()])
    invalid = np.ones((2, 2, 2))
    invalid[0, 0, 0] = -1.0
    with pytest.raises(ValueError, match="non-negative"):
        accumulate_aligned_dose([invalid], [geometry()])


def test_geometry_validation_rejects_invalid_spacing():
    with pytest.raises(ValueError, match="spacing"):
        geometry(spacing=(2.5, 0.0, 2.5)).validate()

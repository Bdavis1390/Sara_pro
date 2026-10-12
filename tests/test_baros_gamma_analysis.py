import numpy as np
import pytest

from baros.gamma_analysis import gamma_compare


def test_identical_1d_dose_has_100_percent_gamma_pass_rate():
    axis = np.linspace(-20.0, 20.0, 41)
    dose = 2.0 * np.exp(-((axis / 8.0) ** 2))
    result = gamma_compare(
        axes_reference_mm=(axis,),
        dose_reference=dose,
        axes_evaluation_mm=(axis,),
        dose_evaluation=dose.copy(),
        dose_percent_threshold=3.0,
        distance_mm_threshold=2.0,
        lower_percent_dose_cutoff=10.0,
    )
    assert result.valid_points > 0
    assert result.passing_points == result.valid_points
    assert result.pass_rate_percent == pytest.approx(100.0)
    assert result.max_finite_gamma == pytest.approx(0.0, abs=1e-12)


def test_clear_global_dose_error_is_detected_under_strict_criterion():
    axis = np.linspace(-20.0, 20.0, 41)
    reference = 2.0 * np.exp(-((axis / 8.0) ** 2))
    evaluation = reference * 0.90
    result = gamma_compare(
        axes_reference_mm=(axis,),
        dose_reference=reference,
        axes_evaluation_mm=(axis,),
        dose_evaluation=evaluation,
        dose_percent_threshold=1.0,
        distance_mm_threshold=0.1,
        lower_percent_dose_cutoff=10.0,
        max_gamma=20.0,
    )
    assert result.valid_points > 0
    assert result.pass_rate_percent < 100.0
    assert result.max_finite_gamma > 1.0


def test_gamma_input_validation_fails_closed():
    with pytest.raises(ValueError):
        gamma_compare(
            axes_reference_mm=([0.0, 1.0],),
            dose_reference=[1.0, 2.0],
            axes_evaluation_mm=([0.0],),
            dose_evaluation=[1.0, 2.0],
        )

    with pytest.raises(ValueError):
        gamma_compare(
            axes_reference_mm=([1.0, 0.0],),
            dose_reference=[1.0, 2.0],
            axes_evaluation_mm=([0.0, 1.0],),
            dose_evaluation=[1.0, 2.0],
        )

    with pytest.raises(ValueError):
        gamma_compare(
            axes_reference_mm=([0.0, 1.0],),
            dose_reference=[0.0, 0.0],
            axes_evaluation_mm=([0.0, 1.0],),
            dose_evaluation=[0.0, 0.0],
        )

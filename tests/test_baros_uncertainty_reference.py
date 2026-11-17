"""Numerical entropy/MI definitions; synthetic probabilities only.

Not an actual clinical model, MR segmentation, FMISO assay, or reproduction
of van Lente et al.'s performance. Do not claim independent validation.
"""

from math import log
import pytest

from baros.uncertainty_reference import (
    as_locked_comparator_risk,
    measure_stochastic_uncertainty,
)


def test_opposite_confident_predictive_samples_maximize_binary_mutual_information():
    r = measure_stochastic_uncertainty(((1.0, 0.0), (0.0, 1.0)))
    assert r.passes == 2
    assert r.classes == 2
    assert r.mean_probabilities == pytest.approx((0.5, 0.5))
    assert r.predictive_entropy == pytest.approx(log(2))
    assert r.expected_entropy == pytest.approx(0)
    assert r.mutual_information == pytest.approx(log(2))
    assert r.mutual_information_normalized == pytest.approx(1)
    assert r.predictive_entropy_normalized == pytest.approx(1)


def test_identical_uniform_predictions_are_uncertain_but_not_epistemically_diverse():
    r = measure_stochastic_uncertainty(((0.5, 0.5),) * 50)
    assert r.predictive_entropy == pytest.approx(log(2))
    assert r.expected_entropy == pytest.approx(log(2))
    assert r.mutual_information == pytest.approx(0, abs=1e-12)
    assert r.mutual_information_normalized == pytest.approx(0, abs=1e-12)


def test_identical_confident_passes_have_zero_mutual_information():
    r = measure_stochastic_uncertainty(((0.9, 0.1),) * 50)
    expected_h = -(0.9 * log(0.9) + 0.1 * log(0.1))
    assert r.predictive_entropy == pytest.approx(expected_h)
    assert r.mutual_information == pytest.approx(0, abs=1e-12)


def test_identical_deterministic_passes_have_zero_entropies():
    r = measure_stochastic_uncertainty(((1.0, 0.0),) * 5)
    assert r.predictive_entropy == 0.0
    assert r.expected_entropy == 0.0
    assert r.mutual_information == 0.0


def test_three_class_maximum_uses_log_number_of_classes_not_binary_assumption():
    r = measure_stochastic_uncertainty(
        ((1., 0., 0.), (0., 1., 0.), (0., 0., 1.))
    )
    assert r.classes == 3
    assert r.predictive_entropy == pytest.approx(log(3))
    assert r.mutual_information == pytest.approx(log(3))
    assert r.predictive_entropy_normalized == pytest.approx(1)
    assert r.mutual_information_normalized == pytest.approx(1)


def test_metric_choice_produces_distinct_locked_risk_scores_when_appropriate():
    r = measure_stochastic_uncertainty(((0.5, 0.5),) * 4)
    pe = as_locked_comparator_risk("SYN-1", r, metric="predictive_entropy")
    mi = as_locked_comparator_risk("SYN-1", r, metric="mutual_information")
    assert pe.risk == pytest.approx(1)
    assert mi.risk == pytest.approx(0, abs=1e-12)
    assert pe.case_id == "SYN-1"
    with pytest.raises(ValueError, match="metric"):
        as_locked_comparator_risk("SYN-1", r, metric="variance")
    with pytest.raises(ValueError, match="case_id"):
        as_locked_comparator_risk("", r, metric="predictive_entropy")


@pytest.mark.parametrize("rows", [
    (),
    ((0.5, 0.5),),
    ((1., 0.), (1., 0., 0.)),
    ((1.2, -0.2), (1.0, 0.0)),
    ((float("nan"), 0.0), (1.0, 0.0)),
    ((float("inf"), 0.0), (1.0, 0.0)),
    ((True, False), (True, False)),
    (("0.5", "0.5"), (0.5, 0.5)),
    ((0.3, 0.3), (0.3, 0.3)),
    ((1.0,), (1.0,)),
])
def test_invalid_probabilities_or_shapes_rejected(rows):
    with pytest.raises(ValueError):
        measure_stochastic_uncertainty(rows)


@pytest.mark.parametrize("tolerance", [0.0, -1.0, "0.1", True, float("nan"), 1e-2])
def test_nonconforming_probability_sum_tolerance_rejected(tolerance):
    with pytest.raises(ValueError, match="sum_tolerance"):
        measure_stochastic_uncertainty(
            ((0.5, 0.5), (0.5, 0.5)), sum_tolerance=tolerance
        )


def test_small_numerical_rounding_is_allowed_but_not_used_for_clinical_calibration():
    r = measure_stochastic_uncertainty(((0.1, 0.9), (0.9, 0.1)))
    assert 0.0 <= r.mutual_information_normalized <= 1.0
    assert r.mutual_information_normalized > 0.0

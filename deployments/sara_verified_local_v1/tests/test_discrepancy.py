from __future__ import annotations

import pytest

from worldshepherd_sara.discrepancy import PairedMeasurement, compare_prediction_to_measurement


def test_discrepancy_summary_preserves_absolute_relative_and_uncertainty_metrics():
    summary = compare_prediction_to_measurement([
        PairedMeasurement(key="gain", predicted=10.5, measured=10.0, uncertainty=0.6, units="dB"),
        PairedMeasurement(key="phase", predicted=31.0, measured=30.0, uncertainty=0.5, units="deg"),
    ])
    assert summary.mean_absolute_error == 0.75
    assert summary.max_absolute_error == 1.0
    assert summary.mean_relative_error is not None
    assert summary.within_uncertainty_fraction == 0.5
    assert summary.metrics[0].normalized_error is not None


def test_zero_measurement_has_no_relative_error_and_zero_uncertainty_is_handled_explicitly():
    summary = compare_prediction_to_measurement([
        PairedMeasurement(key="zero", predicted=0.0, measured=0.0, uncertainty=0.0)
    ])
    assert summary.metrics[0].relative_error is None
    assert summary.metrics[0].normalized_error == 0.0
    assert summary.within_uncertainty_fraction == 1.0


def test_discrepancy_rejects_invalid_uncertainty():
    with pytest.raises(ValueError):
        compare_prediction_to_measurement([
            PairedMeasurement(key="bad", predicted=1.0, measured=1.0, uncertainty=-1.0)
        ])

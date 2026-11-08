import numpy as np
import pytest

from baros.dvh import cumulative_dvh, dose_to_hottest_percent, summarize_dose, volume_at_least


def test_dvh_summary_known_values_and_volume():
    dose = np.array([0.0, 10.0, 20.0, 30.0])
    summary = summarize_dose(dose, voxel_volume_cc=0.5)
    assert summary.voxel_count == 4
    assert summary.total_volume_cc == pytest.approx(2.0)
    assert summary.dmin_gy == pytest.approx(0.0)
    assert summary.dmean_gy == pytest.approx(15.0)
    assert summary.dmedian_gy == pytest.approx(15.0)
    assert summary.dmax_gy == pytest.approx(30.0)


def test_vx_percent_and_cc_follow_at_least_semantics():
    dose = np.array([0.0, 10.0, 20.0, 30.0])
    assert volume_at_least(dose, 20.0) == pytest.approx(50.0)
    assert volume_at_least(dose, 20.0, voxel_volume_cc=0.25, output="cc") == pytest.approx(0.5)
    assert volume_at_least(dose, 30.0) == pytest.approx(25.0)
    assert volume_at_least(dose, 31.0) == pytest.approx(0.0)


def test_dx_nearest_rank_is_explicit_and_deterministic():
    dose = np.array([0.0, 10.0, 20.0, 30.0])
    assert dose_to_hottest_percent(dose, 25.0) == pytest.approx(30.0)
    assert dose_to_hottest_percent(dose, 50.0) == pytest.approx(20.0)
    assert dose_to_hottest_percent(dose, 95.0) == pytest.approx(0.0)
    assert dose_to_hottest_percent(dose, 100.0) == pytest.approx(0.0)


def test_mask_limits_metrics_to_selected_structure():
    dose = np.array([[1.0, 2.0], [10.0, 20.0]])
    mask = np.array([[False, False], [True, True]])
    summary = summarize_dose(dose, mask=mask)
    assert summary.dmean_gy == pytest.approx(15.0)
    assert volume_at_least(dose, 15.0, mask=mask) == pytest.approx(50.0)
    assert dose_to_hottest_percent(dose, 50.0, mask=mask) == pytest.approx(20.0)


def test_empirical_cumulative_dvh_is_monotonic():
    dose = np.array([0.0, 10.0, 10.0, 30.0])
    points, volume = cumulative_dvh(dose)
    assert points.tolist() == pytest.approx([0.0, 10.0, 30.0])
    assert volume.tolist() == pytest.approx([100.0, 75.0, 25.0])
    assert np.all(np.diff(points) > 0)
    assert np.all(np.diff(volume) <= 0)


def test_invalid_dvh_inputs_fail_closed():
    with pytest.raises(ValueError):
        summarize_dose([])
    with pytest.raises(ValueError):
        summarize_dose([1.0, float("nan")])
    with pytest.raises(ValueError):
        summarize_dose([-1.0, 2.0])
    with pytest.raises(ValueError):
        summarize_dose(np.ones((2, 2)), mask=np.ones((3, 3), dtype=bool))
    with pytest.raises(ValueError):
        volume_at_least([1.0], -1.0)
    with pytest.raises(ValueError):
        volume_at_least([1.0], 1.0, output="cc")
    with pytest.raises(ValueError):
        dose_to_hottest_percent([1.0], 0.0)

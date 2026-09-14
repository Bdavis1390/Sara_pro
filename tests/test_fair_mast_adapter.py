import pytest

from worldshepherd_sara.fair_mast_adapter import (
    FairMastQualityPolicy,
    FairMastReadOnlyMetadataClient,
    FairMastSource,
    series_to_sensor_samples,
)


def test_level1_source_builds_stable_zarr_provenance():
    source = FairMastSource(
        shot_id=30420,
        diagnostic_group="amc",
        signal="plasma_current",
        level="level1",
    )
    assert source.zarr_uri == "s3://mast/level1/shots/30420.zarr/amc"
    assert source.diagnostic_name == "amc/plasma_current"
    provenance = source.provenance_for_index(7)
    assert "https://s3.echo.stfc.ac.uk" in provenance
    assert "s3://mast/level1/shots/30420.zarr/amc" in provenance
    assert "signal=plasma_current" in provenance
    assert "index=7" in provenance


def test_metadata_client_is_get_only_and_host_allowlisted():
    client = FairMastReadOnlyMetadataClient()
    assert client.shot_url(30420) == "https://mastapp.site/json/shots/30420"

    with pytest.raises(ValueError, match="host not allowlisted"):
        FairMastReadOnlyMetadataClient("https://example.com/json")

    with pytest.raises(ValueError, match="must use https"):
        FairMastReadOnlyMetadataClient("http://mastapp.site/json")


def test_series_conversion_attaches_provenance_and_level_quality():
    source = FairMastSource(30420, "amc", "plasma_current", "level1")
    samples = series_to_sensor_samples(
        source,
        timestamps=[0.0, 0.001, 0.002],
        values=[0.0, 100.0, 200.0],
        unit="A",
        uncertainty=0.5,
        quality="curated",
    )
    assert len(samples) == 3
    assert all(sample.shot_id == "30420" for sample in samples)
    assert all(sample.diagnostic == "amc/plasma_current" for sample in samples)
    assert all("fair-mast-level1" in sample.quality for sample in samples)
    assert samples[2].provenance.endswith("|index=2|level=level1")


def test_nonfinite_archive_value_is_retained_as_invalid_not_control_valid():
    source = FairMastSource(30420, "amc", "plasma_current", "level1")
    samples = series_to_sensor_samples(
        source,
        timestamps=[0.0, 0.001],
        values=[100.0, float("nan")],
        unit="A",
        uncertainty=0.5,
    )
    assert samples[0].valid is True
    assert samples[1].valid is False


def test_level2_magnetics_are_blocked_for_derivative_sensitive_analysis():
    source = FairMastSource(
        29980,
        "magnetics",
        "b_field_pol_probe_cc_field",
        "level2",
    )
    ok, reason = FairMastQualityPolicy.evaluate(source, derivative_sensitive=True)
    assert ok is False
    assert reason == "level2_magnetics_derivative_quality_risk"

    with pytest.raises(ValueError, match="level2_magnetics_derivative_quality_risk"):
        series_to_sensor_samples(
            source,
            timestamps=[0.0, 0.001],
            values=[0.1, 0.2],
            unit="T",
            uncertainty=1e-6,
            derivative_sensitive=True,
        )


def test_level2_magnetics_remain_available_for_non_derivative_replay_with_provenance():
    source = FairMastSource(
        29980,
        "magnetics",
        "b_field_pol_probe_cc_field",
        "level2",
    )
    samples = series_to_sensor_samples(
        source,
        timestamps=[0.0],
        values=[0.1],
        unit="T",
        uncertainty=1e-6,
        derivative_sensitive=False,
    )
    assert len(samples) == 1
    assert samples[0].valid is True
    assert "level=level2" in samples[0].provenance


def test_timestamp_regression_is_rejected():
    source = FairMastSource(30420, "amc", "plasma_current", "level1")
    with pytest.raises(ValueError, match="timestamp_not_monotonic"):
        series_to_sensor_samples(
            source,
            timestamps=[0.002, 0.001],
            values=[100.0, 101.0],
            unit="A",
            uncertainty=0.5,
        )

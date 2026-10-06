from __future__ import annotations

import pandas as pd

from climateguard.data.coverage import generate_source_coverage_report
from climateguard.data.temporal_alignment import align_datasets, analyze_temporal_overlap, detect_date_range, detect_duplicate_dates, detect_missing_dates, generate_alignment_report
from climateguard.features.catalog import generate_feature_catalog
from climateguard.features.hydro_meteorological import add_hydrological_rolling_features, add_meteorological_rolling_features, prepare_future_alignment_feature_layer


def _meteorology_fixture() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.date_range("2020-01-01", periods=5, freq="D"),
            "rainfall": [0.0, 2.0, 1.5, 5.0, 0.5],
            "temperature": [20.0, 21.0, 22.5, 23.0, 24.0],
            "humidity": [50.0, 52.0, 61.0, 58.0, 60.0],
            "wind_speed": [1.2, 1.8, 1.4, 2.1, 1.7],
            "pressure": [101.2, 101.1, 100.8, 101.0, 100.9],
        }
    )


def _hydrology_fixture() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.date_range("2020-01-03", periods=5, freq="D"),
            "water_level_mMSL": [3.00, 3.10, 3.20, 3.18, 3.25],
        }
    )


def test_exact_date_alignment() -> None:
    nasa = _meteorology_fixture()
    match = nasa.copy()
    result = align_datasets(nasa, match, left_name="NASA", right_name="MATCH", join_type="exact")
    assert result["overlap_exists"] is True
    assert not result["joined"].empty
    assert result["joined"]["date"].nunique() == len(result["joined"])


def test_non_overlapping_datasets() -> None:
    left = pd.DataFrame({"date": pd.date_range("2020-01-01", periods=3, freq="D"), "value": [1, 2, 3]})
    right = pd.DataFrame({"date": pd.date_range("2021-01-01", periods=3, freq="D"), "value": [4, 5, 6]})
    overlap = analyze_temporal_overlap(left, right, left_name="A", right_name="B")
    assert overlap["overlap_exists"] is False
    assert overlap["overlapping_observation_count"] == 0


def test_overlapping_datasets() -> None:
    left = pd.DataFrame({"date": pd.date_range("2020-01-01", periods=5, freq="D"), "value": [1, 2, 3, 4, 5]})
    right = pd.DataFrame({"date": pd.date_range("2020-01-03", periods=5, freq="D"), "value": [10, 11, 12, 13, 14]})
    overlap = analyze_temporal_overlap(left, right, left_name="A", right_name="B")
    assert overlap["overlap_exists"] is True
    assert overlap["overlapping_observation_count"] == 3


def test_duplicate_date_detection() -> None:
    df = pd.DataFrame({"date": ["2020-01-01", "2020-01-01", "2020-01-02"], "value": [1, 2, 3]})
    duplicates = detect_duplicate_dates(df)
    assert duplicates == ["2020-01-01"]


def test_missing_date_detection() -> None:
    df = pd.DataFrame({"date": ["2020-01-01", "2020-01-03"], "value": [1, 3]})
    missing = detect_missing_dates(df)
    assert "2020-01-02" in missing


def test_date_range_detection() -> None:
    df = pd.DataFrame({"date": ["2020-01-01", "2020-01-03"], "value": [1, 3]})
    date_range = detect_date_range(df)
    assert date_range == {"earliest": "2020-01-01", "latest": "2020-01-03"}


def test_source_coverage_calculation() -> None:
    nasa = _meteorology_fixture()
    bwdb = _hydrology_fixture()
    coverage = generate_source_coverage_report({"NASA": nasa, "BWDB": bwdb})
    assert len(coverage) == 2
    assert coverage[0]["source_name"] in {"NASA", "BWDB"}
    assert coverage[0]["observation_count"] > 0


def test_hydrological_rolling_features() -> None:
    df = pd.DataFrame({"date": pd.date_range("2020-01-01", periods=4, freq="D"), "water_level_mMSL": [3.0, 3.1, 3.2, 3.5]})
    features = add_hydrological_rolling_features(df)
    assert "river_level_change_1d" in features.columns
    assert "river_level_rolling_mean_3d" in features.columns
    assert "river_level_rolling_max_7d" in features.columns


def test_meteorological_rolling_features() -> None:
    df = _meteorology_fixture()
    features = add_meteorological_rolling_features(df)
    assert "rainfall_3d_total" in features.columns
    assert "temperature_7d_mean" in features.columns
    assert "pressure_3d_change" in features.columns


def test_no_synthetic_data_creation() -> None:
    meteorology = _meteorology_fixture()
    hydrology = pd.DataFrame({"date": pd.date_range("2025-01-01", periods=3, freq="D"), "water_level_mMSL": [1.0, 1.1, 1.2]})
    result = prepare_future_alignment_feature_layer(meteorology, hydrology)
    assert result["overlap_exists"] is False
    assert result["aligned_dataset"] is None
    assert result["status"] == "NO_TEMPORAL_OVERLAP"


def test_no_temporal_extrapolation() -> None:
    meteorology = pd.DataFrame({"date": ["2020-01-01", "2020-01-02"], "rainfall": [1.0, 2.0]})
    hydrology = pd.DataFrame({"date": ["2020-02-01", "2020-02-02"], "water_level_mMSL": [3.0, 3.1]})
    result = prepare_future_alignment_feature_layer(meteorology, hydrology)
    assert result["overlap_exists"] is False
    assert result["aligned_dataset"] is None


def test_feature_metadata_generation() -> None:
    catalog = generate_feature_catalog()
    names = {item["feature_name"] for item in catalog}
    assert "rainfall_1d" in names
    assert "river_level" in names
    assert any(item["feature_type"] == "hydrological" for item in catalog)


def test_alignment_report_generation() -> None:
    nasa = pd.DataFrame({"date": pd.date_range("2015-01-01", periods=3, freq="D"), "rainfall": [1, 2, 3]})
    bwdb = pd.DataFrame({"date": pd.date_range("2026-08-01", periods=3, freq="D"), "water_level_mMSL": [3.0, 3.1, 3.2]})
    report = generate_alignment_report(nasa, bwdb)
    assert report["overlap_exists"] is False
    assert report["overlapping_observation_count"] == 0
    assert "NOT_CREATED" in report["combined_ml_training_dataset"]

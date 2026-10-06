from __future__ import annotations

import pandas as pd

from climateguard.data.hydrological_integration import (
    REQUIRED_COLUMNS,
    build_canonical_hydrological_dataset,
    generate_ground_truth_status,
    generate_integration_readiness_report,
    load_cleaned_bwdb_dataset,
    validate_dates,
    validate_numeric_water_levels,
    validate_schema,
    validate_station_date_uniqueness,
    validate_station_metadata,
)


def test_dataset_loads_successfully() -> None:
    df = load_cleaned_bwdb_dataset()
    assert len(df) == 31
    assert not df.empty


def test_required_columns_exist() -> None:
    df = load_cleaned_bwdb_dataset()
    schema = validate_schema(df)
    assert schema["schema_valid"] is True
    assert set(REQUIRED_COLUMNS).issubset(df.columns)


def test_station_id_is_sw42() -> None:
    df = load_cleaned_bwdb_dataset()
    assert df["station_id"].nunique() == 1
    assert df["station_id"].iloc[0] == "SW42"


def test_station_metadata_is_consistent() -> None:
    df = load_cleaned_bwdb_dataset()
    metadata = validate_station_metadata(df)
    assert metadata["metadata_valid"] is True
    assert metadata["station_ids"] == ["SW42"]


def test_dates_parse_correctly() -> None:
    df = load_cleaned_bwdb_dataset()
    date_report = validate_dates(df)
    assert date_report["invalid_date_count"] == 0
    assert date_report["earliest"] == "2026-08-01"
    assert date_report["latest"] == "2026-08-31"


def test_dates_are_chronologically_ordered() -> None:
    df = load_cleaned_bwdb_dataset()
    parsed = pd.to_datetime(df["date"], errors="coerce")
    assert parsed.is_monotonic_increasing


def test_station_date_pairs_are_unique() -> None:
    df = load_cleaned_bwdb_dataset()
    duplicates = validate_station_date_uniqueness(df)
    assert duplicates["station_date_pairs_unique"] is True
    assert duplicates["duplicate_station_date_pairs"] == 0


def test_water_levels_are_numeric() -> None:
    df = load_cleaned_bwdb_dataset()
    numeric = validate_numeric_water_levels(df)
    assert numeric["missing_count"] == 0
    assert numeric["invalid_numeric_count"] == 0
    assert numeric["non_finite_count"] == 0
    assert numeric["minimum"] > 0


def test_no_synthetic_observations_are_introduced() -> None:
    df = load_cleaned_bwdb_dataset()
    assert len(df) == 31
    assert df["date"].nunique() == 31
    assert df["station_id"].nunique() == 1


def test_ground_truth_status_correctly_reports_labels_unavailable() -> None:
    df = load_cleaned_bwdb_dataset()
    status = generate_ground_truth_status(df)
    assert status["status"] == "OBSERVED_HYDROLOGY_AVAILABLE_BUT_OFFICIAL_FLOOD_LABELS_UNAVAILABLE"
    assert status["hydrological_observations"]["available"] is True
    assert status["official_flood_labels"]["available"] is False
    assert status["official_flood_threshold"]["available"] is False


def test_canonical_dataset_has_required_schema() -> None:
    canonical = build_canonical_hydrological_dataset()
    assert list(canonical.columns) == REQUIRED_COLUMNS
    assert canonical["date"].is_monotonic_increasing
    assert canonical["station_id"].nunique() == 1


def test_integration_readiness_report_is_generated() -> None:
    df = load_cleaned_bwdb_dataset()
    readiness = generate_integration_readiness_report(df)
    assert readiness["integration_readiness"] == "READY_FOR_TEMPORAL_INTEGRATION"
    assert readiness["schema_validation"]["schema_valid"] is True
    assert readiness["station_validation"]["metadata_valid"] is True

from pathlib import Path

import pandas as pd
import pytest

from climateguard.data.canonical import CANONICAL_COLUMNS, build_canonical_dataset
from climateguard.data.sources import load_bmd_data, load_bwdb_data, load_era5_data, load_nasa_power_data
from climateguard.data.validation import generate_data_quality_report


def test_bmd_loader_builds_canonical_dataset(tmp_path: Path) -> None:
    path = tmp_path / "bmd_sample.csv"
    pd.DataFrame(
        {
            "date": ["2024-01-01", "2024-01-02"],
            "rainfall": [10.0, 20.0],
            "temperature": [25.0, 27.0],
        }
    ).to_csv(path, index=False)

    result = load_bmd_data(path)

    assert "date" in result.columns
    assert "rainfall" in result.columns
    assert "source" in result.columns
    assert "processing_version" in result.columns
    assert result["date"].notna().all()


def test_bwdb_loader_requires_hydrology_columns(tmp_path: Path) -> None:
    path = tmp_path / "bwdb_sample.csv"
    pd.DataFrame({"date": ["2024-01-01"], "river_name": ["Jamuna"]}).to_csv(path, index=False)

    with pytest.raises(ValueError):
        load_bwdb_data(path)


def test_nasa_power_loader_maps_coordinates_and_metadata(tmp_path: Path) -> None:
    path = tmp_path / "power_sample.csv"
    pd.DataFrame(
        {
            "date": ["2024-01-01"],
            "lat": [24.0],
            "lon": [89.0],
            "rainfall": [15.0],
            "temperature": [26.0],
        }
    ).to_csv(path, index=False)

    result = load_nasa_power_data(path)

    assert "latitude" in result.columns
    assert "longitude" in result.columns
    assert "source_dataset" in result.columns


def test_era5_loader_handles_reanalysis_data(tmp_path: Path) -> None:
    path = tmp_path / "era5_sample.csv"
    pd.DataFrame(
        {
            "date": ["2024-01-01"],
            "latitude": [24.0],
            "longitude": [89.0],
            "temperature": [26.5],
        }
    ).to_csv(path, index=False)

    result = load_era5_data(path)

    assert "temperature" in result.columns
    assert "source" in result.columns


def test_build_canonical_dataset_contains_expected_schema() -> None:
    df = pd.DataFrame({"date": ["2024-01-01"], "rainfall": [12.0], "latitude": [24.0], "longitude": [89.0]})

    canonical = build_canonical_dataset(df, source="test-source", source_dataset="fixture")

    missing = [column for column in CANONICAL_COLUMNS if column not in canonical.columns]
    assert not missing
    assert canonical["year"].iloc[0] == 2024
    assert canonical["season"].iloc[0] in {"winter", "pre_monsoon", "monsoon", "post_monsoon"}


def test_data_quality_report_exports_summary() -> None:
    df = pd.DataFrame(
        {
            "date": ["2024-01-01", "2024-01-02", "2024-01-02"],
            "rainfall": [10.0, None, 20.0],
            "latitude": [22.0, 25.0, 90.2],
            "longitude": [89.0, 92.0, 179.0],
        }
    )

    report = generate_data_quality_report(df, date_column="date", latitude_column="latitude", longitude_column="longitude")

    assert report["duplicate_rows"] == 0
    assert report["missing_values"]["rainfall"] == 1
    assert report["coordinate_validation"]["invalid_latitude"] >= 1

from __future__ import annotations

import math
from pathlib import Path

import pandas as pd
import pytest

from climateguard.data.bwdb_hydrology import (
    STATION_META,
    build_clean_bwdb_dataset,
    generate_bwdb_provenance,
    parse_bwdb_water_level_html,
    validate_bwdb_hydrology_dataset,
)


RAW_HTML_PATH = Path("data/raw/phase5_5_hydrological_dataset/bwdb_water_level_SW42_last_30d_raw.html")


def test_parse_bwdb_html_returns_observations() -> None:
    html = RAW_HTML_PATH.read_text(encoding="utf-8", errors="replace")
    records = parse_bwdb_water_level_html(html)

    assert len(records) == 31
    assert all("date" in record for record in records)
    assert all("water_level_mMSL" in record for record in records)


def test_dates_are_normalized_and_values_numeric() -> None:
    html = RAW_HTML_PATH.read_text(encoding="utf-8", errors="replace")
    records = parse_bwdb_water_level_html(html)

    first = records[0]
    last = records[-1]
    assert first["date"] == "2026-08-01"
    assert last["date"] == "2026-08-31"
    assert isinstance(first["water_level_mMSL"], float)
    assert math.isfinite(first["water_level_mMSL"])


def test_duplicate_date_detection_works() -> None:
    df = pd.DataFrame(
        {
            "date": ["2026-08-01", "2026-08-01", "2026-08-03"],
            "station_id": ["SW42", "SW42", "SW42"],
            "station_name": ["Dhaka_Mill Barrack", "Dhaka_Mill Barrack", "Dhaka_Mill Barrack"],
            "river": ["Buriganga", "Buriganga", "Buriganga"],
            "district": ["Dhaka", "Dhaka", "Dhaka"],
            "water_level_mMSL": [3.1, 3.1, 3.2],
        }
    )

    report = validate_bwdb_hydrology_dataset(df)
    assert report["duplicate_dates_count"] == 1


def test_missing_dates_detection_works() -> None:
    df = pd.DataFrame(
        {
            "date": ["2026-08-01", "2026-08-03"],
            "station_id": ["SW42", "SW42"],
            "station_name": ["Dhaka_Mill Barrack", "Dhaka_Mill Barrack"],
            "river": ["Buriganga", "Buriganga"],
            "district": ["Dhaka", "Dhaka"],
            "water_level_mMSL": [3.1, 3.3],
        }
    )

    report = validate_bwdb_hydrology_dataset(df)
    assert report["missing_dates_count"] == 1


def test_invalid_numeric_values_are_detected() -> None:
    df = pd.DataFrame(
        {
            "date": ["2026-08-01", "2026-08-02"],
            "station_id": ["SW42", "SW42"],
            "station_name": ["Dhaka_Mill Barrack", "Dhaka_Mill Barrack"],
            "river": ["Buriganga", "Buriganga"],
            "district": ["Dhaka", "Dhaka"],
            "water_level_mMSL": [float("nan"), 3.2],
        }
    )

    report = validate_bwdb_hydrology_dataset(df)
    assert report["invalid_numeric_count"] == 1


def test_build_clean_dataset_output_contains_required_columns() -> None:
    df = build_clean_bwdb_dataset(RAW_HTML_PATH)

    assert list(df.columns) == [
        "date",
        "water_level_mMSL",
        "station_id",
        "station_name",
        "river",
        "district",
    ]
    assert df["station_id"].nunique() == 1
    assert df["station_name"].nunique() == 1


def test_clean_output_is_chronologically_sorted() -> None:
    df = build_clean_bwdb_dataset(RAW_HTML_PATH)
  
    assert df["date"].is_monotonic_increasing
    assert df["date"].iloc[0].strftime("%Y-%m-%d") == "2026-08-01"
    assert df["date"].iloc[-1].strftime("%Y-%m-%d") == "2026-08-31"


def test_provenance_metadata_fields_are_preserved() -> None:
    provenance = generate_bwdb_provenance(
        raw_input_path=RAW_HTML_PATH,
        cleaned_output_path=Path("data/processed/bwdb_water_level_SW42_clean.csv"),
        retrieval_datetime="2026-10-06T00:45:21Z",
    )

    assert provenance["source_organization"] == STATION_META["organization"]
    assert provenance["station_id"] == STATION_META["station_id"]
    assert provenance["raw_source_preserved"] is True


def test_raw_html_parses_expected_station_metadata() -> None:
    html = RAW_HTML_PATH.read_text(encoding="utf-8", errors="replace")
    records = parse_bwdb_water_level_html(html)

    assert records[0]["station_id"] == "SW42"
    assert records[0]["station_name"] == "Dhaka_Mill Barrack"
    assert records[0]["river"] == "Buriganga"
    assert records[0]["district"] == "Dhaka"


def test_build_clean_dataset_uses_actual_row_count() -> None:
    df = build_clean_bwdb_dataset(RAW_HTML_PATH)

    assert len(df) == 31
    assert df["water_level_mMSL"].notna().all()

from __future__ import annotations

from typing import Any

import pandas as pd


def validate_required_columns(df: pd.DataFrame, required_columns: list[str]) -> list[str]:
    """Return missing required columns.

    This is a validation utility for data ingestion and schema checks.
    """
    missing = [column for column in required_columns if column not in df.columns]
    return missing


def detect_missing_values(df: pd.DataFrame) -> dict[str, int]:
    """Return missing value counts per column."""
    return {column: int(value) for column, value in df.isna().sum().items()}


def detect_duplicate_rows(df: pd.DataFrame) -> int:
    """Return the number of duplicate rows in the DataFrame."""
    return int(df.duplicated().sum())


def validate_date_column(df: pd.DataFrame, date_column: str) -> dict[str, Any]:
    """Validate a date column and report invalid rows.

    The function does not silently remove invalid values; it reports them.
    """
    if date_column not in df.columns:
        raise KeyError(f"Date column not found: {date_column}")

    parsed = pd.to_datetime(df[date_column], errors="coerce")
    invalid_count = int(parsed.isna().sum())
    return {
        "column": date_column,
        "invalid_records": invalid_count,
        "valid_records": int((~parsed.isna()).sum()),
        "min_date": parsed.min().isoformat() if parsed.notna().any() else None,
        "max_date": parsed.max().isoformat() if parsed.notna().any() else None,
    }


def validate_coordinate_columns(
    df: pd.DataFrame,
    latitude_column: str = "latitude",
    longitude_column: str = "longitude",
) -> dict[str, Any]:
    """Validate latitude and longitude ranges without altering the data."""
    errors: list[str] = []
    report: dict[str, Any] = {
        "latitude_column": latitude_column,
        "longitude_column": longitude_column,
        "invalid_latitude": 0,
        "invalid_longitude": 0,
        "out_of_range_rows": 0,
    }

    if latitude_column not in df.columns:
        errors.append(f"Latitude column missing: {latitude_column}")
    if longitude_column not in df.columns:
        errors.append(f"Longitude column missing: {longitude_column}")

    if errors:
        report["errors"] = errors
        return report

    lat = pd.to_numeric(df[latitude_column], errors="coerce")
    lon = pd.to_numeric(df[longitude_column], errors="coerce")

    invalid_latitude = int(((lat < -90) | (lat > 90) | lat.isna()).sum())
    invalid_longitude = int(((lon < -180) | (lon > 180) | lon.isna()).sum())
    report["invalid_latitude"] = invalid_latitude
    report["invalid_longitude"] = invalid_longitude
    report["out_of_range_rows"] = int(
        (((lat < -90) | (lat > 90) | lon.isna()) | ((lon < -180) | (lon > 180) | lat.isna())).sum()
    )
    return report


def generate_data_quality_report(
    df: pd.DataFrame,
    *,
    required_columns: list[str] | None = None,
    date_column: str | None = "date",
    latitude_column: str = "latitude",
    longitude_column: str = "longitude",
) -> dict[str, Any]:
    """Create a structured, exportable data quality summary.

    The function returns a dictionary suitable for JSON export and includes
    suspicious values without deleting them.
    """
    report: dict[str, Any] = {
        "rows": int(len(df)),
        "columns": int(len(df.columns)),
        "missing_values": detect_missing_values(df),
        "duplicate_rows": detect_duplicate_rows(df),
        "column_names": list(df.columns),
        "numeric_summary": df.describe(include="number").to_dict() if not df.empty else {},
    }

    if required_columns:
        report["missing_required_columns"] = validate_required_columns(df, required_columns)

    if date_column and date_column in df.columns:
        report["date_validation"] = validate_date_column(df, date_column)

    report["coordinate_validation"] = validate_coordinate_columns(
        df,
        latitude_column=latitude_column,
        longitude_column=longitude_column,
    )

    return report


def export_data_quality_report(report: dict[str, Any], output_path: str | Any) -> str:
    """Export a data quality report as JSON to a file path."""
    import json

    target = str(output_path)
    with open(target, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, default=str)
    return target

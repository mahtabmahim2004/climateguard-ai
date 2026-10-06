from __future__ import annotations

from typing import Any

import pandas as pd

from .temporal_alignment import detect_date_range, detect_duplicate_dates, detect_missing_dates, validate_date_column


def compute_date_frequency(df: pd.DataFrame, date_column: str = "date") -> str:
    """Report the observed daily cadence or the dominant gap in days."""
    normalized = validate_date_column(df, date_column=date_column)
    if normalized.empty:
        return "unknown"

    ordered = normalized[date_column].sort_values().dt.normalize()
    diffs = ordered.diff().dropna().dt.days
    if diffs.empty:
        return "1D"

    mode = diffs.mode()
    if mode.empty:
        return "1D"
    return f"{int(mode.iloc[0])}D" if int(mode.iloc[0]) > 0 else "1D"


def summarize_source_coverage(
    df: pd.DataFrame,
    *,
    source_name: str,
    location: str | None = None,
    station: str | None = None,
    date_column: str = "date",
    overlap_with: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Summarize the temporal coverage of a source dataset."""
    normalized = validate_date_column(df, date_column=date_column)
    if normalized.empty:
        raise ValueError(f"No valid rows found for source {source_name}.")

    date_range = detect_date_range(normalized, date_column=date_column)
    missing_dates = detect_missing_dates(normalized, date_column=date_column)
    duplicate_dates = detect_duplicate_dates(normalized, date_column=date_column)
    observation_count = len(normalized)

    summary = {
        "source_name": source_name,
        "location": location,
        "station": station,
        "date_range": date_range,
        "observation_count": observation_count,
        "missing_dates": missing_dates,
        "duplicate_dates": duplicate_dates,
        "date_frequency": compute_date_frequency(normalized, date_column=date_column),
        "temporal_coverage": {
            "earliest": date_range["earliest"],
            "latest": date_range["latest"],
            "days": (pd.Timestamp(date_range["latest"]) - pd.Timestamp(date_range["earliest"])) .days + 1,
        },
        "overlap_with_other_sources": overlap_with or {},
    }
    return summary


def generate_source_coverage_report(
    datasets: dict[str, pd.DataFrame],
    *,
    locations: dict[str, str] | None = None,
    stations: dict[str, str] | None = None,
    date_column: str = "date",
) -> list[dict[str, Any]]:
    """Compute coverage summaries for all labeled source datasets."""
    locations = locations or {}
    stations = stations or {}
    results: list[dict[str, Any]] = []

    for source_name, df in datasets.items():
        overlap = {}
        for other_name, other_df in datasets.items():
            if other_name == source_name:
                continue
            other_dates = validate_date_column(other_df, date_column=date_column)[date_column]
            source_dates = validate_date_column(df, date_column=date_column)[date_column]
            if source_dates.empty or other_dates.empty:
                overlap[other_name] = {"overlap_exists": False, "overlapping_observation_count": 0}
                continue
            overlap_start = max(source_dates.min().normalize(), other_dates.min().normalize())
            overlap_end = min(source_dates.max().normalize(), other_dates.max().normalize())
            overlap_exists = overlap_start <= overlap_end
            overlap[other_name] = {
                "overlap_exists": overlap_exists,
                "overlap_range": {
                    "earliest": overlap_start.strftime("%Y-%m-%d") if overlap_exists else None,
                    "latest": overlap_end.strftime("%Y-%m-%d") if overlap_exists else None,
                },
                "overlapping_observation_count": len(pd.date_range(start=overlap_start, end=overlap_end, freq="D")) if overlap_exists else 0,
            }

        results.append(
            summarize_source_coverage(
                df,
                source_name=source_name,
                location=locations.get(source_name),
                station=stations.get(source_name),
                date_column=date_column,
                overlap_with=overlap,
            )
        )

    return results


__all__ = ["compute_date_frequency", "summarize_source_coverage", "generate_source_coverage_report"]

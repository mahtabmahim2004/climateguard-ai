from __future__ import annotations

from typing import Any

import pandas as pd


def validate_date_column(df: pd.DataFrame, date_column: str = "date") -> pd.DataFrame:
    """Return a date-normalized copy of the dataframe."""
    if date_column not in df.columns:
        raise KeyError(f"Date column '{date_column}' not found in dataframe.")

    cleaned = df.copy()
    cleaned[date_column] = pd.to_datetime(cleaned[date_column], errors="coerce")
    cleaned = cleaned.dropna(subset=[date_column]).sort_values(date_column).reset_index(drop=True)
    return cleaned


def detect_duplicate_dates(df: pd.DataFrame, date_column: str = "date") -> list[str]:
    """Detect repeated dates without creating synthetic values."""
    normalized = validate_date_column(df, date_column=date_column)
    duplicate_dates = normalized[date_column][normalized[date_column].duplicated(keep=False)]
    return sorted(duplicate_dates.dt.strftime("%Y-%m-%d").unique().tolist())


def detect_missing_dates(df: pd.DataFrame, date_column: str = "date") -> list[str]:
    """Return missing dates between the minimum and maximum dates in the data."""
    normalized = validate_date_column(df, date_column=date_column)
    if normalized.empty:
        return []

    min_date = normalized[date_column].min().normalize()
    max_date = normalized[date_column].max().normalize()
    expected_dates = pd.date_range(start=min_date, end=max_date, freq="D")
    observed_dates = pd.DatetimeIndex(normalized[date_column].dt.normalize().unique())
    missing = expected_dates.difference(observed_dates)
    return sorted(missing.strftime("%Y-%m-%d").tolist())


def detect_date_range(df: pd.DataFrame, date_column: str = "date") -> dict[str, str]:
    """Summarize the date bounds for a source dataset."""
    normalized = validate_date_column(df, date_column=date_column)
    if normalized.empty:
        return {"earliest": None, "latest": None}
    return {
        "earliest": normalized[date_column].min().strftime("%Y-%m-%d"),
        "latest": normalized[date_column].max().strftime("%Y-%m-%d"),
    }


def analyze_temporal_overlap(
    left_df: pd.DataFrame,
    right_df: pd.DataFrame,
    *,
    left_name: str = "left",
    right_name: str = "right",
    date_column: str = "date",
) -> dict[str, Any]:
    """Check whether two time series overlap and report the overlap period."""
    left = validate_date_column(left_df, date_column=date_column)
    right = validate_date_column(right_df, date_column=date_column)

    left_min = left[date_column].min().normalize()
    left_max = left[date_column].max().normalize()
    right_min = right[date_column].min().normalize()
    right_max = right[date_column].max().normalize()

    overlap_start = max(left_min, right_min)
    overlap_end = min(left_max, right_max)
    overlap_exists = overlap_start <= overlap_end

    overlap_dates: list[str] = []
    if overlap_exists:
        overlap_dates = pd.date_range(start=overlap_start, end=overlap_end, freq="D").strftime("%Y-%m-%d").tolist()

    return {
        "left_name": left_name,
        "right_name": right_name,
        "left_date_range": detect_date_range(left_df, date_column=date_column),
        "right_date_range": detect_date_range(right_df, date_column=date_column),
        "overlap_exists": overlap_exists,
        "overlap_range": {
            "earliest": overlap_start.strftime("%Y-%m-%d") if overlap_exists else None,
            "latest": overlap_end.strftime("%Y-%m-%d") if overlap_exists else None,
        },
        "overlapping_observation_count": len(overlap_dates) if overlap_exists else 0,
        "overlapping_dates": overlap_dates,
        "status": "TEMPORAL_OVERLAP" if overlap_exists else "NO_TEMPORAL_OVERLAP",
        "message": "TEMPORAL OVERLAP EXISTS." if overlap_exists else "NO TEMPORAL OVERLAP; a fused training dataset must not be created.",
    }


def align_datasets(
    left_df: pd.DataFrame,
    right_df: pd.DataFrame,
    *,
    left_name: str = "left",
    right_name: str = "right",
    date_column: str = "date",
    join_type: str = "left",
    left_prefix: str = "left_",
    right_prefix: str = "right_",
) -> dict[str, Any]:
    """Align two datasets by date and refuse to fabricate observations."""
    if join_type not in {"left", "inner", "exact"}:
        raise ValueError("join_type must be one of: 'left', 'inner', 'exact'")

    left = validate_date_column(left_df, date_column=date_column)
    right = validate_date_column(right_df, date_column=date_column)

    overlap = analyze_temporal_overlap(left, right, left_name=left_name, right_name=right_name, date_column=date_column)

    if join_type == "exact":
        joined = left.merge(right, on=date_column, how="inner", suffixes=(left_prefix.rstrip("_"), right_prefix.rstrip("_")))
        joined = joined.sort_values(date_column).reset_index(drop=True)
        return {
            "join_type": join_type,
            "joined": joined,
            "overlap_exists": overlap["overlap_exists"],
            "overlap_summary": overlap,
            "status": "EXACT_MATCH" if not joined.empty else "NO_MATCHING_DATES",
        }

    if join_type == "inner":
        joined = left.merge(right, on=date_column, how="inner", suffixes=(left_prefix.rstrip("_"), right_prefix.rstrip("_")))
        joined = joined.sort_values(date_column).reset_index(drop=True)
        return {
            "join_type": join_type,
            "joined": joined,
            "overlap_exists": overlap["overlap_exists"],
            "overlap_summary": overlap,
            "status": "INNER_JOIN_READY" if not joined.empty else "NO_OVERLAP",
        }

    joined = left.merge(right, on=date_column, how="left", suffixes=(left_prefix.rstrip("_"), right_prefix.rstrip("_")))
    joined = joined.sort_values(date_column).reset_index(drop=True)
    return {
        "join_type": join_type,
        "joined": joined,
        "overlap_exists": overlap["overlap_exists"],
        "overlap_summary": overlap,
        "status": "LEFT_JOIN_READY" if not joined.empty else "NO_DATA",
    }


def generate_alignment_report(
    nasa_df: pd.DataFrame,
    bwdb_df: pd.DataFrame,
    *,
    nasa_name: str = "NASA_POWER",
    bwdb_name: str = "BWDB",
) -> dict[str, Any]:
    """Create a machine-readable report describing the current temporal compatibility."""
    overlap = analyze_temporal_overlap(nasa_df, bwdb_df, left_name=nasa_name, right_name=bwdb_name, date_column="date")

    report = {
        "source_1": nasa_name,
        "source_2": bwdb_name,
        "nasa_date_range": detect_date_range(nasa_df, date_column="date"),
        "bwdb_date_range": detect_date_range(bwdb_df, date_column="date"),
        "overlap_exists": overlap["overlap_exists"],
        "overlapping_observation_count": overlap["overlapping_observation_count"],
        "combined_ml_training_dataset": "NOT_CREATED",
        "status": "NO TEMPORAL OVERLAP",
        "message": "NO FUSED TRAINING DATASET CREATED BECAUSE VERIFIED SOURCES HAVE NO TEMPORAL OVERLAP.",
        "scientific_note": "The current NASA POWER and BWDB datasets are temporally incompatible for supervised ML fusion.",
    }
    if overlap["overlap_exists"]:
        report["status"] = "TEMPORAL_OVERLAP_AVAILABLE"
        report["message"] = "Temporal overlap exists; feature alignment may proceed only for compatible, verified observations."
    return report


__all__ = [
    "validate_date_column",
    "detect_duplicate_dates",
    "detect_missing_dates",
    "detect_date_range",
    "analyze_temporal_overlap",
    "align_datasets",
    "generate_alignment_report",
]

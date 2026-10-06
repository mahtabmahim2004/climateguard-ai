from __future__ import annotations

import re

import pandas as pd


def standardize_column_name(column_name: str) -> str:
    """Convert a raw column name into a portable snake_case-like value."""
    normalized = str(column_name).strip().lower()
    normalized = re.sub(r"[^a-z0-9]+", "_", normalized)
    return normalized.strip("_")


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Standardize column names to lowercase, snake_case-style strings."""
    renamed = df.copy()
    renamed.columns = [standardize_column_name(column) for column in renamed.columns]
    return renamed


def parse_date_column(df: pd.DataFrame, date_column: str) -> pd.DataFrame:
    """Convert a column to datetime while preserving invalid values as NaT."""
    if date_column not in df.columns:
        raise KeyError(f"Date column not found: {date_column}")

    cleaned = df.copy()
    cleaned[date_column] = pd.to_datetime(cleaned[date_column], errors="coerce")
    return cleaned


def remove_exact_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """Remove exact duplicate rows and return the cleaned DataFrame."""
    return df.drop_duplicates().reset_index(drop=True)


def coerce_numeric_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Convert selected columns to numeric, preserving invalid values as NaN."""
    cleaned = df.copy()
    for column in columns:
        if column in cleaned.columns:
            cleaned[column] = pd.to_numeric(cleaned[column], errors="coerce")
    return cleaned


def sort_chronologically(df: pd.DataFrame, date_column: str = "date") -> pd.DataFrame:
    """Sort rows by date in ascending order."""
    if date_column not in df.columns:
        raise KeyError(f"Date column not found: {date_column}")

    cleaned = df.copy()
    cleaned[date_column] = pd.to_datetime(cleaned[date_column], errors="coerce")
    return cleaned.sort_values(by=date_column, kind="mergesort").reset_index(drop=True)


def clean_dataset(
    df: pd.DataFrame,
    *,
    date_column: str = "date",
    required_columns: list[str] | None = None,
    numeric_columns: list[str] | None = None,
) -> pd.DataFrame:
    """Apply a reproducible cleaning workflow to a DataFrame.

    This function performs schema normalization and validation-friendly cleaning
    without generating synthetic data or inventing target labels.
    """
    cleaned = normalize_columns(df)

    normalized_required = [standardize_column_name(column) for column in (required_columns or [])]
    normalized_numeric = [standardize_column_name(column) for column in (numeric_columns or [])]

    if required_columns:
        missing = [column for column in normalized_required if column not in cleaned.columns]
        if missing:
            raise KeyError(f"Missing required columns after cleaning: {missing}")

    normalized_date_column = standardize_column_name(date_column)

    if normalized_date_column in cleaned.columns:
        cleaned = parse_date_column(cleaned, normalized_date_column)

    cleaned = remove_exact_duplicates(cleaned)

    if numeric_columns:
        cleaned = coerce_numeric_columns(cleaned, normalized_numeric)

    if normalized_date_column in cleaned.columns:
        cleaned = sort_chronologically(cleaned, normalized_date_column)

    return cleaned

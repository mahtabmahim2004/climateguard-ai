from __future__ import annotations

from pathlib import Path

import pandas as pd

from .canonical import build_canonical_dataset, canonicalize_columns
from .cleaning import normalize_columns, parse_date_column
from .loader import load_dataset


def _require_columns(df: pd.DataFrame, required: list[str]) -> None:
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")


def _normalize_source_dataframe(df: pd.DataFrame, *, source: str, source_dataset: str, original_file: str | None = None) -> pd.DataFrame:
    normalized = normalize_columns(df)
    normalized = parse_date_column(normalized, "date") if "date" in normalized.columns else normalized
    return build_canonical_dataset(
        normalized,
        source=source,
        source_dataset=source_dataset,
        original_file=original_file,
    )


def load_bmd_data(
    file_path: str | Path,
    *,
    required_columns: list[str] | None = None,
) -> pd.DataFrame:
    """Load Bangladesh Meteorological Department data in a source-specific format."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"BMD dataset not found: {path}")

    df = load_dataset(path)
    required = required_columns or ["date", "rainfall"]
    normalized = canonicalize_columns(df)
    _require_columns(normalized, required)

    if "date" in normalized.columns:
        normalized = parse_date_column(normalized, "date")

    return _normalize_source_dataframe(
        normalized,
        source="Bangladesh Meteorological Department",
        source_dataset="BMD",
        original_file=str(path),
    )


def load_bwdb_data(
    file_path: str | Path,
    *,
    required_columns: list[str] | None = None,
) -> pd.DataFrame:
    """Load Bangladesh Water Development Board hydrological data."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"BWDB dataset not found: {path}")

    df = load_dataset(path)
    required = required_columns or ["date", "river_level"]
    normalized = canonicalize_columns(df)
    _require_columns(normalized, required)

    if "date" in normalized.columns:
        normalized = parse_date_column(normalized, "date")

    return _normalize_source_dataframe(
        normalized,
        source="Bangladesh Water Development Board",
        source_dataset="BWDB",
        original_file=str(path),
    )


def load_nasa_power_data(
    file_path: str | Path,
    *,
    required_columns: list[str] | None = None,
) -> pd.DataFrame:
    """Load NASA POWER climate data after validating required fields."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"NASA POWER dataset not found: {path}")

    df = load_dataset(path)
    required = required_columns or ["date", "latitude", "longitude", "rainfall", "temperature"]
    normalized = canonicalize_columns(df)
    _require_columns(normalized, required)

    if "date" in normalized.columns:
        normalized = parse_date_column(normalized, "date")

    return _normalize_source_dataframe(
        normalized,
        source="NASA POWER",
        source_dataset="NASA_POWER",
        original_file=str(path),
    )


def load_era5_data(
    file_path: str | Path,
    *,
    required_columns: list[str] | None = None,
) -> pd.DataFrame:
    """Load ECMWF ERA5-style reanalysis data after validating required fields."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"ERA5 dataset not found: {path}")

    df = load_dataset(path)
    required = required_columns or ["date", "latitude", "longitude", "temperature"]
    normalized = canonicalize_columns(df)
    _require_columns(normalized, required)

    if "date" in normalized.columns:
        normalized = parse_date_column(normalized, "date")

    return _normalize_source_dataframe(
        normalized,
        source="ECMWF ERA5",
        source_dataset="ERA5",
        original_file=str(path),
    )

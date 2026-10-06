from __future__ import annotations

from datetime import datetime

import pandas as pd

from .cleaning import normalize_columns

CANONICAL_COLUMNS = [
    "date",
    "year",
    "month",
    "day_of_year",
    "season",
    "latitude",
    "longitude",
    "division",
    "district",
    "upazila",
    "rainfall",
    "temperature",
    "humidity",
    "wind_speed",
    "pressure",
    "river_level",
    "river_discharge",
    "soil_moisture",
    "elevation",
    "flood_event",
    "flood_risk",
    "source",
    "source_dataset",
    "retrieval_date",
    "original_file",
    "processing_version",
]

SEASON_MAP = {
    12: "winter",
    1: "winter",
    2: "winter",
    3: "pre_monsoon",
    4: "pre_monsoon",
    5: "pre_monsoon",
    6: "monsoon",
    7: "monsoon",
    8: "monsoon",
    9: "post_monsoon",
    10: "post_monsoon",
    11: "post_monsoon",
}

COLUMN_ALIASES = {
    "date": {"date", "observation_date", "timestamp", "datetime"},
    "latitude": {"latitude", "lat", "y"},
    "longitude": {"longitude", "lon", "long", "x"},
    "rainfall": {"rainfall", "precipitation", "precip", "rain_mm"},
    "temperature": {"temperature", "temp", "air_temperature"},
    "humidity": {"humidity", "relative_humidity"},
    "wind_speed": {"wind_speed", "windspeed", "wind"},
    "pressure": {"pressure", "atmospheric_pressure", "surface_pressure"},
    "river_level": {"river_level", "water_level"},
    "river_discharge": {"river_discharge", "discharge", "stream_flow"},
    "soil_moisture": {"soil_moisture", "surface_soil_moisture"},
    "elevation": {"elevation", "altitude"},
    "division": {"division"},
    "district": {"district"},
    "upazila": {"upazila", "subdistrict"},
}


def canonicalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Map common source-specific columns to the project canonical names."""
    normalized = normalize_columns(df)
    renamed = normalized.copy()

    for canonical_name, aliases in COLUMN_ALIASES.items():
        if canonical_name in renamed.columns:
            continue
        match = next((column for column in renamed.columns if column in aliases), None)
        if match is not None:
            renamed = renamed.rename(columns={match: canonical_name})

    return renamed


def add_temporal_features(df: pd.DataFrame, date_column: str = "date") -> pd.DataFrame:
    """Add year, month, day_of_year, and season features when a valid date exists."""
    if date_column not in df.columns:
        return df

    enriched = df.copy()
    enriched[date_column] = pd.to_datetime(enriched[date_column], errors="coerce")
    enriched["year"] = enriched[date_column].dt.year
    enriched["month"] = enriched[date_column].dt.month
    enriched["day_of_year"] = enriched[date_column].dt.dayofyear
    enriched["season"] = enriched[date_column].dt.month.map(SEASON_MAP)
    return enriched


def attach_provenance(
    df: pd.DataFrame,
    *,
    source: str,
    source_dataset: str,
    original_file: str | None = None,
    retrieval_date: str | datetime | None = None,
    processing_version: str = "phase3",
) -> pd.DataFrame:
    """Attach provenance metadata without fabricating observed values."""
    enriched = df.copy()
    enriched["source"] = source
    enriched["source_dataset"] = source_dataset
    enriched["retrieval_date"] = (
        pd.Timestamp(retrieval_date).isoformat() if retrieval_date is not None else pd.Timestamp.utcnow().isoformat()
    )
    enriched["original_file"] = original_file
    enriched["processing_version"] = processing_version
    return enriched


def build_canonical_dataset(
    df: pd.DataFrame,
    *,
    source: str,
    source_dataset: str,
    original_file: str | None = None,
    retrieval_date: str | datetime | None = None,
    processing_version: str = "phase3",
) -> pd.DataFrame:
    """Create a canonical dataset with provenance metadata and temporal features.

    The function never manufactures a flood target; it simply preserves canonical
    structure and source metadata when the input dataset is valid.
    """
    canonical = canonicalize_columns(df)
    canonical = add_temporal_features(canonical)
    canonical = attach_provenance(
        canonical,
        source=source,
        source_dataset=source_dataset,
        original_file=original_file,
        retrieval_date=retrieval_date,
        processing_version=processing_version,
    )

    existing_columns = set(canonical.columns)
    for column in CANONICAL_COLUMNS:
        if column not in existing_columns:
            canonical[column] = pd.NA

    return canonical.loc[:, CANONICAL_COLUMNS]

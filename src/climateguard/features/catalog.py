from __future__ import annotations

from typing import Any

FEATURE_CATALOG: list[dict[str, Any]] = [
    {
        "feature_name": "rainfall_1d",
        "source": "NASA POWER",
        "feature_type": "meteorological",
        "physical_meaning": "Daily rainfall total for the most recent day.",
        "calculation": "Sum of rainfall observations across the previous 1 day.",
        "input_columns": ["rainfall"],
        "temporal_window": "1 day",
        "units": "mm/day",
        "currently_usable_for_ml_training": True,
        "scientific_limitations": "This is meteorological rainfall, not flood ground truth.",
    },
    {
        "feature_name": "rainfall_3d",
        "source": "NASA POWER",
        "feature_type": "meteorological",
        "physical_meaning": "Three-day cumulative rainfall.",
        "calculation": "Rolling sum of rainfall over the previous 3 days.",
        "input_columns": ["rainfall"],
        "temporal_window": "3 days",
        "units": "mm",
        "currently_usable_for_ml_training": True,
        "scientific_limitations": "Still a meteorological signal rather than flood outcome data.",
    },
    {
        "feature_name": "rainfall_7d",
        "source": "NASA POWER",
        "feature_type": "meteorological",
        "physical_meaning": "Seven-day cumulative rainfall.",
        "calculation": "Rolling sum of rainfall over the previous 7 days.",
        "input_columns": ["rainfall"],
        "temporal_window": "7 days",
        "units": "mm",
        "currently_usable_for_ml_training": True,
        "scientific_limitations": "It is not equivalent to a verified flood event label.",
    },
    {
        "feature_name": "temperature_anomaly",
        "source": "NASA POWER",
        "feature_type": "meteorological",
        "physical_meaning": "Deviation from the local climatological baseline.",
        "calculation": "Observed daily temperature minus a reference baseline when available.",
        "input_columns": ["temperature"],
        "temporal_window": "daily / climatological context",
        "units": "C",
        "currently_usable_for_ml_training": True,
        "scientific_limitations": "Requires a valid climatology reference to be scientifically meaningful.",
    },
    {
        "feature_name": "river_level",
        "source": "BWDB",
        "feature_type": "hydrological",
        "physical_meaning": "Observed river water level at the station.",
        "calculation": "Measured water level for the current date at station SW42.",
        "input_columns": ["water_level_mMSL"],
        "temporal_window": "daily",
        "units": "m above mean sea level",
        "currently_usable_for_ml_training": False,
        "scientific_limitations": "The current BWDB dataset is a single station and does not have a validated flood threshold or overlap with NASA data.",
    },
    {
        "feature_name": "river_level_change_1d",
        "source": "BWDB",
        "feature_type": "hydrological",
        "physical_meaning": "One-day change in observed water level.",
        "calculation": "Current river level minus the level from the previous day.",
        "input_columns": ["water_level_mMSL"],
        "temporal_window": "1 day",
        "units": "m",
        "currently_usable_for_ml_training": False,
        "scientific_limitations": "Derived only within the 2026 BWDB period; not a flood label and not temporally aligned with NASA data.",
    },
    {
        "feature_name": "river_level_rolling_mean_3d",
        "source": "BWDB",
        "feature_type": "hydrological",
        "physical_meaning": "Three-day rolling average river level.",
        "calculation": "Mean of water level over the previous 3 days.",
        "input_columns": ["water_level_mMSL"],
        "temporal_window": "3 days",
        "units": "m",
        "currently_usable_for_ml_training": False,
        "scientific_limitations": "Available only for the current 2026 observation window and must not be extrapolated.",
    },
    {
        "feature_name": "river_level_rolling_max_7d",
        "source": "BWDB",
        "feature_type": "hydrological",
        "physical_meaning": "Seven-day rolling maximum river level.",
        "calculation": "Maximum observed water level over the previous 7 days.",
        "input_columns": ["water_level_mMSL"],
        "temporal_window": "7 days",
        "units": "m",
        "currently_usable_for_ml_training": False,
        "scientific_limitations": "No official flood threshold is available; this is a hydrological observation summary, not a flood outcome.",
    },
]


def generate_feature_catalog() -> list[dict[str, Any]]:
    """Return a serializable catalog for all engineered feature definitions."""
    return [dict(feature) for feature in FEATURE_CATALOG]


__all__ = ["FEATURE_CATALOG", "generate_feature_catalog"]

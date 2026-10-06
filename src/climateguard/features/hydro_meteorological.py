from __future__ import annotations

import pandas as pd


def add_meteorological_rolling_features(
    df: pd.DataFrame,
    *,
    rainfall_column: str = "rainfall",
    temperature_column: str = "temperature",
    humidity_column: str = "humidity",
    wind_speed_column: str = "wind_speed",
    pressure_column: str = "pressure",
    windows: tuple[int, ...] = (1, 3, 7, 14, 30),
) -> pd.DataFrame:
    """Generate rolling meteorological features from the actual observed period only."""
    working = df.copy()

    for window in windows:
        if rainfall_column in working.columns:
            working[f"rainfall_{window}d_total"] = working[rainfall_column].rolling(window=window, min_periods=1).sum()
            working[f"rainfall_{window}d_mean"] = working[rainfall_column].rolling(window=window, min_periods=1).mean()

        if temperature_column in working.columns:
            working[f"temperature_{window}d_mean"] = working[temperature_column].rolling(window=window, min_periods=1).mean()

        if humidity_column in working.columns:
            working[f"humidity_{window}d_mean"] = working[humidity_column].rolling(window=window, min_periods=1).mean()

        if wind_speed_column in working.columns:
            working[f"wind_speed_{window}d_mean"] = working[wind_speed_column].rolling(window=window, min_periods=1).mean()

        if pressure_column in working.columns:
            working[f"pressure_{window}d_change"] = working[pressure_column].diff().rolling(window=window, min_periods=1).mean()

    return working


def add_hydrological_rolling_features(
    df: pd.DataFrame,
    *,
    water_level_column: str = "water_level_mMSL",
    windows: tuple[int, ...] = (1, 3, 7),
) -> pd.DataFrame:
    """Generate hydrological rolling features for the actual BWDB observations only."""
    working = df.copy()

    for window in windows:
        if water_level_column in working.columns:
            working[f"river_level_change_{window}d"] = working[water_level_column].diff(window)
            working[f"river_level_rolling_mean_{window}d"] = working[water_level_column].rolling(window=window, min_periods=1).mean()
            working[f"river_level_rolling_max_{window}d"] = working[water_level_column].rolling(window=window, min_periods=1).max()

    return working


def prepare_future_alignment_feature_layer(
    meteorology_df: pd.DataFrame,
    hydrology_df: pd.DataFrame,
    *,
    date_column: str = "date",
) -> dict[str, object]:
    """Return compatibility metadata and feature definitions without fabricating fused data."""
    meteorology = meteorology_df.copy()
    hydrology = hydrology_df.copy()

    meteorology[date_column] = pd.to_datetime(meteorology[date_column], errors="coerce")
    hydrology[date_column] = pd.to_datetime(hydrology[date_column], errors="coerce")

    overlap_start = max(meteorology[date_column].min(), hydrology[date_column].min())
    overlap_end = min(meteorology[date_column].max(), hydrology[date_column].max())
    overlap_exists = overlap_start <= overlap_end

    if not overlap_exists:
        return {
            "status": "NO_TEMPORAL_OVERLAP",
            "overlap_exists": False,
            "meteorology_feature_frame": meteorology,
            "hydrology_feature_frame": hydrology,
            "aligned_dataset": None,
            "message": "NO FUSED TRAINING DATASET CREATED BECAUSE VERIFIED SOURCES HAVE NO TEMPORAL OVERLAP.",
        }

    aligned = meteorology.merge(hydrology, on=date_column, how="inner", suffixes=("_meteorology", "_hydrology"))
    aligned = aligned.sort_values(date_column).reset_index(drop=True)
    meteorology_features = add_meteorological_rolling_features(aligned)
    hydrology_features = add_hydrological_rolling_features(meteorology_features)

    return {
        "status": "TEMPORAL_OVERLAP_AVAILABLE",
        "overlap_exists": True,
        "meteorology_feature_frame": meteorology,
        "hydrology_feature_frame": hydrology,
        "aligned_dataset": hydrology_features,
        "message": "Future alignment can proceed once temporal compatibility is verified.",
    }


__all__ = [
    "add_meteorological_rolling_features",
    "add_hydrological_rolling_features",
    "prepare_future_alignment_feature_layer",
]

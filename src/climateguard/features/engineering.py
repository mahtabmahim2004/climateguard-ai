from __future__ import annotations

import pandas as pd


def placeholder_feature_summary() -> dict[str, str]:
    """Placeholder function for future feature engineering work."""
    return {
        "status": "initialized",
        "module": "climateguard.features.engineering",
        "purpose": "Feature engineering foundation for flood-risk modeling",
    }


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


def add_date_features(df: pd.DataFrame, date_column: str = "date") -> pd.DataFrame:
    """Create calendar-derived time features.

    These features are based only on the observed timestamp and do not use any
    future information. They are designed for reproducible feature preparation.
    """
    if date_column not in df.columns:
        raise KeyError(f"Date column not found: {date_column}")

    cleaned = df.copy()
    cleaned[date_column] = pd.to_datetime(cleaned[date_column], errors="coerce")

    cleaned["year"] = cleaned[date_column].dt.year
    cleaned["month"] = cleaned[date_column].dt.month
    cleaned["day"] = cleaned[date_column].dt.day
    cleaned["day_of_year"] = cleaned[date_column].dt.dayofyear
    cleaned["season"] = cleaned[date_column].dt.month.map(SEASON_MAP)
    return cleaned


def add_lag_features(
    df: pd.DataFrame,
    value_column: str,
    lags: list[int] | tuple[int, ...] = (1, 3, 7),
    group_column: str | None = None,
) -> pd.DataFrame:
    """Create lagged numeric features using only prior observations.

    When a group column is supplied, lags are computed within each group.
    """
    if value_column not in df.columns:
        raise KeyError(f"Value column not found: {value_column}")

    cleaned = df.copy()
    for lag in lags:
        column_name = f"{value_column}_lag_{lag}"
        if group_column is None:
            cleaned[column_name] = cleaned[value_column].shift(lag)
        else:
            if group_column not in cleaned.columns:
                raise KeyError(f"Group column not found: {group_column}")
            cleaned[column_name] = cleaned.groupby(group_column)[value_column].transform(
                lambda series: series.shift(lag)
            )
    return cleaned


def add_rolling_statistics(
    df: pd.DataFrame,
    value_column: str,
    windows: list[int] | tuple[int, ...] = (3, 7),
    group_column: str | None = None,
) -> pd.DataFrame:
    """Create moving-window statistics such as rolling mean and rolling sum.

    These features are based on past values only and are meant for structured
    pipeline preparation, not final model training.
    """
    if value_column not in df.columns:
        raise KeyError(f"Value column not found: {value_column}")

    cleaned = df.copy()
    for window in windows:
        mean_name = f"{value_column}_rolling_mean_{window}"
        sum_name = f"{value_column}_rolling_sum_{window}"

        if group_column is None:
            cleaned[mean_name] = cleaned[value_column].rolling(window=window, min_periods=1).mean()
            cleaned[sum_name] = cleaned[value_column].rolling(window=window, min_periods=1).sum()
        else:
            if group_column not in cleaned.columns:
                raise KeyError(f"Group column not found: {group_column}")
            cleaned[mean_name] = cleaned.groupby(group_column)[value_column].transform(
                lambda series: series.rolling(window=window, min_periods=1).mean()
            )
            cleaned[sum_name] = cleaned.groupby(group_column)[value_column].transform(
                lambda series: series.rolling(window=window, min_periods=1).sum()
            )
    return cleaned


def add_rainfall_window_features(
    df: pd.DataFrame,
    rainfall_column: str = "rainfall",
    windows: list[int] | tuple[int, ...] = (1, 3, 7, 30),
    group_column: str | None = None,
) -> pd.DataFrame:
    """Prepare rainfall accumulation windows for downstream ML tasks.

    This is a feature-preparation function only. It should support future modeling
    workflows, but it does not create labels or claim any finished predictions.
    """
    if rainfall_column not in df.columns:
        raise KeyError(f"Rainfall column not found: {rainfall_column}")

    cleaned = df.copy()
    for window in windows:
        suffix = f"rainfall_{window}d_total"
        if group_column is None:
            cleaned[suffix] = (
                cleaned[rainfall_column].rolling(window=window, min_periods=1).sum()
            )
        else:
            if group_column not in cleaned.columns:
                raise KeyError(f"Group column not found: {group_column}")
            cleaned[suffix] = cleaned.groupby(group_column)[rainfall_column].transform(
                lambda series: series.rolling(window=window, min_periods=1).sum()
            )
    return cleaned

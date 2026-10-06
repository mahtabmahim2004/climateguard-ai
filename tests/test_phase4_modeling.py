from __future__ import annotations

from pathlib import Path

import pandas as pd

from climateguard.models.baseline import build_feature_matrix, train_baseline_models
from climateguard.models.dataset import (
    add_lag_and_rolling_features,
    build_flood_risk_proxy,
    build_modeling_dataset,
    create_temporal_splits,
    load_raw_nasa_power_dataset,
)
from climateguard.models.evaluate import evaluate_model


def test_nasa_power_dataset_loads_and_normalizes() -> None:
    df = load_raw_nasa_power_dataset()

    assert {"date", "latitude", "longitude", "temperature", "rainfall", "humidity", "wind_speed", "pressure"}.issubset(df.columns)
    assert df["date"].notna().all()
    assert df["latitude"].eq(23.8103).all()
    assert df["longitude"].eq(90.4125).all()


def test_modeling_dataset_has_clean_temporal_features_and_proxy() -> None:
    path = Path("data/processed/flood_model_dataset.csv")
    model_df = build_modeling_dataset(output_path=path)

    assert path.exists()
    assert model_df["date"].is_monotonic_increasing
    assert "flood_risk_proxy" in model_df.columns
    assert set(model_df["flood_risk_proxy"]).issubset({0, 1})
    assert model_df["rainfall_7d_total"].notna().all()
    assert model_df["rainfall_lag_7d"].notna().all()


def test_temporal_splits_are_chronological() -> None:
    df = build_modeling_dataset(output_path=Path("data/processed/flood_model_dataset.csv"))
    splits = create_temporal_splits(df)

    assert splits["train"]["date"].max() < splits["validation"]["date"].min()
    assert splits["validation"]["date"].max() < splits["test"]["date"].min()


def test_lag_and_rolling_features_do_not_use_future_values() -> None:
    df = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=4, freq="D"),
            "latitude": [23.8103] * 4,
            "longitude": [90.4125] * 4,
            "temperature": [20.0, 22.0, 21.0, 23.0],
            "rainfall": [0.0, 5.0, 15.0, 2.0],
            "humidity": [70.0, 75.0, 80.0, 73.0],
            "wind_speed": [2.0, 2.5, 3.0, 2.8],
            "pressure": [101.2, 101.1, 101.0, 101.3],
        }
    )

    engineered = add_lag_and_rolling_features(df)

    assert pd.isna(engineered["rainfall_lag_1d"].iloc[0])
    assert engineered["rainfall_lag_1d"].iloc[1] == 0.0
    assert engineered["rainfall_3d_total"].iloc[2] == 20.0
    assert engineered["temperature_lag_2d"].iloc[2] == 20.0


def test_flood_proxy_target_is_binary_and_defined_from_past_rainfall() -> None:
    df = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=8, freq="D"),
            "rainfall": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 60.0],
            "temperature": [20.0, 21.0, 22.0, 23.0, 22.0, 21.0, 20.0, 19.0],
            "humidity": [70.0, 72.0, 75.0, 78.0, 77.0, 76.0, 74.0, 80.0],
            "wind_speed": [2.0, 3.0, 2.0, 3.5, 2.2, 2.1, 2.6, 3.0],
            "pressure": [101.0, 100.9, 101.1, 101.0, 100.8, 100.9, 101.2, 100.7],
            "latitude": [23.8103] * 8,
            "longitude": [90.4125] * 8,
        }
    )
    df = add_lag_and_rolling_features(df)
    proxy_df = build_flood_risk_proxy(df)

    assert set(proxy_df["flood_risk_proxy"]).issubset({0, 1})
    assert proxy_df["flood_risk_proxy"].iloc[7] == 1
    assert proxy_df["flood_risk_proxy"].iloc[0] == 0


def test_baseline_model_training_and_evaluation_run() -> None:
    df = build_modeling_dataset(output_path=Path("data/processed/flood_model_dataset.csv"))
    splits = create_temporal_splits(df)
    summary = train_baseline_models(
        splits["train"],
        splits["validation"],
        splits["test"],
        output_dir=Path("data/processed/models"),
    )

    assert set(summary["models"]).issuperset({"logistic_regression", "random_forest"})
    for model_name in ("logistic_regression", "random_forest"):
        X_valid = build_feature_matrix(splits["validation"], summary["feature_columns"])
        y_valid = splits["validation"]["flood_risk_proxy"].astype(int)
        metrics = evaluate_model(summary["models"][model_name]["model"], X_valid, y_valid)
        assert set(metrics).issuperset({"accuracy", "precision", "recall", "f1_score", "confusion_matrix"})

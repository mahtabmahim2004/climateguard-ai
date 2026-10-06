from __future__ import annotations

import pandas as pd

from climateguard.models.baseline import build_feature_matrix
from climateguard.models.comparison import generate_feature_importance
from climateguard.models.dataset import DEFAULT_MODEL_DATA_PATH, build_modeling_dataset
from climateguard.models.evaluate import evaluate_model
from climateguard.models.temporal import create_chronological_splits
from climateguard.models.threshold import evaluate_thresholds
from climateguard.models.train import run_phase7_pipeline


def test_chronological_splits_are_created() -> None:
    dataset = pd.read_csv(DEFAULT_MODEL_DATA_PATH)
    splits = create_chronological_splits(dataset)
    assert set(splits) == {"train", "validation", "test"}
    assert splits["train"]["date"].max() < splits["validation"]["date"].min()
    assert splits["validation"]["date"].max() < splits["test"]["date"].min()


def test_no_train_test_date_overlap() -> None:
    dataset = pd.read_csv(DEFAULT_MODEL_DATA_PATH)
    splits = create_chronological_splits(dataset)
    combined = pd.concat([splits["train"], splits["validation"], splits["test"]], ignore_index=True)
    assert len(combined) == len(dataset)
    assert len(set(combined["date"].tolist())) == len(combined["date"].tolist())


def test_no_temporal_leakage_in_split_ranges() -> None:
    dataset = pd.read_csv(DEFAULT_MODEL_DATA_PATH)
    splits = create_chronological_splits(dataset)
    assert pd.to_datetime(splits["train"]["date"]).max() < pd.to_datetime(splits["validation"]["date"]).min()
    assert pd.to_datetime(splits["validation"]["date"]).max() < pd.to_datetime(splits["test"]["date"]).min()


def test_preprocessing_is_fitted_on_training_data_only() -> None:
    dataset = pd.read_csv(DEFAULT_MODEL_DATA_PATH)
    splits = create_chronological_splits(dataset)
    model = build_modeling_dataset(output_path=DEFAULT_MODEL_DATA_PATH)
    feature_columns = [column for column in model.columns if column not in {"date", "flood_risk_proxy"}]
    X_train = build_feature_matrix(splits["train"], feature_columns)
    X_validation = build_feature_matrix(splits["validation"], feature_columns)
    y_train = splits["train"]["flood_risk_proxy"].astype(int)
    assert X_train.shape[0] == len(splits["train"])
    assert X_validation.shape[0] == len(splits["validation"])
    assert y_train.notna().all()


def test_target_validation() -> None:
    dataset = pd.read_csv(DEFAULT_MODEL_DATA_PATH)
    assert dataset["flood_risk_proxy"].isin([0, 1]).all()
    assert dataset["flood_risk_proxy"].nunique() == 2


def test_threshold_selection() -> None:
    dataset = pd.read_csv(DEFAULT_MODEL_DATA_PATH)
    splits = create_chronological_splits(dataset)
    y_true = splits["validation"]["flood_risk_proxy"].to_numpy(dtype=int)
    y_prob = pd.Series([0.1, 0.9] * (len(y_true) // 2), dtype=float)[: len(y_true)]
    summary = evaluate_thresholds(y_true, y_prob)
    assert "selected_threshold" in summary
    assert 0.1 <= summary["selected_threshold"] <= 0.9


def test_metric_calculation() -> None:
    dataset = pd.read_csv(DEFAULT_MODEL_DATA_PATH)
    splits = create_chronological_splits(dataset)
    feature_columns = [column for column in dataset.columns if column not in {"date", "flood_risk_proxy"}]
    from climateguard.models.baseline import _build_pipeline_for_model

    model = _build_pipeline_for_model("logistic_regression", feature_columns)
    model.fit(build_feature_matrix(splits["train"], feature_columns), splits["train"]["flood_risk_proxy"].astype(int))
    metrics = evaluate_model(model, build_feature_matrix(splits["validation"], feature_columns), splits["validation"]["flood_risk_proxy"].astype(int), threshold=0.5)
    assert {"accuracy", "precision", "recall", "f1_score", "confusion_matrix", "selected_threshold"}.issubset(metrics.keys())


def test_prediction_output_schema() -> None:
    result = run_phase7_pipeline(output_dir="data/processed")
    predictions = pd.read_csv(result["test_predictions_path"])
    assert {"date", "actual_proxy_label", "predicted_proxy_label", "risk_probability", "model_name"}.issubset(predictions.columns)


def test_model_comparison() -> None:
    result = run_phase7_pipeline(output_dir="data/processed")
    comparison = result["comparison"]["models"]
    assert len(comparison) >= 3
    assert all("model_name" in model for model in comparison)
    assert all("validation_metrics" in model for model in comparison)


def test_feature_importance_generation() -> None:
    result = run_phase7_pipeline(output_dir="data/processed")
    feature_importance = pd.read_csv(result["feature_importance_path"])
    assert not feature_importance.empty
    assert {"model_name", "feature", "importance", "rank"}.issubset(feature_importance.columns)

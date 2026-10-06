from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

from climateguard.models.calibration import (
    brier_score,
    calibration_curve,
    calibrate_probability_estimates,
    generate_model_selection_report,
    reliability_bins,
)
from climateguard.models.robustness import robustness_analysis
from climateguard.models.stability import temporal_stability_analysis
from climateguard.models.uncertainty import (
    assess_in_distribution,
    build_training_feature_stats,
    generate_proxy_risk_output,
    probability_to_proxy_risk_band,
)


def _synthetic_dataset() -> tuple[pd.DataFrame, pd.Series, pd.DataFrame, pd.Series]:
    rng = np.random.default_rng(42)
    n = 120
    rainfall = rng.normal(3.0, 1.2, size=n)
    temp = rng.normal(25.0, 3.0, size=n)
    humidity = rng.normal(60.0, 12.0, size=n)
    df = pd.DataFrame({
        "date": pd.date_range("2020-01-01", periods=n, freq="D"),
        "rainfall": rainfall,
        "temperature": temp,
        "humidity": humidity,
        "wind_speed": rng.normal(2.5, 0.6, size=n),
        "pressure": rng.normal(101.0, 2.0, size=n),
    })
    y = pd.Series((rainfall + humidity / 30.0 > 5.0).astype(int), index=np.arange(n))
    train_end = 80
    validation_end = 100
    X_train = df.iloc[:train_end].copy()
    y_train = y.iloc[:train_end].copy()
    X_valid = df.iloc[train_end:validation_end].copy()
    y_valid = y.iloc[train_end:validation_end].copy()
    X_test = df.iloc[validation_end:].copy()
    y_test = y.iloc[validation_end:].copy()
    return X_train, y_train, X_valid, y_valid, X_test, y_test


def test_probability_calibration() -> None:
    y_true = np.array([0, 0, 1, 1])
    y_prob = np.array([0.1, 0.3, 0.7, 0.9])
    curve = calibration_curve(y_true, y_prob)
    assert "brier_score" in curve
    assert "expected_calibration_error" in curve
    assert len(curve["bins"]) == 10


def test_brier_score_calculation() -> None:
    y_true = np.array([0, 1, 1, 0])
    y_prob = np.array([0.1, 0.8, 0.7, 0.2])
    assert 0.0 <= brier_score(y_true, y_prob) <= 1.0


def test_calibration_curve_generation() -> None:
    y_true = np.array([0, 0, 1, 1, 0, 1])
    y_prob = np.array([0.2, 0.1, 0.8, 0.9, 0.4, 0.6])
    bins = reliability_bins(y_true, y_prob)
    assert len(bins) == 10
    assert all("probability_bin" in row for row in bins)


def test_probability_band_conversion() -> None:
    assert probability_to_proxy_risk_band(0.20) == "LOW"
    assert probability_to_proxy_risk_band(0.50) == "MEDIUM"
    assert probability_to_proxy_risk_band(0.80) == "HIGH"


def test_perturbation_and_sensitivity_analysis() -> None:
    X_train, y_train, X_valid, y_valid, X_test, y_test = _synthetic_dataset()
    model = LogisticRegression(max_iter=2000, random_state=42)
    model.fit(X_train[["rainfall", "temperature", "humidity"]], y_train)
    output = robustness_analysis(model, X=X_valid[["rainfall", "temperature", "humidity"]], feature_columns=["rainfall", "temperature", "humidity"], perturbations={"rainfall": 0.1, "temperature": 0.05}, model_name="logistic_regression")
    assert output
    assert all("probability_change" in row for row in output)


def test_temporal_stability_analysis() -> None:
    X_train, y_train, X_valid, y_valid, X_test, y_test = _synthetic_dataset()
    model = LogisticRegression(max_iter=2000, random_state=42)
    model.fit(X_train[["rainfall", "temperature", "humidity"]], y_train)
    full_df = pd.concat([X_valid, X_test], ignore_index=True)
    full_df["flood_risk_proxy"] = pd.concat([y_valid, y_test], ignore_index=True)
    summary = temporal_stability_analysis(model, df=full_df, feature_columns=["rainfall", "temperature", "humidity"], date_column="date", target_column="flood_risk_proxy")
    assert summary["summary"]["period_count"] > 0
    assert "records" in summary


def test_ood_detection() -> None:
    df = pd.DataFrame({"rainfall": [1.0, 2.0, 3.0], "temperature": [20.0, 21.0, 22.0]})
    stats = build_training_feature_stats(df, ["rainfall", "temperature"])
    in_distribution, reason = assess_in_distribution({"rainfall": 2.0, "temperature": 21.0}, training_feature_stats=stats)
    assert in_distribution is True
    assert "training feature distribution" in reason.lower()
    out_of_distribution, _ = assess_in_distribution({"rainfall": 100.0, "temperature": 100.0}, training_feature_stats=stats)
    assert out_of_distribution is False


def test_proxy_risk_output_schema() -> None:
    payload = generate_proxy_risk_output(model_name="random_forest", probability=0.73, calibration_status="well_calibrated", in_distribution=True)
    assert {"model_name", "probability", "proxy_risk_band", "calibration_status", "in_distribution", "target_type", "scientific_warning"}.issubset(payload.keys())
    assert payload["proxy_risk_band"] in {"LOW", "MEDIUM", "HIGH"}


def test_model_selection_report() -> None:
    report = generate_model_selection_report(
        {
            "logistic_regression": {"calibration_quality": 0.8, "robustness": 0.7, "temporal_stability": 0.75, "validation_f1": 0.8, "strengths": ["simple"], "weaknesses": ["less flexible"]},
            "random_forest": {"calibration_quality": 0.9, "robustness": 0.9, "temporal_stability": 0.95, "validation_f1": 0.99, "strengths": ["tree"], "weaknesses": ["less linear"]},
        }
    )
    assert "candidate_models" in report
    assert "final_recommendation" in report
    assert report["final_recommendation"]["model_name"] == "random_forest"


def test_no_test_set_leakage_during_calibration() -> None:
    X_train, y_train, X_valid, y_valid, X_test, y_test = _synthetic_dataset()
    model = LogisticRegression(max_iter=2000, random_state=42)
    model.fit(X_train[["rainfall", "temperature", "humidity"]], y_train)
    calibrated_probs, baseline_probs, summary = calibrate_probability_estimates(
        model,
        X_validation=X_valid[["rainfall", "temperature", "humidity"]],
        y_validation=y_valid,
        X_target=X_test[["rainfall", "temperature", "humidity"]],
    )
    assert len(calibrated_probs) == len(baseline_probs) == len(X_test)
    assert "baseline_brier_score_validation" in summary
    assert "calibrated_brier_score_validation" in summary


def test_invalid_probability_handling() -> None:
    y_true = np.array([0, 1, 1])
    y_prob = np.array([-0.2, 0.5, 1.5])
    score = brier_score(y_true, y_prob)
    assert np.isfinite(score)
    assert 0.0 <= score <= 1.0


def test_calibration_method_supports_validation_only_fit() -> None:
    X_train, y_train, X_valid, y_valid, X_test, y_test = _synthetic_dataset()
    model = LogisticRegression(max_iter=2000, random_state=42)
    model.fit(X_train[["rainfall", "temperature", "humidity"]], y_train)
    calibrated_probs, baseline_probs, summary = calibrate_probability_estimates(
        model,
        X_validation=X_valid[["rainfall", "temperature", "humidity"]],
        y_validation=y_valid,
        X_target=X_test[["rainfall", "temperature", "humidity"]],
        method="sigmoid",
    )
    assert len(calibrated_probs) == len(X_test)
    assert summary["method"] == "sigmoid"

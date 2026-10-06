from __future__ import annotations

import joblib
import numpy as np
import pandas as pd
import pytest

from climateguard.config import PROCESSED_DATA_DIR
from climateguard.models.scenarios import (
    analyze_monotonicity,
    apply_feature_perturbation,
    compare_scenarios,
    create_scenario,
    evaluate_scenario,
    run_scenario,
    summarize_stress_tests,
)
from climateguard.models.uncertainty import build_training_feature_stats


@pytest.fixture
def scenario_fixture() -> dict[str, object]:
    dataset = pd.read_csv(PROCESSED_DATA_DIR / "flood_model_dataset.csv")
    feature_columns = [column for column in dataset.columns if column not in {"date", "flood_risk_proxy"}]
    model = joblib.load(PROCESSED_DATA_DIR / "models" / "random_forest.joblib")
    baseline = dataset.iloc[150].copy()
    training_stats = build_training_feature_stats(dataset[feature_columns], feature_columns)
    return {"dataset": dataset, "feature_columns": feature_columns, "model": model, "baseline": baseline, "training_stats": training_stats}


def test_scenario_creation(scenario_fixture: dict[str, object]) -> None:
    scenario = create_scenario("heavy_rainfall", {"rainfall": 0.20, "humidity": 0.10})
    assert scenario["name"] == "heavy_rainfall"
    assert scenario["feature_changes"]["rainfall"] == 0.20
    assert scenario["mode"] == "relative"


def test_feature_perturbation(scenario_fixture: dict[str, object]) -> None:
    baseline = scenario_fixture["baseline"]
    perturbed = apply_feature_perturbation(baseline, "rainfall", 0.20, mode="relative")
    assert perturbed["rainfall"] > baseline["rainfall"]


def test_baseline_preservation(scenario_fixture: dict[str, object]) -> None:
    baseline = scenario_fixture["baseline"]
    result = run_scenario(
        scenario_fixture["model"],
        baseline,
        {"rainfall": 0.0},
        feature_columns=scenario_fixture["feature_columns"],
        model_name="random_forest",
        training_feature_stats=scenario_fixture["training_stats"],
        scenario_name="baseline_check",
    )
    assert result["baseline_probability"] == pytest.approx(result["scenario_probability"], rel=1e-8, abs=1e-8)
    assert result["probability_delta"] == pytest.approx(0.0, abs=1e-8)


def test_probability_calculation(scenario_fixture: dict[str, object]) -> None:
    baseline = scenario_fixture["baseline"]
    result = evaluate_scenario(
        scenario_fixture["model"],
        baseline,
        {"name": "rainfall_increase", "feature_changes": {"rainfall": 0.30}},
        feature_columns=scenario_fixture["feature_columns"],
        model_name="random_forest",
        training_feature_stats=scenario_fixture["training_stats"],
    )
    assert 0.0 <= result["baseline_probability"] <= 1.0
    assert 0.0 <= result["scenario_probability"] <= 1.0
    assert "probability_delta" in result
    assert result["calibration_status"] == "not_evaluated"


def test_probability_delta(scenario_fixture: dict[str, object]) -> None:
    baseline = scenario_fixture["baseline"]
    result = evaluate_scenario(
        scenario_fixture["model"],
        baseline,
        {"name": "humidity_up", "feature_changes": {"humidity": 0.35}},
        feature_columns=scenario_fixture["feature_columns"],
        model_name="random_forest",
        training_feature_stats=scenario_fixture["training_stats"],
    )
    assert result["probability_delta"] == pytest.approx(result["scenario_probability"] - result["baseline_probability"])


def test_risk_band_transition(scenario_fixture: dict[str, object]) -> None:
    baseline = scenario_fixture["baseline"]
    result = evaluate_scenario(
        scenario_fixture["model"],
        baseline,
        {"name": "heavy_rainfall", "feature_changes": {"rainfall": 0.8, "humidity": 0.3}},
        feature_columns=scenario_fixture["feature_columns"],
        model_name="random_forest",
        training_feature_stats=scenario_fixture["training_stats"],
    )
    assert "risk_band_transition" in result
    assert result["risk_band_transition"] in {True, False}


def test_ood_propagation(scenario_fixture: dict[str, object]) -> None:
    baseline = scenario_fixture["baseline"]
    result = evaluate_scenario(
        scenario_fixture["model"],
        baseline,
        {"name": "rainfall_extreme", "feature_changes": {"rainfall": 3.0, "humidity": 1.5}},
        feature_columns=scenario_fixture["feature_columns"],
        model_name="random_forest",
        training_feature_stats=scenario_fixture["training_stats"],
    )
    assert "in_distribution" in result
    assert "ood_reason" in result


def test_multi_feature_scenarios(scenario_fixture: dict[str, object]) -> None:
    baseline = scenario_fixture["baseline"]
    scenarios = [
        {"name": "rainfall_plus", "feature_changes": {"rainfall": 0.2}},
        {"name": "rainfall_humidity_plus", "feature_changes": {"rainfall": 0.2, "humidity": 0.15}},
        {"name": "rainfall_minus", "feature_changes": {"rainfall": -0.2}},
    ]
    results = compare_scenarios(
        scenario_fixture["model"],
        baseline,
        scenarios,
        feature_columns=scenario_fixture["feature_columns"],
        model_name="random_forest",
        training_feature_stats=scenario_fixture["training_stats"],
    )
    assert len(results) == 3
    assert all("scenario_probability" in row for row in results)


def test_explanation_comparison(scenario_fixture: dict[str, object]) -> None:
    baseline = scenario_fixture["baseline"]
    result = evaluate_scenario(
        scenario_fixture["model"],
        baseline,
        {"name": "rainfall_up", "feature_changes": {"rainfall": 0.25}},
        feature_columns=scenario_fixture["feature_columns"],
        model_name="random_forest",
        training_feature_stats=scenario_fixture["training_stats"],
    )
    assert result["explanation_before"] is not None
    assert result["explanation_after"] is not None
    assert "top_contributing_features" in result["explanation_before"]


def test_stress_test_summary(scenario_fixture: dict[str, object]) -> None:
    baseline = scenario_fixture["baseline"]
    scenarios = [
        {"name": "rainfall_plus", "feature_changes": {"rainfall": 0.2}},
        {"name": "humidity_up", "feature_changes": {"humidity": 0.3}},
        {"name": "rainfall_minus", "feature_changes": {"rainfall": -0.2}},
    ]
    results = compare_scenarios(
        scenario_fixture["model"],
        baseline,
        scenarios,
        feature_columns=scenario_fixture["feature_columns"],
        model_name="random_forest",
        training_feature_stats=scenario_fixture["training_stats"],
    )
    summary = summarize_stress_tests(results)
    assert "largest_probability_increase" in summary
    assert "largest_probability_decrease" in summary
    assert "strongest_sensitivity_features" in summary


def test_monotonicity_sanity_analysis(scenario_fixture: dict[str, object]) -> None:
    monotonic = analyze_monotonicity(
        scenario_fixture["model"],
        scenario_fixture["baseline"],
        "rainfall",
        feature_columns=scenario_fixture["feature_columns"],
        perturbation_levels=[-0.20, -0.10, 0.0, 0.10, 0.20],
    )
    assert monotonic["monotonicity_status"] in {"increasing", "decreasing", "non_monotonic"}
    assert len(monotonic["probabilities"]) == 5


def test_invalid_feature_handling(scenario_fixture: dict[str, object]) -> None:
    with pytest.raises(KeyError):
        apply_feature_perturbation(scenario_fixture["baseline"], "not_a_feature", 0.15)


def test_invalid_perturbation_handling(scenario_fixture: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        apply_feature_perturbation(scenario_fixture["baseline"], "rainfall", float("nan"))


def test_deterministic_scenario_results(scenario_fixture: dict[str, object]) -> None:
    baseline = scenario_fixture["baseline"]
    result_one = evaluate_scenario(
        scenario_fixture["model"],
        baseline,
        {"name": "deterministic", "feature_changes": {"rainfall": 0.35, "humidity": 0.10}},
        feature_columns=scenario_fixture["feature_columns"],
        model_name="random_forest",
        training_feature_stats=scenario_fixture["training_stats"],
    )
    result_two = evaluate_scenario(
        scenario_fixture["model"],
        baseline,
        {"name": "deterministic", "feature_changes": {"rainfall": 0.35, "humidity": 0.10}},
        feature_columns=scenario_fixture["feature_columns"],
        model_name="random_forest",
        training_feature_stats=scenario_fixture["training_stats"],
    )
    assert result_one["baseline_probability"] == pytest.approx(result_two["baseline_probability"])
    assert result_one["scenario_probability"] == pytest.approx(result_two["scenario_probability"])

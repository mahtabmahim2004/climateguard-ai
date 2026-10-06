from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from climateguard.config import PROCESSED_DATA_DIR
from climateguard.models.explainability import (
    feature_directionality,
    generate_trust_report,
    global_feature_importance,
    local_prediction_explanation,
    partial_dependence_analysis,
    permutation_importance_analysis,
    save_explainability_artifacts,
)


def _load_modeling_dataset() -> tuple[pd.DataFrame, list[str]]:
    dataset = pd.read_csv(PROCESSED_DATA_DIR / "flood_model_dataset.csv")
    feature_columns = [column for column in dataset.columns if column not in {"date", "flood_risk_proxy"}]
    return dataset, feature_columns


def test_global_feature_importance_generation() -> None:
    dataset, feature_columns = _load_modeling_dataset()
    model = __import__("joblib").load(PROCESSED_DATA_DIR / "models" / "random_forest.joblib")
    importance = global_feature_importance(model, dataset[feature_columns], feature_columns, top_n=5, y=dataset["flood_risk_proxy"])
    assert not importance.empty
    assert {"feature", "importance", "rank"}.issubset(importance.columns)


def test_permutation_importance_summarizes_features() -> None:
    dataset, feature_columns = _load_modeling_dataset()
    model = __import__("joblib").load(PROCESSED_DATA_DIR / "models" / "random_forest.joblib")
    permutation = permutation_importance_analysis(model, dataset[feature_columns], dataset["flood_risk_proxy"], feature_columns)
    assert not permutation.empty
    assert {"feature", "importance_mean", "importance_std", "rank"}.issubset(permutation.columns)


def test_local_prediction_explanation_is_generated() -> None:
    dataset, feature_columns = _load_modeling_dataset()
    model = __import__("joblib").load(PROCESSED_DATA_DIR / "models" / "random_forest.joblib")
    explanation = local_prediction_explanation(model, dataset[feature_columns], feature_columns, sample_index=10, top_n=3)
    assert "predicted_probability" in explanation
    assert "top_contributing_features" in explanation
    assert explanation["scientific_warning"].lower().find("proxy") >= 0


def test_feature_directionality_has_signs() -> None:
    dataset, feature_columns = _load_modeling_dataset()
    model = __import__("joblib").load(PROCESSED_DATA_DIR / "models" / "random_forest.joblib")
    directionality = feature_directionality(model, dataset[feature_columns], feature_columns)
    assert directionality
    assert all("feature" in row and "direction" in row for row in directionality)


def test_partial_dependence_analysis_is_generated() -> None:
    dataset, feature_columns = _load_modeling_dataset()
    model = __import__("joblib").load(PROCESSED_DATA_DIR / "models" / "random_forest.joblib")
    curves = partial_dependence_analysis(model, dataset[feature_columns], feature_columns, grid_size=8)
    assert curves
    assert all("feature" in row and "partial_dependence_values" in row for row in curves)


def test_trust_report_contains_required_sections() -> None:
    dataset, feature_columns = _load_modeling_dataset()
    model = __import__("joblib").load(PROCESSED_DATA_DIR / "models" / "random_forest.joblib")
    report = generate_trust_report(model, dataset[feature_columns], dataset["flood_risk_proxy"], feature_columns)
    assert "global_feature_importance" in report
    assert "feature_directionality" in report
    assert "partial_dependence_analysis" in report
    assert "overall_trust_status" in report
    assert "proxy" in report["scientific_warning"].lower()


def test_explainability_artifacts_are_saved() -> None:
    dataset, feature_columns = _load_modeling_dataset()
    model = __import__("joblib").load(PROCESSED_DATA_DIR / "models" / "random_forest.joblib")
    outputs = save_explainability_artifacts(model, dataset[feature_columns], dataset["flood_risk_proxy"], feature_columns, output_dir=PROCESSED_DATA_DIR)
    for path in outputs.values():
        assert Path(path).exists()
    trust_report = json.loads(Path(outputs["trust_report"]).read_text(encoding="utf-8"))
    assert "overall_trust_status" in trust_report

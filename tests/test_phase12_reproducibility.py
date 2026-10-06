from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest
import sklearn

from climateguard.config import PROCESSED_DATA_DIR, PROJECT_ROOT
from climateguard.models.dataset import DEFAULT_FEATURE_COLUMNS
from climateguard.models.final_integration import _assess_phase12_completion
from climateguard.validation.reproducibility import (
    DEFAULT_AUDIT_OUTPUT,
    DEFAULT_HEALTH_OUTPUT,
    DEFAULT_MANIFEST_OUTPUT,
    TARGET_COLUMN,
    TARGET_DEFINITION,
    build_artifact_manifest,
    build_pipeline_health_report,
    build_scientific_audit,
    validate_reproducibility,
    validate_required_artifacts,
)

DATASET_PATH = PROCESSED_DATA_DIR / "flood_model_dataset.csv"


def _load_dataset() -> pd.DataFrame:
    return pd.read_csv(DATASET_PATH, parse_dates=["date"])


def test_required_phase12_and_prior_phase_artifacts_exist() -> None:
    required = [
        "phase8_alignment_report.json",
        "phase8_source_coverage.json",
        "phase10_model_trust_report.json",
        "phase10_feature_directionality.json",
        "phase10_partial_dependence.json",
        "phase11_scenario_results.json",
        "phase11_stress_test_summary.json",
        "phase11_sanity_checks.json",
        DEFAULT_MANIFEST_OUTPUT,
        DEFAULT_AUDIT_OUTPUT,
        DEFAULT_HEALTH_OUTPUT,
    ]
    missing = [name for name in required if not (PROCESSED_DATA_DIR / name).is_file()]
    assert not missing, f"Required Phase 12 or prior-phase artifacts are missing: {missing}"
    assert DATASET_PATH.is_file(), f"Required modeling dataset is missing: {DATASET_PATH}"


def test_artifact_manifest_is_valid_and_only_lists_existing_phase_1_to_11_files() -> None:
    manifest_path = PROCESSED_DATA_DIR / DEFAULT_MANIFEST_OUTPUT
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["phase"] == 12
    assert manifest["artifact_count"] == len(manifest["artifacts"])
    assert manifest["artifacts"]
    assert "only" in manifest["manifest_scope"].lower()
    for artifact in manifest["artifacts"]:
        path = PROJECT_ROOT / artifact["path"]
        assert 1 <= artifact["phase"] <= 11
        assert artifact["existence_status"] == "PRESENT"
        assert path.is_file(), f"Manifest points to a missing artifact: {artifact['path']}"
        assert artifact["artifact_type"]
        assert artifact["description"]
        if path.suffix.lower() == ".csv":
            assert artifact["row_count"] >= 0
            assert artifact["schema"]


def test_required_dataset_and_expected_features_are_available() -> None:
    assert DATASET_PATH.is_file()
    dataset = _load_dataset()
    missing_features = sorted(set(DEFAULT_FEATURE_COLUMNS) - set(dataset.columns))
    assert not missing_features, f"Required feature columns are missing: {missing_features}"
    assert TARGET_COLUMN in dataset.columns
    assert len(dataset) > 0


def test_temporal_periods_are_valid_and_non_overlapping() -> None:
    dataset = _load_dataset()
    train = dataset.loc[dataset["date"] <= "2021-12-31", "date"]
    validation = dataset.loc[dataset["date"].between("2022-01-01", "2023-12-31"), "date"]
    test = dataset.loc[dataset["date"] >= "2024-01-01", "date"]
    assert not train.empty and not validation.empty and not test.empty
    assert train.max() < validation.min()
    assert validation.max() < test.min()
    assert train.max() <= pd.Timestamp("2021-12-31")
    assert validation.min() >= pd.Timestamp("2022-01-01")
    assert test.min() >= pd.Timestamp("2024-01-01")


def test_target_definition_matches_rainfall_proxy_rule() -> None:
    dataset = _load_dataset()
    expected = ((dataset["rainfall_7d_total"] >= 60) & (dataset["rainfall"] >= 10)).astype("int64")
    actual = dataset[TARGET_COLUMN].astype("int64")
    assert actual.equals(expected)
    assert "rainfall-derived proxy" in TARGET_DEFINITION
    assert "not observed flood ground truth" in TARGET_DEFINITION


def test_scientific_audit_preserves_guardrails_and_reports_uncertainty_honestly() -> None:
    audit = json.loads((PROCESSED_DATA_DIR / DEFAULT_AUDIT_OUTPUT).read_text(encoding="utf-8"))
    assert audit["status"] in {"PASS", "WARN"}
    checks = audit["checks"]
    required_checks = {
        "target_is_rainfall_derived_proxy",
        "target_is_not_observed_flood_ground_truth",
        "no_fabricated_flood_labels",
        "no_fabricated_hydrological_observations",
        "no_nasa_bwdb_false_fusion",
        "no_date_shifting",
        "no_bwdb_interpolation",
        "no_invented_official_flood_thresholds",
        "no_causal_flood_prediction_claims",
        "model_probability_is_proxy_task_probability",
        "low_medium_high_are_proxy_risk_bands",
        "phase11_is_controlled_scenario_analysis",
        "phase11_is_not_official_climate_scenario",
        "ood_logic_remains_available",
        "temporal_evaluation_is_chronological",
        "test_data_remains_separated",
        "limitations_remain_documented",
    }
    assert required_checks.issubset(checks)
    assert all(item["status"] in {"PASS", "WARN", "FAIL"} for item in checks.values())
    assert checks["target_is_rainfall_derived_proxy"]["status"] == "PASS"
    assert checks["no_nasa_bwdb_false_fusion"]["status"] == "PASS"
    assert checks["phase11_is_controlled_scenario_analysis"]["status"] == "PASS"
    assert checks["ood_logic_remains_available"]["status"] == "PASS"


def test_nasa_and_bwdb_non_overlap_and_no_fused_training_dataset() -> None:
    alignment = json.loads((PROCESSED_DATA_DIR / "phase8_alignment_report.json").read_text(encoding="utf-8"))
    dataset = _load_dataset()
    assert alignment["overlap_exists"] is False
    assert alignment["overlapping_observation_count"] == 0
    assert alignment["combined_ml_training_dataset"] == "NOT_CREATED"
    assert not {"water_level_mMSL", "river_level", "station_id"} & set(dataset.columns)


def test_phase9_implementation_and_test_artifacts_exist() -> None:
    expected = [
        "src/climateguard/models/calibration.py",
        "src/climateguard/models/robustness.py",
        "src/climateguard/models/stability.py",
        "src/climateguard/models/uncertainty.py",
        "tests/test_phase9_calibration_robustness.py",
    ]
    missing = [name for name in expected if not (PROJECT_ROOT / name).is_file()]
    assert not missing, f"Phase 9 implementation/test files are missing: {missing}"


def test_phase10_artifacts_exist() -> None:
    expected = [
        "phase10_global_feature_importance.csv",
        "phase10_permutation_importance.csv",
        "phase10_feature_directionality.json",
        "phase10_partial_dependence.json",
        "phase10_local_examples.json",
        "phase10_model_trust_report.json",
    ]
    missing = [name for name in expected if not (PROCESSED_DATA_DIR / name).is_file()]
    assert not missing, f"Phase 10 outputs are missing: {missing}"


def test_phase11_artifacts_exist() -> None:
    expected = [
        "phase11_scenario_results.json",
        "phase11_stress_test_summary.json",
        "phase11_scenario_matrix.csv",
        "phase11_sanity_checks.json",
        "phase11_proxy_probability_comparison.png",
        "phase11_rainfall_scenario_response.png",
    ]
    missing = [name for name in expected if not (PROCESSED_DATA_DIR / name).is_file()]
    assert not missing, f"Phase 11 outputs are missing: {missing}"


def test_reproducibility_validation_is_deterministic() -> None:
    report = validate_reproducibility(DATASET_PATH, repeats=3, seed=42)
    assert report["status"] == "pass"
    assert report["is_reproducible"] is True
    assert report["n_rows"] == len(_load_dataset())
    assert len(report["fingerprints"]) == 3
    assert len(set(report["fingerprints"])) == 1
    assert report["checks"]["temporal_ranges"]["status"] == "PASS"
    assert report["checks"]["source_coverage"]["status"] == "PASS"


def test_missing_artifacts_and_dataset_produce_clear_failures(tmp_path: Path) -> None:
    missing_dataset = tmp_path / "missing.csv"
    reproducibility = validate_reproducibility(
        missing_dataset,
        processed_dir=tmp_path,
        project_root=tmp_path,
    )
    assert reproducibility["status"] == "fail"
    assert reproducibility["is_reproducible"] is False
    assert "missing" in reproducibility["error"].lower()

    artifact_check = validate_required_artifacts(
        output_dir=tmp_path,
        required_artifacts=["required-report.json", "required-data.csv"],
    )
    assert artifact_check["status"] == "fail"
    assert artifact_check["is_valid"] is False
    assert artifact_check["missing_artifacts"] == ["required-report.json", "required-data.csv"]


def test_pipeline_health_reports_component_statuses_explicitly() -> None:
    health = json.loads((PROCESSED_DATA_DIR / DEFAULT_HEALTH_OUTPUT).read_text(encoding="utf-8"))
    required = {
        "data_pipeline",
        "feature_pipeline",
        "model_pipeline",
        "temporal_evaluation",
        "calibration",
        "uncertainty",
        "explainability",
        "scenario_analysis",
        "tests",
        "documentation",
        "artifacts",
    }
    assert required.issubset(health["components"])
    assert health["status"] in {"PASS", "WARN", "FAIL"}
    assert all(
        component["status"] in {"PASS", "WARN", "FAIL"}
        for component in health["components"].values()
    )


def test_model_artifact_compatibility_reports_runtime_and_serialized_versions() -> None:
    health = build_pipeline_health_report()
    compatibility = health["components"]["model_artifact_compatibility"]["details_by_model"]
    assert compatibility["runtime_sklearn_version"] == sklearn.__version__
    assert compatibility["status"] in {"PASS", "WARN", "FAIL"}
    assert compatibility["models"]
    for model in compatibility["models"].values():
        assert model["load_status"] == "PASS"
        assert model["artifact_sklearn_versions"] == [sklearn.__version__]
        assert model["runtime_sklearn_version"] == sklearn.__version__
        assert model["compatibility_warnings"] == []


def test_scientific_audit_builder_is_repeatable() -> None:
    first = build_scientific_audit()
    second = build_scientific_audit()
    assert first == second


def test_scientific_audit_keeps_source_history_warns_with_local_snapshot_evidence() -> None:
    audit = build_scientific_audit()
    for name in (
        "no_fabricated_hydrological_observations",
        "no_date_shifting",
        "no_bwdb_interpolation",
    ):
        check = audit["checks"][name]
        assert check["status"] == "WARN"
        assert check["blocking"] is False
        assert check["classification"] == "non_blocking_source_evidence_limitation"
        assert check["local_snapshot_consistency"]["status"] == "PASS"
        assert all(check["local_snapshot_consistency"]["exact_date_value_metadata_match"].values())


def test_calibration_health_does_not_treat_phase11_default_label_as_evidence() -> None:
    calibration = build_pipeline_health_report()["components"]["calibration"]
    assert calibration["status"] == "WARN"
    assert calibration["blocking"] is False
    assert calibration["persisted_model_calibration_report"] is False
    assert calibration["phase11_calibration_status_labels"] == ["well_calibrated"]
    assert calibration["phase11_labels_are_evidence"] is False


def test_completion_gate_accepts_only_classified_warnings_and_passing_validation() -> None:
    warning = {"status": "WARN", "blocking": False, "classification": "documented_evidence_limit"}
    inputs = {
        "validation_results": {
            "phase12_tests": "PASS",
            "full_test_suite": "PASS",
            "compileall": "PASS",
        },
        "reproducibility": {"is_reproducible": True},
        "research_validation": {"is_valid": True},
        "scientific_audit": {"status": "WARN", "checks": {"source": warning}},
        "pipeline_health": {
            "status": "WARN",
            "components": {
                "model_artifact_compatibility": {"status": "PASS"},
                "calibration": warning,
            },
        },
        "required_files": {"reports": True},
    }
    assert _assess_phase12_completion(**inputs)["is_complete"] is True

    inputs["scientific_audit"] = {
        "status": "WARN",
        "checks": {"source": {"status": "WARN"}},
    }
    assessment = _assess_phase12_completion(**inputs)
    assert assessment["is_complete"] is False
    assert any("not classified as non-blocking" in item for item in assessment["blocking_reasons"])


def test_artifact_manifest_builder_is_repeatable() -> None:
    first = build_artifact_manifest()
    second = build_artifact_manifest()
    assert first == second


def test_pipeline_health_builder_is_repeatable() -> None:
    first = build_pipeline_health_report()
    second = build_pipeline_health_report()
    assert first == second


def test_pipeline_health_accepts_an_explicit_test_run_status() -> None:
    health = build_pipeline_health_report(test_status="PASS")
    assert health["components"]["tests"]["status"] == "PASS"
    with pytest.raises(ValueError, match="test_status"):
        build_pipeline_health_report(test_status="UNKNOWN")

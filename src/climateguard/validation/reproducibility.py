from __future__ import annotations

import hashlib
import json
import pickle
import pickletools
import warnings
from pathlib import Path
from typing import Any, Sequence

import joblib
import pandas as pd
import sklearn
from sklearn.exceptions import InconsistentVersionWarning

from climateguard.config import PROCESSED_DATA_DIR, PROJECT_ROOT

DEFAULT_PHASE12_OUTPUT = "phase12_final_integration_report.json"
DEFAULT_REPRODUCIBILITY_OUTPUT = "phase12_reproducibility_summary.json"
DEFAULT_VALIDATION_OUTPUT = "phase12_research_validation_report.json"
DEFAULT_MANIFEST_OUTPUT = "phase12_artifact_manifest.json"
DEFAULT_AUDIT_OUTPUT = "phase12_scientific_audit.json"
DEFAULT_HEALTH_OUTPUT = "phase12_pipeline_health.json"
TARGET_COLUMN = "flood_risk_proxy"
TARGET_DEFINITION = (
    "1 when rainfall_7d_total >= 60 mm and same-day rainfall >= 10 mm; "
    "otherwise 0. This is a rainfall-derived proxy, not observed flood ground truth."
)


def _expected_features() -> list[str]:
    from climateguard.models.dataset import DEFAULT_FEATURE_COLUMNS

    return list(DEFAULT_FEATURE_COLUMNS)


_ARTIFACTS: tuple[tuple[int, str, str, str], ...] = (
    (1, "README.md", "documentation", "Project foundation and documented scope."),
    (1, "requirements.txt", "environment", "Pinned Python dependency list."),
    (1, ".env.example", "configuration_template", "Environment-variable template without runtime secrets."),
    (2, "DATA_PIPELINE.md", "documentation", "Data workflow and pipeline scope."),
    (2, "DATA_DICTIONARY.md", "documentation", "Canonical data and feature definitions."),
    (2, "notebooks/phase2_eda_template.ipynb", "analysis_template", "Reusable exploratory-data-analysis notebook template."),
    (2, "src/climateguard/data/loader.py", "source_code", "General data-loading utilities."),
    (2, "src/climateguard/data/validation.py", "source_code", "Data validation utilities."),
    (2, "src/climateguard/data/cleaning.py", "source_code", "Data-cleaning utilities."),
    (2, "src/climateguard/features/engineering.py", "source_code", "Feature preparation utilities."),
    (2, "tests/test_data_pipeline.py", "test_suite", "Data pipeline unit tests."),
    (3, "data/raw/nasa_power_dhaka_daily_2015_2024.csv", "observed_data", "Retained NASA POWER daily meteorology source file."),
    (3, "data/processed/nasa_power_dhaka_daily_2015_2024_quality_report.json", "quality_report", "NASA POWER data quality summary."),
    (3, "data/external/dataset_manifest.csv", "manifest", "Dataset/source manifest."),
    (3, "src/climateguard/data/sources.py", "source_code", "Source-specific ingestion interfaces."),
    (3, "src/climateguard/data/canonical.py", "source_code", "Canonical data schema and provenance utilities."),
    (3, "PHASE3_DATA_ACQUISITION.md", "documentation", "Phase 3 verified-source acquisition notes."),
    (4, "data/processed/flood_model_dataset.csv", "modeling_dataset", "NASA POWER-derived modeling data and rainfall proxy target."),
    (4, "data/processed/phase4_model_training_summary.json", "evaluation_report", "Initial baseline model evaluation summary."),
    (4, "data/processed/models/logistic_regression.joblib", "model", "Persisted logistic regression estimator."),
    (4, "data/processed/models/random_forest.joblib", "model", "Persisted random forest estimator."),
    (4, "data/processed/models/gradient_boosting.joblib", "model", "Persisted gradient boosting estimator."),
    (4, "src/climateguard/models/dataset.py", "source_code", "Modeling dataset, proxy target, features, and chronological split implementation."),
    (4, "src/climateguard/models/baseline.py", "source_code", "Baseline model training implementation."),
    (4, "tests/test_phase4_modeling.py", "test_suite", "Phase 4 modeling tests."),
    (4, "PHASE4_ML_MODEL.md", "documentation", "Model target, evaluation design, and limitations."),
    (5, "data/processed/bwdb_water_level_SW42_clean.csv", "observed_data", "Cleaned BWDB SW42 hydrological observations."),
    (5, "data/processed/bwdb_water_level_SW42_provenance.json", "provenance", "Provenance metadata for the cleaned BWDB observations."),
    (5, "data/processed/bwdb_water_level_SW42_quality_report.json", "quality_report", "Quality summary for BWDB SW42 observations."),
    (5, "PHASE5_1_HYDROLOGICAL_ACQUISITION.md", "documentation", "BWDB acquisition and source-access status."),
    (5, "PHASE5_6_HYDROLOGICAL_DATA_CLEANING_VALIDATION.md", "documentation", "BWDB cleaning and validation documentation."),
    (6, "data/processed/bwdb_hydrological_observations.csv", "observed_data", "Canonical BWDB observations; separate from the NASA modeling data."),
    (6, "data/processed/bwdb_ground_truth_status.json", "scientific_status", "Availability status for hydrology and flood labels."),
    (6, "data/processed/bwdb_hydrological_integration_report.json", "integration_report", "BWDB structural integration readiness report."),
    (6, "src/climateguard/data/hydrological_integration.py", "source_code", "Hydrological integration and readiness reporting."),
    (6, "tests/test_phase6_hydrological_integration.py", "test_suite", "Phase 6 integration tests."),
    (7, "data/processed/phase7_model_comparison.json", "evaluation_report", "Chronological proxy-task model comparison."),
    (7, "data/processed/phase7_feature_importance.csv", "analysis_output", "Feature importance for the proxy target."),
    (7, "data/processed/phase7_test_predictions.csv", "evaluation_output", "Held-out chronological test predictions."),
    (7, "data/processed/phase7_error_analysis.json", "evaluation_report", "Held-out proxy-task error analysis."),
    (7, "data/processed/phase7_threshold_analysis.json", "evaluation_report", "Validation-threshold analysis; not an official flood threshold."),
    (7, "src/climateguard/models/train.py", "source_code", "Phase 7 model training/evaluation pipeline."),
    (7, "tests/test_phase7_ml_modeling.py", "test_suite", "Phase 7 scientific modeling tests."),
    (7, "PHASE7_SCIENTIFIC_ML_MODELING.md", "documentation", "Chronological proxy-task evaluation and limitations."),
    (8, "data/processed/phase8_alignment_report.json", "alignment_report", "Temporal source compatibility and fusion status."),
    (8, "data/processed/phase8_source_coverage.json", "coverage_report", "Observed source coverage and overlap report."),
    (8, "data/processed/phase8_feature_catalog.json", "feature_catalog", "Documented meteorological and hydrological feature definitions."),
    (8, "src/climateguard/data/temporal_alignment.py", "source_code", "Temporal source alignment utilities."),
    (8, "tests/test_phase8_temporal_alignment.py", "test_suite", "Phase 8 temporal alignment tests."),
    (8, "PHASE8_MULTI_SOURCE_ALIGNMENT.md", "documentation", "Source coverage and no-fusion findings."),
    (9, "src/climateguard/models/calibration.py", "source_code", "Probability calibration and calibration metrics utilities."),
    (9, "src/climateguard/models/robustness.py", "source_code", "Proxy-model robustness analysis utilities."),
    (9, "src/climateguard/models/stability.py", "source_code", "Temporal stability analysis utilities."),
    (9, "src/climateguard/models/uncertainty.py", "source_code", "Proxy-risk bands, OOD checks, and uncertainty output utilities."),
    (9, "tests/test_phase9_calibration_robustness.py", "test_suite", "Phase 9 calibration, robustness, and uncertainty tests."),
    (10, "data/processed/phase10_global_feature_importance.csv", "analysis_output", "Global feature importance for the proxy task."),
    (10, "data/processed/phase10_permutation_importance.csv", "analysis_output", "Permutation importance for the proxy task."),
    (10, "data/processed/phase10_feature_directionality.json", "analysis_output", "Feature-directionality summaries."),
    (10, "data/processed/phase10_partial_dependence.json", "analysis_output", "Partial-dependence-style proxy model analysis."),
    (10, "data/processed/phase10_local_examples.json", "analysis_output", "Local proxy model explanation examples."),
    (10, "data/processed/phase10_model_trust_report.json", "trust_report", "Model trust and limitation report."),
    (10, "src/climateguard/models/explainability.py", "source_code", "Proxy-model explanation and trust analysis."),
    (10, "tests/test_phase10_explainability.py", "test_suite", "Phase 10 explainability tests."),
    (10, "PHASE10_EXPLAINABILITY_AND_TRUST.md", "documentation", "Explainability methods and scientific limitations."),
    (11, "data/processed/phase11_scenario_results.json", "scenario_output", "Controlled proxy-model perturbation results."),
    (11, "data/processed/phase11_stress_test_summary.json", "scenario_output", "Summary of Phase 11 proxy-model stress tests."),
    (11, "data/processed/phase11_scenario_matrix.csv", "scenario_output", "Baseline/scenario matrix results."),
    (11, "data/processed/phase11_sanity_checks.json", "scenario_output", "Controlled feature-sweep sanity checks."),
    (11, "data/processed/phase11_proxy_probability_comparison.png", "visualization", "Baseline versus scenario model probability plot."),
    (11, "data/processed/phase11_rainfall_scenario_response.png", "visualization", "Model response to controlled rainfall perturbations."),
    (11, "src/climateguard/models/scenarios.py", "source_code", "Controlled proxy-model scenario and stress-test implementation."),
    (11, "tests/test_phase11_scenarios.py", "test_suite", "Phase 11 scenario-analysis tests."),
    (11, "PHASE11_SCENARIO_ANALYSIS.md", "documentation", "Scenario-analysis scope and scientific guardrails."),
)

_REQUIRED_PHASE11_ARTIFACTS = tuple(
    Path(path).name for phase, path, _, _ in _ARTIFACTS if phase == 11 and path.startswith("data/")
)
_REQUIRED_PHASE10_ARTIFACTS = tuple(
    Path(path).name for phase, path, _, _ in _ARTIFACTS if phase == 10 and path.startswith("data/")
)


def _check(status: str, evidence: str, *, value: Any = None) -> dict[str, Any]:
    result: dict[str, Any] = {"status": status, "evidence": evidence}
    if value is not None:
        result["value"] = value
    return result


def _json_read(path: Path) -> dict[str, Any] | list[Any] | None:
    if not path.is_file():
        return None
    try:
        with path.open("r", encoding="utf-8") as stream:
            parsed = json.load(stream)
    except (OSError, json.JSONDecodeError):
        return None
    return parsed if isinstance(parsed, (dict, list)) else None


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace").lower()
    except OSError:
        return ""


def _dataset_path(path: str | Path | None, processed_dir: Path) -> Path:
    candidate = Path(path) if path is not None else processed_dir / "flood_model_dataset.csv"
    return candidate / "flood_model_dataset.csv" if candidate.is_dir() else candidate


def _read_dataset(path: Path) -> tuple[pd.DataFrame | None, str | None]:
    if not path.is_file():
        return None, f"Required processed dataset is missing: {path}"
    try:
        frame = pd.read_csv(path)
    except (OSError, pd.errors.ParserError, pd.errors.EmptyDataError, UnicodeDecodeError) as exc:
        return None, f"Could not read processed dataset {path}: {exc}"
    if frame.empty:
        return frame, f"Required processed dataset is empty: {path}"
    return frame, None


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _frame_fingerprint(frame: pd.DataFrame) -> str:
    normalized = frame.copy()
    if "date" in normalized.columns:
        normalized["date"] = pd.to_datetime(normalized["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    data = normalized.to_csv(index=False, lineterminator="\n", float_format="%.17g").encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _feature_and_target_checks(frame: pd.DataFrame) -> tuple[dict[str, Any], bool]:
    expected_features = _expected_features()
    missing_features = [column for column in expected_features if column not in frame.columns]
    if TARGET_COLUMN not in frame.columns:
        target_check = _check("FAIL", f"Target column {TARGET_COLUMN!r} is missing.")
        target_valid = False
    elif not {"rainfall", "rainfall_7d_total"}.issubset(frame.columns):
        target_check = _check("FAIL", "Cannot validate the target rule because rainfall input columns are missing.")
        target_valid = False
    else:
        expected = (
            (pd.to_numeric(frame["rainfall_7d_total"], errors="coerce") >= 60)
            & (pd.to_numeric(frame["rainfall"], errors="coerce") >= 10)
        ).astype("int64")
        actual = pd.to_numeric(frame[TARGET_COLUMN], errors="coerce")
        target_valid = bool(actual.notna().all() and actual.astype("int64").equals(expected))
        target_check = _check(
            "PASS" if target_valid else "FAIL",
            "Target values match the documented rainfall-only rule."
            if target_valid
            else "Target values do not match the documented rainfall-only rule.",
            value=TARGET_DEFINITION,
        )
    feature_check = _check(
        "PASS" if not missing_features else "FAIL",
        "All expected model features are present."
        if not missing_features
        else "Expected model features are missing.",
        value={"expected": expected_features, "missing": missing_features},
    )
    return {"features": feature_check, "target_definition": target_check}, not missing_features and target_valid


def _temporal_summary(frame: pd.DataFrame) -> dict[str, Any]:
    if "date" not in frame.columns:
        return {
            "status": "FAIL",
            "error": "Dataset has no date column.",
            "ranges": {},
            "no_overlap": False,
        }
    dates = pd.to_datetime(frame["date"], errors="coerce")
    if dates.isna().any() or dates.empty:
        return {
            "status": "FAIL",
            "error": "Dataset contains invalid or absent dates.",
            "ranges": {},
            "no_overlap": False,
        }

    ranges: dict[str, Any] = {}
    masks = {
        "train": dates <= pd.Timestamp("2021-12-31"),
        "validation": (dates >= pd.Timestamp("2022-01-01")) & (dates <= pd.Timestamp("2023-12-31")),
        "test": dates >= pd.Timestamp("2024-01-01"),
    }
    for name, mask in masks.items():
        period = dates[mask]
        ranges[name] = {
            "start": period.min().strftime("%Y-%m-%d") if not period.empty else None,
            "end": period.max().strftime("%Y-%m-%d") if not period.empty else None,
            "row_count": int(mask.sum()),
        }
    populated = all(value["row_count"] > 0 for value in ranges.values())
    ordered = bool(
        populated
        and ranges["train"]["end"] < ranges["validation"]["start"]
        and ranges["validation"]["end"] < ranges["test"]["start"]
    )
    return {
        "status": "PASS" if ordered else "FAIL",
        "ranges": ranges,
        "no_overlap": ordered,
        "chronological": ordered,
    }


def _source_coverage(processed_dir: Path) -> dict[str, Any]:
    coverage = _json_read(processed_dir / "phase8_source_coverage.json")
    alignment = _json_read(processed_dir / "phase8_alignment_report.json")
    if not isinstance(coverage, list) or not isinstance(alignment, dict):
        return {"status": "WARN", "evidence": "Phase 8 source coverage or alignment report is missing or invalid."}
    by_name = {str(item.get("source_name", "")).upper(): item for item in coverage if isinstance(item, dict)}
    nasa = by_name.get("NASA_POWER")
    bwdb = by_name.get("BWDB")
    overlap = alignment.get("overlap_exists")
    acceptable = bool(nasa and bwdb and overlap is False)
    details = {
        "nasa_power": nasa.get("date_range") if nasa else None,
        "bwdb": bwdb.get("date_range") if bwdb else None,
        "overlap_exists": overlap,
        "combined_ml_training_dataset": alignment.get("combined_ml_training_dataset"),
    }
    return {
        "status": "PASS" if acceptable else "FAIL",
        "evidence": "Phase 8 records both source ranges and reports no temporal overlap."
        if acceptable
        else "Phase 8 does not establish the expected no-overlap source status.",
        **details,
    }


def _bwdb_snapshot_consistency(project_root: Path, processed_dir: Path) -> dict[str, Any]:
    """Compare preserved BWDB HTML with persisted tables; this cannot authenticate the external source."""
    raw_path = project_root / "data" / "raw" / "phase5_5_hydrological_dataset" / "bwdb_water_level_SW42_last_30d_raw.html"
    output_names = ("bwdb_water_level_SW42_clean.csv", "bwdb_hydrological_observations.csv")
    try:
        from climateguard.data.bwdb_hydrology import parse_bwdb_water_level_html

        raw_records = parse_bwdb_water_level_html(raw_path.read_text(encoding="utf-8", errors="replace"))
        parsed = pd.DataFrame(raw_records)
        columns = ["date", "water_level_mMSL", "station_id", "station_name", "river", "district"]
        parsed["date"] = pd.to_datetime(parsed["date"], errors="coerce").dt.strftime("%Y-%m-%d")
        parsed["water_level_mMSL"] = pd.to_numeric(parsed["water_level_mMSL"], errors="coerce")
        parsed = parsed.loc[:, columns].sort_values("date").reset_index(drop=True)

        outputs: dict[str, bool] = {}
        row_counts: dict[str, int | None] = {}
        for name in output_names:
            output_path = processed_dir / name
            if not output_path.is_file():
                outputs[name] = False
                row_counts[name] = None
                continue
            saved = pd.read_csv(output_path)
            if not set(columns).issubset(saved.columns):
                outputs[name] = False
                row_counts[name] = len(saved)
                continue
            saved["date"] = pd.to_datetime(saved["date"], errors="coerce").dt.strftime("%Y-%m-%d")
            saved["water_level_mMSL"] = pd.to_numeric(saved["water_level_mMSL"], errors="coerce")
            for column in ("station_id", "station_name", "river", "district"):
                saved[column] = saved[column].astype(str)
            saved = saved.loc[:, columns].sort_values("date").reset_index(drop=True)
            outputs[name] = bool(parsed.equals(saved))
            row_counts[name] = len(saved)

        consistent = bool(raw_records and all(outputs.values()))
        return {
            "status": "PASS" if consistent else "WARN",
            "scope": "Local raw-snapshot transformation consistency only; not independent source authentication.",
            "raw_snapshot": str(raw_path.relative_to(project_root)),
            "parsed_row_count": len(parsed),
            "persisted_row_counts": row_counts,
            "exact_date_value_metadata_match": outputs,
            "date_shifting_or_interpolation_detected": False if consistent else None,
        }
    except (OSError, KeyError, ValueError, pd.errors.ParserError) as error:
        return {
            "status": "WARN",
            "scope": "Local raw-snapshot transformation consistency only; not independent source authentication.",
            "raw_snapshot": str(raw_path.relative_to(project_root)),
            "error": f"{type(error).__name__}: {error}",
            "exact_date_value_metadata_match": {},
            "date_shifting_or_interpolation_detected": None,
        }


def _model_availability(project_root: Path) -> dict[str, Any]:
    expected = [
        "data/processed/models/logistic_regression.joblib",
        "data/processed/models/random_forest.joblib",
        "data/processed/models/gradient_boosting.joblib",
    ]
    available = [path for path in expected if (project_root / path).is_file()]
    return {
        "status": "PASS" if available else "FAIL",
        "expected": expected,
        "available": available,
        "missing": [path for path in expected if path not in available],
    }


def _model_artifact_compatibility(project_root: Path, availability: dict[str, Any]) -> dict[str, Any]:
    """Check saved sklearn version metadata and loadability without rewriting model artifacts."""
    runtime_version = sklearn.__version__
    models: dict[str, Any] = {}
    for relative_path in availability["available"]:
        path = project_root / relative_path
        artifact_versions: set[str] = set()
        metadata_error: str | None = None
        try:
            operations = list(pickletools.genops(path.read_bytes()))
            for index, (opcode, argument, _) in enumerate(operations):
                if argument != "_sklearn_version":
                    continue
                next_index = index + 1
                while next_index < len(operations) and operations[next_index][0].name == "MEMOIZE":
                    next_index += 1
                if next_index < len(operations) and isinstance(operations[next_index][1], str):
                    artifact_versions.add(operations[next_index][1])
        except (OSError, ValueError, IndexError) as error:
            metadata_error = f"{type(error).__name__}: {error}"

        load_error: str | None = None
        compatibility_warnings: list[str] = []
        try:
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always", InconsistentVersionWarning)
                joblib.load(path)
            for item in caught:
                if issubclass(item.category, InconsistentVersionWarning):
                    compatibility_warnings.append(str(item.message))
                    warnings.warn_explicit(item.message, item.category, item.filename, item.lineno)
        except (
            AttributeError,
            EOFError,
            ImportError,
            ModuleNotFoundError,
            OSError,
            pickle.UnpicklingError,
            TypeError,
            ValueError,
        ) as error:
            load_error = f"{type(error).__name__}: {error}"

        if load_error is not None:
            status = "FAIL"
        elif metadata_error is not None or not artifact_versions:
            status = "WARN"
        elif artifact_versions != {runtime_version} or compatibility_warnings:
            status = "WARN"
        else:
            status = "PASS"
        models[relative_path] = {
            "status": status,
            "load_status": "FAIL" if load_error else "PASS",
            "runtime_sklearn_version": runtime_version,
            "artifact_sklearn_versions": sorted(artifact_versions),
            "compatibility_warnings": compatibility_warnings,
            "metadata_error": metadata_error,
            "load_error": load_error,
        }

    statuses = [model["status"] for model in models.values()]
    overall = "FAIL" if "FAIL" in statuses else "WARN" if "WARN" in statuses or len(models) != len(availability["expected"]) else "PASS"
    return {
        "status": overall,
        "runtime_sklearn_version": runtime_version,
        "models": models,
    }


def _audit_item(status: str, detail: str, evidence: Sequence[str] = ()) -> dict[str, Any]:
    return {"status": status, "detail": detail, "evidence": list(evidence)}


def build_scientific_audit(
    *,
    project_root: str | Path = PROJECT_ROOT,
    processed_dir: str | Path | None = None,
    dataset_path: str | Path | None = None,
) -> dict[str, Any]:
    """Audit the scientific constraints using data, code, reports, and documentation actually present."""
    root = Path(project_root)
    processed = Path(processed_dir) if processed_dir is not None else root / "data" / "processed"
    data_path = _dataset_path(dataset_path, processed)
    frame, read_error = _read_dataset(data_path)
    alignment = _json_read(processed / "phase8_alignment_report.json")
    ground_truth = _json_read(processed / "bwdb_ground_truth_status.json")
    source_coverage = _source_coverage(processed)
    bwdb_snapshot = _bwdb_snapshot_consistency(root, processed)
    model_uncertainty = _read_text(root / "src" / "climateguard" / "models" / "uncertainty.py")
    target_code = _read_text(root / "src" / "climateguard" / "models" / "dataset.py")
    scenario_code = _read_text(root / "src" / "climateguard" / "models" / "scenarios.py")
    temporal_code = _read_text(root / "src" / "climateguard" / "models" / "temporal.py")
    phase4_doc = _read_text(root / "PHASE4_ML_MODEL.md")
    phase6_doc = _read_text(root / "PHASE6_HYDROLOGICAL_INTEGRATION.md")
    phase7_doc = _read_text(root / "PHASE7_SCIENTIFIC_ML_MODELING.md")
    phase8_doc = _read_text(root / "PHASE8_MULTI_SOURCE_ALIGNMENT.md")
    phase10_doc = _read_text(root / "PHASE10_EXPLAINABILITY_AND_TRUST.md")
    phase11_doc = _read_text(root / "PHASE11_SCENARIO_ANALYSIS.md")
    phase12_doc = _read_text(root / "PHASE12_REPRODUCIBILITY_AND_FINAL_VALIDATION.md")

    target_checks, target_valid = _feature_and_target_checks(frame) if frame is not None and not frame.empty else ({}, False)
    frame_columns = set(frame.columns) if frame is not None else set()
    hydrology_in_dataset = bool({"water_level_mMSL", "river_level", "station_id"} & frame_columns)
    ranges = _temporal_summary(frame) if frame is not None and not frame.empty else {"status": "FAIL", "ranges": {}, "no_overlap": False}
    nasa_to_bwdb_nonoverlap = bool(
        isinstance(alignment, dict)
        and alignment.get("overlap_exists") is False
        and alignment.get("combined_ml_training_dataset") == "NOT_CREATED"
        and not hydrology_in_dataset
    )
    bwdb_status_evidence = (
        isinstance(ground_truth, dict)
        and (processed / "bwdb_hydrological_observations.csv").is_file()
    )
    bwdb_interpolation_evidence = (
        "no interpolation" in phase6_doc
        and (processed / "bwdb_hydrological_observations.csv").is_file()
    )
    docs_complete = all((root / name).is_file() for name in (
        "PHASE4_ML_MODEL.md",
        "PHASE6_HYDROLOGICAL_INTEGRATION.md",
        "PHASE7_SCIENTIFIC_ML_MODELING.md",
        "PHASE8_MULTI_SOURCE_ALIGNMENT.md",
        "PHASE10_EXPLAINABILITY_AND_TRUST.md",
        "PHASE11_SCENARIO_ANALYSIS.md",
    ))

    checks: dict[str, dict[str, Any]] = {
        "target_is_rainfall_derived_proxy": _audit_item(
            "PASS" if target_valid else "FAIL",
            "Target is verified against the rainfall-only rule."
            if target_valid
            else "Target could not be verified against the rainfall-only rule.",
            ["src/climateguard/models/dataset.py", "data/processed/flood_model_dataset.csv"],
        ),
        "target_is_not_observed_flood_ground_truth": _audit_item(
            "PASS" if target_valid and isinstance(ground_truth, dict) and ground_truth.get("official_flood_labels", {}).get("available") is False else "WARN",
            "Target rule and ground-truth status distinguish proxy target from observed flood labels."
            if target_valid and isinstance(ground_truth, dict) and ground_truth.get("official_flood_labels", {}).get("available") is False
            else "Official flood ground-truth unavailability could not be confirmed from the current artifacts.",
            ["data/processed/bwdb_ground_truth_status.json", "PHASE4_ML_MODEL.md"],
        ),
        "no_fabricated_flood_labels": _audit_item(
            "PASS" if target_valid and "not a real flood label" in target_code else "WARN",
            "Target is computed from the documented rainfall rule; no independent flood labels are used."
            if target_valid and "not a real flood label" in target_code
            else "No fabricated labels are evidenced, but the target-generation claim is not fully verifiable.",
            ["src/climateguard/models/dataset.py", "data/processed/flood_model_dataset.csv"],
        ),
        "no_fabricated_hydrological_observations": _audit_item(
            "WARN" if bwdb_status_evidence else "FAIL",
            "The preserved raw BWDB snapshot parses to the same dates, values, and station metadata in both persisted tables; external source authenticity still cannot be independently established."
            if bwdb_snapshot["status"] == "PASS" and bwdb_status_evidence
            else "Local source consistency could not be established, and external source authenticity cannot be independently verified."
            if bwdb_status_evidence
            else "Required BWDB source-status evidence is missing.",
            [
                "data/raw/phase5_5_hydrological_dataset/bwdb_water_level_SW42_last_30d_raw.html",
                "data/processed/bwdb_water_level_SW42_clean.csv",
                "data/processed/bwdb_hydrological_observations.csv",
                "data/processed/bwdb_hydrological_integration_provenance.json",
            ],
        ),
        "no_nasa_bwdb_false_fusion": _audit_item(
            "PASS" if nasa_to_bwdb_nonoverlap else "FAIL",
            "Phase 8 reports no source date overlap, no combined ML dataset, and the proxy training table has no hydrology columns."
            if nasa_to_bwdb_nonoverlap
            else "Current alignment or modeling artifacts do not support the documented no-fusion claim.",
            ["data/processed/phase8_alignment_report.json", "data/processed/flood_model_dataset.csv"],
        ),
        "no_date_shifting": _audit_item(
            "WARN" if source_coverage["status"] == "PASS" else "FAIL",
            "Persisted BWDB dates match the preserved raw snapshot exactly; this cannot establish whether dates were altered before that snapshot was captured."
            if bwdb_snapshot["status"] == "PASS" and source_coverage["status"] == "PASS"
            else "Source coverage is present, but local raw-snapshot date consistency could not be established."
            if source_coverage["status"] == "PASS"
            else "Source coverage evidence is missing or invalid.",
            [
                "data/raw/phase5_5_hydrological_dataset/bwdb_water_level_SW42_last_30d_raw.html",
                "data/processed/bwdb_water_level_SW42_clean.csv",
                "data/processed/phase8_source_coverage.json",
                "PHASE8_MULTI_SOURCE_ALIGNMENT.md",
            ],
        ),
        "no_bwdb_interpolation": _audit_item(
            "WARN" if bwdb_interpolation_evidence else "FAIL",
            "The preserved raw snapshot and both persisted tables match row-for-row, with no added interpolated rows; processing before the snapshot cannot be independently audited."
            if bwdb_snapshot["status"] == "PASS" and bwdb_interpolation_evidence
            else "The documentation states no interpolation, but local raw-snapshot consistency could not be established."
            if bwdb_interpolation_evidence
            else "Expected BWDB non-interpolation evidence is missing.",
            [
                "data/raw/phase5_5_hydrological_dataset/bwdb_water_level_SW42_last_30d_raw.html",
                "data/processed/bwdb_water_level_SW42_clean.csv",
                "data/processed/bwdb_hydrological_observations.csv",
                "PHASE6_HYDROLOGICAL_INTEGRATION.md",
            ],
        ),
        "no_invented_official_flood_thresholds": _audit_item(
            "PASS" if isinstance(ground_truth, dict) and ground_truth.get("official_flood_threshold", {}).get("available") is False else "WARN",
            "Ground-truth status says no official flood threshold is established."
            if isinstance(ground_truth, dict) and ground_truth.get("official_flood_threshold", {}).get("available") is False
            else "Official threshold availability is not established by current artifacts.",
            ["data/processed/bwdb_ground_truth_status.json", "PHASE7_SCIENTIFIC_ML_MODELING.md"],
        ),
        "no_causal_flood_prediction_claims": _audit_item(
            "PASS" if "no causal claim" in phase11_doc and "does not claim real flood forecasting" in phase10_doc else "WARN",
            "Phase 10 and Phase 11 documentation explicitly limits interpretation and disclaims causal/forecast claims."
            if "no causal claim" in phase11_doc and "does not claim real flood forecasting" in phase10_doc
            else "Scientific limitation documentation is incomplete or could not be verified.",
            ["PHASE10_EXPLAINABILITY_AND_TRUST.md", "PHASE11_SCENARIO_ANALYSIS.md"],
        ),
        "model_probability_is_proxy_task_probability": _audit_item(
            "PASS" if "proxy-risk" in model_uncertainty and "not an observed flood probability" in model_uncertainty else "WARN",
            "Prediction output labels probability as rainfall-derived proxy risk, not observed flood probability."
            if "proxy-risk" in model_uncertainty and "not an observed flood probability" in model_uncertainty
            else "Uncertainty output does not clearly preserve proxy-task interpretation.",
            ["src/climateguard/models/uncertainty.py"],
        ),
        "low_medium_high_are_proxy_risk_bands": _audit_item(
            "PASS" if "probability_to_proxy_risk_band" in model_uncertainty and all(label in model_uncertainty for label in ("low", "medium", "high")) else "WARN",
            "LOW/MEDIUM/HIGH are generated as proxy-risk bands."
            if "probability_to_proxy_risk_band" in model_uncertainty and all(label in model_uncertainty for label in ("low", "medium", "high"))
            else "Risk-band interpretation is not verified.",
            ["src/climateguard/models/uncertainty.py"],
        ),
        "phase11_is_controlled_scenario_analysis": _audit_item(
            "PASS" if "controlled" in phase11_doc and "stress testing" in phase11_doc else "WARN",
            "Phase 11 code and documentation describe controlled model perturbations."
            if "controlled" in phase11_doc and "stress testing" in phase11_doc
            else "Phase 11 scenario scope is not clearly verified.",
            ["src/climateguard/models/scenarios.py", "PHASE11_SCENARIO_ANALYSIS.md"],
        ),
        "phase11_is_not_official_climate_scenario": _audit_item(
            "PASS" if "not an official climate scenario" in phase12_doc and "apply_feature_perturbation" in scenario_code else "WARN",
            "Phase 11 is documented as model stress testing rather than an official climate scenario."
            if "not an official climate scenario" in phase12_doc and "apply_feature_perturbation" in scenario_code
            else "Phase 11 climate-scenario status is unclear.",
            ["PHASE11_SCENARIO_ANALYSIS.md"],
        ),
        "ood_logic_remains_available": _audit_item(
            "PASS" if "def assess_in_distribution" in model_uncertainty and "assess_in_distribution" in scenario_code else "FAIL",
            "OOD assessment implementation remains available and is consumed by scenario logic."
            if "def assess_in_distribution" in model_uncertainty and "assess_in_distribution" in scenario_code
            else "OOD assessment implementation is missing or disconnected.",
            ["src/climateguard/models/uncertainty.py", "src/climateguard/models/scenarios.py"],
        ),
        "temporal_evaluation_is_chronological": _audit_item(
            "PASS" if ranges.get("status") == "PASS" and "chronological" in temporal_code else "FAIL",
            "Dataset ranges conform to non-overlapping train, validation, and test chronology."
            if ranges.get("status") == "PASS" and "chronological" in temporal_code
            else "Chronological split evidence is invalid or missing.",
            ["src/climateguard/models/temporal.py", "data/processed/phase7_model_comparison.json"],
        ),
        "test_data_remains_separated": _audit_item(
            "PASS" if ranges.get("status") == "PASS" and (processed / "phase7_test_predictions.csv").is_file() else "FAIL",
            "A separate 2024 test range and test prediction artifact are present."
            if ranges.get("status") == "PASS" and (processed / "phase7_test_predictions.csv").is_file()
            else "Independent test-range evidence is missing.",
            ["data/processed/phase7_test_predictions.csv", "data/processed/phase7_model_comparison.json"],
        ),
        "limitations_remain_documented": _audit_item(
            "PASS" if docs_complete and ("limitation" in phase4_doc or "limitations" in phase7_doc) else "WARN",
            "Phase 4, 6, 7, 8, 10, and 11 limitation documents are present."
            if docs_complete and ("limitation" in phase4_doc or "limitations" in phase7_doc)
            else "One or more phase limitation documents are missing.",
            ["PHASE4_ML_MODEL.md", "PHASE6_HYDROLOGICAL_INTEGRATION.md", "PHASE7_SCIENTIFIC_ML_MODELING.md", "PHASE8_MULTI_SOURCE_ALIGNMENT.md", "PHASE10_EXPLAINABILITY_AND_TRUST.md", "PHASE11_SCENARIO_ANALYSIS.md"],
        ),
    }
    for check_name in (
        "no_fabricated_hydrological_observations",
        "no_date_shifting",
        "no_bwdb_interpolation",
    ):
        checks[check_name]["blocking"] = False
        checks[check_name]["classification"] = "non_blocking_source_evidence_limitation"
        checks[check_name]["local_snapshot_consistency"] = bwdb_snapshot
    if read_error:
        checks["dataset_readability"] = _audit_item("FAIL", read_error)

    statuses = {item["status"] for item in checks.values()}
    overall = "FAIL" if "FAIL" in statuses else "WARN" if "WARN" in statuses else "PASS"
    return {
        "phase": 12,
        "status": overall,
        "checks": checks,
        "completion_warnings": [
            name for name, item in checks.items()
            if item["status"] == "WARN"
        ],
        "summary": {
            "pass": sum(item["status"] == "PASS" for item in checks.values()),
            "warn": sum(item["status"] == "WARN" for item in checks.values()),
            "fail": sum(item["status"] == "FAIL" for item in checks.values()),
        },
        "scientific_scope": "Audit applies to this repository's rainfall-derived proxy task and does not validate real-world flood forecasting.",
    }


def _artifact_metadata(path: Path, artifact_type: str) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "existence_status": "PRESENT" if path.is_file() else "MISSING",
        "artifact_type": artifact_type,
    }
    if not path.is_file():
        return metadata
    metadata["size_bytes"] = path.stat().st_size
    metadata["sha256"] = _file_sha256(path)
    if path.suffix.lower() == ".csv":
        try:
            if artifact_type == "observed_data" and path.name.startswith("nasa_power_"):
                from climateguard.models.dataset import load_raw_nasa_power_dataset

                frame = load_raw_nasa_power_dataset(path)
            else:
                frame = pd.read_csv(path)
        except (OSError, ValueError, pd.errors.ParserError, pd.errors.EmptyDataError, UnicodeDecodeError):
            metadata["read_status"] = "UNREADABLE"
            return metadata
        metadata["row_count"] = int(len(frame))
        metadata["schema"] = list(frame.columns)
        date_columns = [name for name in frame.columns if name.lower() in {"date", "observation_date"}]
        for date_column in date_columns:
            dates = pd.to_datetime(frame[date_column], errors="coerce").dropna()
            if not dates.empty:
                metadata["date_coverage"] = {
                    "column": date_column,
                    "start": dates.min().strftime("%Y-%m-%d"),
                    "end": dates.max().strftime("%Y-%m-%d"),
                }
                break
    elif path.suffix.lower() == ".json":
        parsed = _json_read(path)
        if isinstance(parsed, dict):
            metadata["schema"] = list(parsed.keys())
            for key in ("rows", "n_rows", "observation_count", "row_count"):
                if isinstance(parsed.get(key), int):
                    metadata["row_count"] = parsed[key]
                    break
            for key in ("date_range", "nasa_date_range", "bwdb_date_range"):
                value = parsed.get(key)
                if isinstance(value, dict):
                    start = value.get("earliest", value.get("min", value.get("start")))
                    end = value.get("latest", value.get("max", value.get("end")))
                    if start is not None or end is not None:
                        metadata["date_coverage"] = {"start": start, "end": end}
                        break
    return metadata


def build_artifact_manifest(
    *,
    project_root: str | Path = PROJECT_ROOT,
    processed_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Describe only known Phase 1–11 artifacts that actually exist in the project."""
    root = Path(project_root)
    processed = Path(processed_dir) if processed_dir is not None else root / "data" / "processed"
    records = []
    for phase, relative_path, artifact_type, description in _ARTIFACTS:
        path = root / relative_path
        if not path.is_file():
            continue
        record = {
            "phase": phase,
            "path": relative_path.replace("\\", "/"),
            "description": description,
            **_artifact_metadata(path, artifact_type),
        }
        records.append(record)
    records.sort(key=lambda item: (item["phase"], item["path"]))
    return {
        "phase": 12,
        "manifest_scope": "Existing Phase 1–11 project artifacts only; no missing or hypothetical artifacts are represented.",
        "artifact_count": len(records),
        "artifacts": records,
        "phase_counts": {
            str(phase): sum(item["phase"] == phase for item in records)
            for phase in range(1, 12)
        },
        "processed_data_directory": str(processed),
    }


def _health_component(status: str, details: str, evidence: Sequence[str] = ()) -> dict[str, Any]:
    return {"status": status, "details": details, "evidence": list(evidence)}


def build_pipeline_health_report(
    *,
    project_root: str | Path = PROJECT_ROOT,
    processed_dir: str | Path | None = None,
    dataset_path: str | Path | None = None,
    test_status: str | None = None,
) -> dict[str, Any]:
    """Report explicit component status based on present source, dataset, reports, and tests."""
    root = Path(project_root)
    processed = Path(processed_dir) if processed_dir is not None else root / "data" / "processed"
    path = _dataset_path(dataset_path, processed)
    frame, read_error = _read_dataset(path)
    temporal = _temporal_summary(frame) if frame is not None and not frame.empty else {"status": "FAIL"}
    target_checks, target_valid = _feature_and_target_checks(frame) if frame is not None and not frame.empty else ({}, False)
    source_check = _source_coverage(processed)
    model_check = _model_availability(root)
    model_compatibility = _model_artifact_compatibility(root, model_check)
    scenario_results = _json_read(processed / "phase11_scenario_results.json")
    scenario_calibration_labels = sorted({
        str(item["calibration_status"])
        for item in scenario_results
        if isinstance(item, dict) and item.get("calibration_status") is not None
    }) if isinstance(scenario_results, list) else []

    normalized_test_status = test_status.upper() if test_status is not None else "WARN"
    if normalized_test_status not in {"PASS", "WARN", "FAIL"}:
        raise ValueError("test_status must be PASS, WARN, FAIL, or None.")
    components: dict[str, dict[str, Any]] = {
        "data_pipeline": _health_component(
            "PASS" if frame is not None and not frame.empty and source_check["status"] == "PASS" else "FAIL",
            "Processed proxy dataset and both-source coverage report are available."
            if frame is not None and not frame.empty and source_check["status"] == "PASS"
            else read_error or "Dataset or Phase 8 source-coverage validation failed.",
            ["data/processed/flood_model_dataset.csv", "data/processed/phase8_source_coverage.json"],
        ),
        "feature_pipeline": _health_component(
            target_checks.get("features", {}).get("status", "FAIL"),
            "Expected model features are present." if target_checks.get("features", {}).get("status") == "PASS" else "One or more expected model features are missing.",
            ["src/climateguard/models/dataset.py"],
        ),
        "model_pipeline": _health_component(
            model_check["status"],
            "At least one persisted model is available."
            if model_check["available"]
            else "No persisted model artifact is available.",
            model_check["available"],
        ),
        "model_artifact_compatibility": _health_component(
            model_compatibility["status"],
            "Persisted model metadata matches the current scikit-learn runtime and every available model loads."
            if model_compatibility["status"] == "PASS"
            else "One or more model versions could not be verified or loaded; see per-model compatibility evidence.",
            model_check["available"],
        ) | {"details_by_model": model_compatibility},
        "temporal_evaluation": _health_component(
            temporal.get("status", "FAIL"),
            "Chronological train, validation, and test periods are populated and non-overlapping."
            if temporal.get("status") == "PASS"
            else "Chronological period validation failed.",
            ["src/climateguard/models/temporal.py", "data/processed/phase7_model_comparison.json"],
        ),
        "calibration": _health_component(
            "WARN",
            "Calibration utilities are tested on synthetic fixtures, but no persisted calibration metrics exist for the saved project models. Phase 11's well_calibrated field is a default label, not calibration evidence.",
            [
                "src/climateguard/models/calibration.py",
                "tests/test_phase9_calibration_robustness.py",
                "src/climateguard/models/scenarios.py",
                "data/processed/phase11_scenario_results.json",
            ],
        ) | {
            "blocking": False,
            "classification": "non_blocking_missing_model_calibration_evidence",
            "persisted_model_calibration_report": False,
            "phase11_calibration_status_labels": scenario_calibration_labels,
            "phase11_labels_are_evidence": False,
        },
        "uncertainty": _health_component(
            "PASS" if (root / "src/climateguard/models/uncertainty.py").is_file() and (root / "tests/test_phase9_calibration_robustness.py").is_file() else "FAIL",
            "Proxy-risk output and OOD assessment implementation/tests are present."
            if (root / "src/climateguard/models/uncertainty.py").is_file() and (root / "tests/test_phase9_calibration_robustness.py").is_file()
            else "Uncertainty/OOD source or tests are missing.",
            ["src/climateguard/models/uncertainty.py", "tests/test_phase9_calibration_robustness.py"],
        ),
        "explainability": _health_component(
            "PASS" if all((processed / item).is_file() for item in ("phase10_model_trust_report.json", "phase10_feature_directionality.json", "phase10_partial_dependence.json")) else "FAIL",
            "Core Phase 10 explanation outputs are available."
            if all((processed / item).is_file() for item in ("phase10_model_trust_report.json", "phase10_feature_directionality.json", "phase10_partial_dependence.json"))
            else "One or more core Phase 10 outputs are missing.",
            ["data/processed/phase10_model_trust_report.json", "data/processed/phase10_feature_directionality.json", "data/processed/phase10_partial_dependence.json"],
        ),
        "scenario_analysis": _health_component(
            "PASS" if all((processed / item).is_file() for item in _REQUIRED_PHASE11_ARTIFACTS) else "FAIL",
            "All declared Phase 11 scenario outputs are available."
            if all((processed / item).is_file() for item in _REQUIRED_PHASE11_ARTIFACTS)
            else "One or more declared Phase 11 scenario outputs are missing.",
            [path for path in _REQUIRED_PHASE11_ARTIFACTS if (processed / path).is_file()],
        ),
        "tests": _health_component(
            normalized_test_status,
            "Most recent test run status was supplied by the validation orchestrator."
            if test_status is not None
            else "Test modules are present; this report does not execute tests and records no latest test-run result.",
            ["tests/test_phase12_reproducibility.py", "tests/test_phase9_calibration_robustness.py", "tests/test_phase10_explainability.py", "tests/test_phase11_scenarios.py"],
        ),
        "documentation": _health_component(
            "PASS" if all((root / name).is_file() for name in ("PHASE10_EXPLAINABILITY_AND_TRUST.md", "PHASE11_SCENARIO_ANALYSIS.md", "PHASE8_MULTI_SOURCE_ALIGNMENT.md")) else "WARN",
            "Core scientific, source-alignment, and scenario documentation is present."
            if all((root / name).is_file() for name in ("PHASE10_EXPLAINABILITY_AND_TRUST.md", "PHASE11_SCENARIO_ANALYSIS.md", "PHASE8_MULTI_SOURCE_ALIGNMENT.md"))
            else "One or more core phase documentation files are missing.",
            ["PHASE8_MULTI_SOURCE_ALIGNMENT.md", "PHASE10_EXPLAINABILITY_AND_TRUST.md", "PHASE11_SCENARIO_ANALYSIS.md"],
        ),
        "artifacts": _health_component(
            "PASS" if all((processed / item).is_file() for item in (*_REQUIRED_PHASE10_ARTIFACTS, *_REQUIRED_PHASE11_ARTIFACTS)) and model_check["available"] else "FAIL",
            "Phase 10/11 outputs and model files are present."
            if all((processed / item).is_file() for item in (*_REQUIRED_PHASE10_ARTIFACTS, *_REQUIRED_PHASE11_ARTIFACTS)) and model_check["available"]
            else "Required Phase 10/11 or model artifacts are missing.",
            [path for path in (*_REQUIRED_PHASE10_ARTIFACTS, *_REQUIRED_PHASE11_ARTIFACTS) if (processed / path).is_file()] + model_check["available"],
        ),
    }
    statuses = {component["status"] for component in components.values()}
    overall = "FAIL" if "FAIL" in statuses else "WARN" if "WARN" in statuses else "PASS"
    return {
        "phase": 12,
        "status": overall,
        "components": components,
        "dataset": {
            "path": str(path),
            "row_count": int(len(frame)) if frame is not None else None,
            "temporal_ranges": temporal.get("ranges", {}),
            "target_valid": target_valid,
        },
    }


def validate_reproducibility(
    dataset_path: str | Path | None = None,
    *,
    repeats: int = 3,
    seed: int = 42,
    output_dir: str | Path | None = None,
    processed_dir: str | Path | None = None,
    project_root: str | Path = PROJECT_ROOT,
) -> dict[str, Any]:
    """Validate dataset availability, schema, time splits, source coverage, artifacts, and stable fingerprints."""
    if repeats < 1:
        raise ValueError("repeats must be at least 1.")
    root = Path(project_root)
    processed = Path(processed_dir) if processed_dir is not None else root / "data" / "processed"
    path = _dataset_path(dataset_path, processed)
    frame, read_error = _read_dataset(path)
    if frame is None or frame.empty:
        report = {
            "status": "fail",
            "is_reproducible": False,
            "dataset_path": str(path),
            "repeats": repeats,
            "seed": seed,
            "fingerprints": [],
            "error": read_error or f"Required processed dataset is missing: {path}",
            "checks": {"dataset_availability": _check("FAIL", read_error or f"Required processed dataset is missing: {path}")},
        }
    else:
        target_checks, target_valid = _feature_and_target_checks(frame)
        temporal = _temporal_summary(frame)
        source = _source_coverage(processed)
        model_availability = _model_availability(root)
        model_compatibility = _model_artifact_compatibility(root, model_availability)
        availability = _check("PASS", "Processed dataset exists and is nonempty.", value={"rows": int(len(frame))})
        expected_features = _expected_features()
        schema = _check(
            "PASS" if {"date", TARGET_COLUMN, *expected_features}.issubset(frame.columns) else "FAIL",
            "Required target, date, and model feature schema is present."
            if {"date", TARGET_COLUMN, *expected_features}.issubset(frame.columns)
            else "Required target/date/features are missing.",
            value=list(frame.columns),
        )
        model_check = _check(
            model_availability["status"],
            "Model artifacts are available." if model_availability["available"] else "No expected persisted model artifacts are available.",
            value=model_availability,
        )
        audit = build_scientific_audit(project_root=root, processed_dir=processed, dataset_path=path)
        audit_status = "FAIL" if audit["status"] == "FAIL" else "WARN" if audit["status"] == "WARN" else "PASS"
        fingerprints: list[str] = []
        read_consistent = True
        for _ in range(repeats):
            fingerprints.append(_frame_fingerprint(frame))
            current, error = _read_dataset(path)
            if error or current is None or _frame_fingerprint(current) != fingerprints[-1]:
                read_consistent = False
        checks = {
            "dataset_availability": availability,
            "dataset_schema": schema,
            "row_counts": _check("PASS", "Row counts are recorded from the available dataset.", value={"total": int(len(frame))}),
            "date_ranges": _check("PASS" if temporal["status"] == "PASS" else "FAIL", "Dataset date ranges were parsed and summarized.", value=temporal["ranges"]),
            "feature_availability": target_checks["features"],
            "target_definition": target_checks["target_definition"],
            "temporal_ranges": _check(temporal["status"], "Train/validation/test ranges are chronological and non-overlapping." if temporal["status"] == "PASS" else temporal.get("error", "Temporal range validation failed."), value=temporal["ranges"]),
            "model_artifact_availability": model_check,
            "model_artifact_compatibility": _check(
                model_compatibility["status"],
                "Persisted models match the current scikit-learn runtime and load successfully."
                if model_compatibility["status"] == "PASS"
                else "Persisted model runtime compatibility is incomplete or has warnings.",
                value=model_compatibility,
            ),
            "source_coverage": _check(source["status"], source["evidence"], value={key: value for key, value in source.items() if key not in {"status", "evidence"}}),
            "repeated_dataset_fingerprint": _check("PASS" if read_consistent and len(set(fingerprints)) == 1 else "FAIL", "Repeated dataset reads produced identical canonical fingerprints." if read_consistent and len(set(fingerprints)) == 1 else "Dataset fingerprints changed between repeated reads.", value=fingerprints),
            "scientific_guardrails": _check(audit_status, "Scientific audit completed.", value=audit["summary"]),
        }
        hard_failures = {"FAIL"} & {item["status"] for item in checks.values()}
        report = {
            "status": "fail" if hard_failures else "pass",
            "is_reproducible": not hard_failures,
            "dataset_path": str(path),
            "repeats": repeats,
            "seed": seed,
            "n_rows": int(len(frame)),
            "n_columns": int(len(frame.columns)),
            "schema": list(frame.columns),
            "date_range": {
                "start": pd.to_datetime(frame["date"]).min().strftime("%Y-%m-%d"),
                "end": pd.to_datetime(frame["date"]).max().strftime("%Y-%m-%d"),
            } if "date" in frame else None,
            "fingerprints": fingerprints,
            "checks": checks,
            "scientific_warning": "A reproducibility PASS validates repository data consistency and artifacts only; it does not establish flood-prediction validity.",
        }

    if output_dir is not None:
        output_path = Path(output_dir) / DEFAULT_REPRODUCIBILITY_OUTPUT
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        report["report_path"] = str(output_path)
    return report


def validate_required_artifacts(
    *,
    output_dir: str | Path = PROCESSED_DATA_DIR,
    required_artifacts: Sequence[str],
) -> dict[str, Any]:
    """Return clear missing-artifact diagnostics for a requested artifact list."""
    target = Path(output_dir)
    missing = [str(name) for name in required_artifacts if not (target / name).is_file()]
    present = [str(name) for name in required_artifacts if (target / name).is_file()]
    return {
        "status": "fail" if missing else "pass",
        "is_valid": not missing,
        "required_artifacts": list(required_artifacts),
        "existing_artifacts": present,
        "missing_artifacts": missing,
        "checks": {str(name): (target / name).is_file() for name in required_artifacts},
    }


def write_phase12_reports(
    *,
    project_root: str | Path = PROJECT_ROOT,
    processed_dir: str | Path | None = None,
    dataset_path: str | Path | None = None,
    test_status: str | None = None,
) -> dict[str, Any]:
    """Write the Phase 12 manifest, scientific audit, pipeline health, and reproducibility reports."""
    root = Path(project_root)
    processed = Path(processed_dir) if processed_dir is not None else root / "data" / "processed"
    processed.mkdir(parents=True, exist_ok=True)
    reproducibility = validate_reproducibility(
        dataset_path,
        output_dir=processed,
        processed_dir=processed,
        project_root=root,
    )
    manifest = build_artifact_manifest(project_root=root, processed_dir=processed)
    audit = build_scientific_audit(project_root=root, processed_dir=processed, dataset_path=dataset_path)
    health = build_pipeline_health_report(
        project_root=root,
        processed_dir=processed,
        dataset_path=dataset_path,
        test_status=test_status,
    )
    outputs = {
        "artifact_manifest": (processed / DEFAULT_MANIFEST_OUTPUT, manifest),
        "scientific_audit": (processed / DEFAULT_AUDIT_OUTPUT, audit),
        "pipeline_health": (processed / DEFAULT_HEALTH_OUTPUT, health),
    }
    for path, payload in outputs.values():
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return {
        "reproducibility": reproducibility,
        "artifact_manifest": manifest,
        "scientific_audit": audit,
        "pipeline_health": health,
        "report_paths": {
            "reproducibility": str(processed / DEFAULT_REPRODUCIBILITY_OUTPUT),
            **{name: str(path) for name, (path, _) in outputs.items()},
        },
    }


__all__ = [
    "DEFAULT_PHASE12_OUTPUT",
    "DEFAULT_REPRODUCIBILITY_OUTPUT",
    "DEFAULT_VALIDATION_OUTPUT",
    "DEFAULT_MANIFEST_OUTPUT",
    "DEFAULT_AUDIT_OUTPUT",
    "DEFAULT_HEALTH_OUTPUT",
    "TARGET_COLUMN",
    "TARGET_DEFINITION",
    "build_artifact_manifest",
    "build_pipeline_health_report",
    "build_scientific_audit",
    "validate_reproducibility",
    "validate_required_artifacts",
    "write_phase12_reports",
]

from __future__ import annotations

import json
import math
import os
from datetime import date
from http import HTTPStatus
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs
from wsgiref.simple_server import make_server

import joblib
import numpy as np
import pandas as pd
import sklearn

from climateguard.config import PROCESSED_DATA_DIR
from climateguard.models.baseline import build_feature_matrix
from climateguard.models.dataset import DEFAULT_FEATURE_COLUMNS
from climateguard.models.explainability import local_prediction_explanation
from climateguard.models.scenarios import run_scenario
from climateguard.models.uncertainty import (
    assess_in_distribution,
    build_training_feature_stats,
    generate_proxy_risk_output,
)

MODEL_NAMES = ("logistic_regression", "random_forest", "gradient_boosting")
MODEL_LABELS = {
    "logistic_regression": "Logistic Regression",
    "random_forest": "Random Forest",
    "gradient_boosting": "Gradient Boosting",
}
SCIENTIFIC_WARNING = (
    "This is rainfall-derived proxy-model output, not an observed flood prediction or official warning."
)
SCENARIO_WARNING = (
    "These are controlled proxy-model scenario responses; they are not real flood warnings or forecast evaluations."
)
WEB_DIR = Path(__file__).resolve().parent / "web"
STATIC_DIR = WEB_DIR / "static"
CURRENT_FEATURES = {
    "temperature": (-90.0, 65.0),
    "rainfall": (0.0, 1000.0),
    "humidity": (0.0, 100.0),
    "wind_speed": (0.0, 100.0),
    "pressure": (50.0, 120.0),
}


class ApiRequestError(Exception):
    def __init__(self, status: HTTPStatus, message: str) -> None:
        super().__init__(message)
        self.status = status


def _load_dataset() -> pd.DataFrame:
    path = PROCESSED_DATA_DIR / "flood_model_dataset.csv"
    if not path.is_file():
        raise FileNotFoundError(f"Processed modeling dataset is missing: {path}")
    frame = pd.read_csv(path, parse_dates=["date"])
    missing = sorted(set(DEFAULT_FEATURE_COLUMNS + ["date"]) - set(frame.columns))
    if missing:
        raise ValueError(f"Processed modeling dataset is missing required columns: {missing}")
    if frame.empty or frame["date"].isna().any():
        raise ValueError("Processed modeling dataset is empty or has invalid dates.")
    return frame.sort_values("date").reset_index(drop=True)


def _load_models() -> dict[str, Any]:
    loaded: dict[str, Any] = {}
    for model_name in MODEL_NAMES:
        path = PROCESSED_DATA_DIR / "models" / f"{model_name}.joblib"
        if not path.is_file():
            raise FileNotFoundError(f"Saved model artifact is missing: {path}")
        model = joblib.load(path)
        if not hasattr(model, "predict_proba"):
            raise TypeError(f"Saved model '{model_name}' does not support predict_proba.")
        feature_names = list(getattr(model, "feature_names_in_", []))
        if feature_names != DEFAULT_FEATURE_COLUMNS:
            raise ValueError(
                f"Saved model '{model_name}' feature schema does not match the project's "
                "canonical feature pipeline."
            )
        loaded[model_name] = model
    return loaded


def _load_model_metrics() -> dict[str, dict[str, Any]]:
    path = PROCESSED_DATA_DIR / "phase7_model_comparison.json"
    if not path.is_file():
        raise FileNotFoundError(f"Persisted Phase 7 model comparison is missing: {path}")
    comparison = json.loads(path.read_text(encoding="utf-8"))
    rows = comparison.get("models")
    if not isinstance(rows, list):
        raise ValueError("Phase 7 model comparison does not contain a models list.")
    return {str(row["model_name"]): row for row in rows}


def _training_features(dataset: pd.DataFrame | None = None) -> pd.DataFrame:
    frame = dataset if dataset is not None else _load_dataset()
    training = frame.loc[frame["date"] < pd.Timestamp("2022-01-01")]
    if training.empty:
        raise ValueError("No training-period rows are available for reference statistics.")
    return build_feature_matrix(training, DEFAULT_FEATURE_COLUMNS)


def _training_feature_stats(dataset: pd.DataFrame | None = None) -> dict[str, dict[str, float]]:
    return build_training_feature_stats(_training_features(dataset), DEFAULT_FEATURE_COLUMNS)


def _dataset_row(reference_date: date, dataset: pd.DataFrame | None = None) -> pd.Series:
    frame = dataset if dataset is not None else _load_dataset()
    matches = frame.loc[frame["date"].dt.date == reference_date]
    if matches.empty:
        raise ApiRequestError(
            HTTPStatus.UNPROCESSABLE_ENTITY,
            "Choose a date present in the processed NASA POWER modeling dataset.",
        )
    return matches.iloc[0].copy()


def _reference_payload(row: pd.Series) -> dict[str, Any]:
    return {
        "reference_date": row["date"].date().isoformat(),
        "temperature": float(row["temperature"]),
        "rainfall": float(row["rainfall"]),
        "humidity": float(row["humidity"]),
        "wind_speed": float(row["wind_speed"]),
        "pressure": float(row["pressure"]),
    }


def _build_observation(request: dict[str, Any], dataset: pd.DataFrame | None = None) -> pd.DataFrame:
    row = _dataset_row(request["reference_date"], dataset)
    rainfall_delta = request["rainfall"] - float(row["rainfall"])
    for feature in CURRENT_FEATURES:
        row[feature] = request[feature]
    row["rainfall_1d"] = request["rainfall"]
    for feature in ("rainfall_3d_total", "rainfall_7d_total", "rainfall_14d_total"):
        row[feature] = float(row[feature]) + rainfall_delta
    return build_feature_matrix(pd.DataFrame([row]), DEFAULT_FEATURE_COLUMNS)


def _probability(model: Any, observation: pd.DataFrame) -> float:
    values = np.asarray(model.predict_proba(observation), dtype=float)
    if values.ndim != 2 or values.shape[1] < 2 or not np.isfinite(values[0, 1]):
        raise ValueError("Saved model returned an invalid binary probability result.")
    return float(np.clip(values[0, 1], 0.0, 1.0))


def _metric_threshold(model_name: str, metrics: dict[str, dict[str, Any]]) -> float:
    row = metrics.get(model_name)
    if row is None or "selected_threshold" not in row:
        raise ValueError(f"No persisted selected threshold is available for {model_name}.")
    return float(row["selected_threshold"])


def _prediction_result(
    model_name: str,
    model: Any,
    observation: pd.DataFrame,
    metrics: dict[str, dict[str, Any]],
    training_stats: dict[str, dict[str, float]],
) -> dict[str, Any]:
    probability = _probability(model, observation)
    in_distribution, reason = assess_in_distribution(
        observation,
        training_feature_stats=training_stats,
    )
    result = generate_proxy_risk_output(
        model_name=model_name,
        probability=probability,
        calibration_status="not_evaluated",
        in_distribution=in_distribution,
        scientific_warning=SCIENTIFIC_WARNING,
    )
    result.update(
        {
            "model_label": MODEL_LABELS[model_name],
            "proxy_label": int(probability >= _metric_threshold(model_name, metrics)),
            "decision_threshold": _metric_threshold(model_name, metrics),
            "ood_reason": reason,
        }
    )
    return result


def _load_explainability() -> dict[str, Any]:
    importance_path = PROCESSED_DATA_DIR / "phase10_global_feature_importance.csv"
    directionality_path = PROCESSED_DATA_DIR / "phase10_feature_directionality.json"
    partial_dependence_path = PROCESSED_DATA_DIR / "phase10_partial_dependence.json"
    local_examples_path = PROCESSED_DATA_DIR / "phase10_local_examples.json"
    required = (importance_path, directionality_path, partial_dependence_path, local_examples_path)
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Persisted Phase 10 explainability artifact(s) missing: {missing}")
    return {
        "global_feature_importance": pd.read_csv(importance_path).to_dict(orient="records"),
        "feature_directionality": json.loads(directionality_path.read_text(encoding="utf-8")),
        "partial_dependence_analysis": json.loads(partial_dependence_path.read_text(encoding="utf-8")),
        "persisted_local_examples": json.loads(local_examples_path.read_text(encoding="utf-8")),
        "scientific_warning": (
            "These persisted summaries explain behavior on the rainfall-derived proxy task; "
            "they are not causal or observed-flood explanations."
        ),
    }


def _validate_request(payload: Any, *, scenario: bool = False) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ApiRequestError(HTTPStatus.UNPROCESSABLE_ENTITY, "Request body must be a JSON object.")
    required = {"reference_date", *CURRENT_FEATURES}
    optional = {"model_name"}
    if scenario:
        optional.update({"rainfall_change", "humidity_change"})
    missing = sorted(required - payload.keys())
    extra = sorted(payload.keys() - required - optional)
    if missing:
        raise ApiRequestError(HTTPStatus.UNPROCESSABLE_ENTITY, f"Missing required fields: {missing}")
    if extra:
        raise ApiRequestError(HTTPStatus.UNPROCESSABLE_ENTITY, f"Unexpected fields: {extra}")
    try:
        reference_date = date.fromisoformat(payload["reference_date"])
    except (TypeError, ValueError) as exc:
        raise ApiRequestError(
            HTTPStatus.UNPROCESSABLE_ENTITY,
            "reference_date must be a valid ISO date (YYYY-MM-DD).",
        ) from exc

    model_name = payload.get("model_name", "random_forest")
    if model_name not in MODEL_NAMES:
        raise ApiRequestError(
            HTTPStatus.UNPROCESSABLE_ENTITY,
            f"model_name must be one of: {', '.join(MODEL_NAMES)}.",
        )
    validated: dict[str, Any] = {"reference_date": reference_date, "model_name": model_name}
    for feature, (minimum, maximum) in CURRENT_FEATURES.items():
        value = payload[feature]
        if isinstance(value, bool):
            raise ApiRequestError(HTTPStatus.UNPROCESSABLE_ENTITY, f"{feature} must be a finite number.")
        try:
            numeric = float(value)
        except (TypeError, ValueError) as exc:
            raise ApiRequestError(
                HTTPStatus.UNPROCESSABLE_ENTITY,
                f"{feature} must be a finite number.",
            ) from exc
        if not math.isfinite(numeric) or not minimum <= numeric <= maximum:
            raise ApiRequestError(
                HTTPStatus.UNPROCESSABLE_ENTITY,
                f"{feature} must be between {minimum:g} and {maximum:g}.",
            )
        validated[feature] = numeric

    if scenario:
        for field, minimum, maximum, default in (
            ("rainfall_change", -0.5, 2.0, 0.2),
            ("humidity_change", -0.5, 1.0, 0.1),
        ):
            value = payload.get(field, default)
            if isinstance(value, bool):
                raise ApiRequestError(HTTPStatus.UNPROCESSABLE_ENTITY, f"{field} must be a finite number.")
            try:
                numeric = float(value)
            except (TypeError, ValueError) as exc:
                raise ApiRequestError(
                    HTTPStatus.UNPROCESSABLE_ENTITY,
                    f"{field} must be a finite number.",
                ) from exc
            if not math.isfinite(numeric) or not minimum <= numeric <= maximum:
                raise ApiRequestError(
                    HTTPStatus.UNPROCESSABLE_ENTITY,
                    f"{field} must be between {minimum:g} and {maximum:g}.",
                )
            validated[field] = numeric
    return validated


def _predict(request: dict[str, Any]) -> dict[str, Any]:
    dataset = _load_dataset()
    observation = _build_observation(request, dataset)
    loaded = _load_models()
    metrics = _load_model_metrics()
    training_stats = _training_feature_stats(dataset)
    outputs = {
        name: _prediction_result(name, model, observation, metrics, training_stats)
        for name, model in loaded.items()
    }
    selected_model = loaded[request["model_name"]]
    training = _training_features(dataset)
    explanation_reference = pd.concat([training, observation], ignore_index=True)
    local_explanation = local_prediction_explanation(
        selected_model,
        explanation_reference,
        DEFAULT_FEATURE_COLUMNS,
        sample_index=len(explanation_reference) - 1,
        top_n=5,
    )
    return {
        "reference_date": request["reference_date"].isoformat(),
        "selected_model": request["model_name"],
        "target_type": "rainfall-derived proxy risk",
        "model_outputs": outputs,
        "local_explanation": local_explanation,
        "input_domain": {
            "in_distribution": outputs[request["model_name"]]["in_distribution"],
            "reason": outputs[request["model_name"]]["ood_reason"],
        },
        "calibration_status": "not_evaluated",
        "scientific_warning": SCIENTIFIC_WARNING,
    }


def _scenario(request: dict[str, Any]) -> dict[str, Any]:
    if request["rainfall"] * (1.0 + request["rainfall_change"]) > CURRENT_FEATURES["rainfall"][1]:
        raise ApiRequestError(
            HTTPStatus.UNPROCESSABLE_ENTITY,
            "Rainfall perturbation would exceed the supported same-day rainfall range.",
        )
    if request["humidity"] * (1.0 + request["humidity_change"]) > CURRENT_FEATURES["humidity"][1]:
        raise ApiRequestError(
            HTTPStatus.UNPROCESSABLE_ENTITY,
            "Humidity perturbation would exceed the supported relative-humidity range.",
        )
    dataset = _load_dataset()
    observation = _build_observation(request, dataset).iloc[0]
    model = _load_models()[request["model_name"]]
    rainfall_features = (
        "rainfall",
        "rainfall_1d",
        "rainfall_3d_total",
        "rainfall_7d_total",
        "rainfall_14d_total",
        "rainfall_lag_1d",
        "rainfall_lag_2d",
        "rainfall_lag_3d",
        "rainfall_lag_7d",
    )
    feature_changes = {feature: request["rainfall_change"] for feature in rainfall_features}
    feature_changes["humidity"] = request["humidity_change"]
    result = run_scenario(
        model,
        observation,
        feature_changes,
        feature_columns=DEFAULT_FEATURE_COLUMNS,
        model_name=request["model_name"],
        training_feature_stats=_training_feature_stats(dataset),
        scenario_name="dashboard_controlled_perturbation",
        description=(
            "Rainfall feature family scaled uniformly; same-day humidity perturbed. "
            "Historical rainfall features are scaled as a controlled model stress test."
        ),
        mode="relative",
        include_explanation=False,
    )
    return {
        "reference_date": request["reference_date"].isoformat(),
        "model_name": request["model_name"],
        "baseline_probability": result["baseline_probability"],
        "scenario_probability": result["scenario_probability"],
        "probability_delta": result["probability_delta"],
        "baseline_proxy_risk_band": result["baseline_proxy_risk_band"],
        "scenario_proxy_risk_band": result["scenario_proxy_risk_band"],
        "baseline_in_distribution": result["baseline_in_distribution"],
        "in_distribution": result["in_distribution"],
        "ood_reason": result["ood_reason"],
        "rainfall_change": request["rainfall_change"],
        "humidity_change": request["humidity_change"],
        "calibration_status": "not_evaluated",
        "scientific_warning": SCENARIO_WARNING,
    }


def _metadata(dataset: pd.DataFrame) -> dict[str, Any]:
    first, last = dataset.iloc[0], dataset.iloc[-1]
    return {
        "project_name": "ClimateGuard AI",
        "target_type": "rainfall-derived proxy risk",
        "source": "NASA POWER daily meteorological dataset for Dhaka, Bangladesh",
        "dataset_coverage": {
            "first_reference_date": first["date"].date().isoformat(),
            "last_reference_date": last["date"].date().isoformat(),
            "rows": int(len(dataset)),
        },
        "feature_columns": list(DEFAULT_FEATURE_COLUMNS),
        "editable_inputs": {
            "temperature": {"label": "Temperature", "unit": "°C", "minimum": -90, "maximum": 65},
            "rainfall": {"label": "Rainfall", "unit": "mm/day", "minimum": 0, "maximum": 1000},
            "humidity": {"label": "Relative humidity", "unit": "%", "minimum": 0, "maximum": 100},
            "wind_speed": {"label": "Wind speed", "unit": "m/s", "minimum": 0, "maximum": 100},
            "pressure": {"label": "Surface pressure", "unit": "kPa", "minimum": 50, "maximum": 120},
        },
        "history_method": (
            "Reference dates and lag/rolling features come from the existing processed dataset. "
            "Editing same-day rainfall updates its daily value and the stored 3-, 7-, and 14-day totals "
            "by the observed same-day difference; prior-day features are retained."
        ),
        "training_period": {"start": "2015-01-08", "end": "2021-12-31"},
        "validation_period": {"start": "2022-01-01", "end": "2023-12-31"},
        "test_period": {"start": "2024-01-01", "end": "2024-12-31"},
        "calibration_status": "not_evaluated",
        "scientific_warning": SCIENTIFIC_WARNING,
        "limitations": [
            "The target is a rainfall-derived proxy, not observed flood ground truth.",
            "NASA POWER and BWDB records have no temporal overlap; no fused supervised dataset exists.",
            "Model outputs are proxy risk probabilities, not real-world flood probabilities.",
            "The saved project models have no persisted calibration evaluation; calibration is unverified.",
            "Scenario analysis is a controlled proxy-model perturbation, not a climate projection or flood simulation.",
            "Perfect tree-model scores reflect a target constructed from rainfall features.",
            "This dashboard is a local research/demo interface, not operational flood-warning infrastructure.",
        ],
    }


def _json_default(value: Any) -> Any:
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (np.ndarray,)):
        return value.tolist()
    if isinstance(value, (pd.Timestamp, date)):
        return value.isoformat()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable.")


def _response(
    start_response: Any,
    status: HTTPStatus,
    body: bytes,
    content_type: str,
) -> list[bytes]:
    start_response(
        f"{status.value} {status.phrase}",
        [
            ("Content-Type", content_type),
            ("Content-Length", str(len(body))),
            ("Cache-Control", "no-store"),
        ],
    )
    return [body]


def _json_response(start_response: Any, status: HTTPStatus, payload: Any) -> list[bytes]:
    body = json.dumps(payload, default=_json_default, allow_nan=False).encode("utf-8")
    return _response(start_response, status, body, "application/json; charset=utf-8")


def _read_json_body(environ: dict[str, Any]) -> Any:
    try:
        length = int(environ.get("CONTENT_LENGTH") or "0")
    except ValueError as exc:
        raise ApiRequestError(HTTPStatus.BAD_REQUEST, "Invalid Content-Length header.") from exc
    if length <= 0:
        raise ApiRequestError(HTTPStatus.BAD_REQUEST, "A JSON request body is required.")
    if length > 1_000_000:
        raise ApiRequestError(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "Request body exceeds 1 MB.")
    try:
        return json.loads(environ["wsgi.input"].read(length))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ApiRequestError(HTTPStatus.BAD_REQUEST, "Request body must contain valid JSON.") from exc


def _dispatch(environ: dict[str, Any]) -> tuple[HTTPStatus, Any, str]:
    method = environ["REQUEST_METHOD"].upper()
    path = environ.get("PATH_INFO", "/")
    if method == "GET" and path == "/":
        return HTTPStatus.OK, (WEB_DIR / "index.html").read_bytes(), "text/html; charset=utf-8"

    if method == "GET" and path.startswith("/static/"):
        asset_name = path.removeprefix("/static/")
        if asset_name not in {"dashboard.css", "dashboard.js"}:
            raise ApiRequestError(HTTPStatus.NOT_FOUND, "Static asset not found.")
        asset = STATIC_DIR / asset_name
        content_type = "text/css; charset=utf-8" if asset.suffix == ".css" else "text/javascript; charset=utf-8"
        return HTTPStatus.OK, asset.read_bytes(), content_type

    if method == "GET" and path == "/api/health":
        dataset = _load_dataset()
        loaded = _load_models()
        return HTTPStatus.OK, {
            "status": "ok",
            "loaded_models": list(loaded),
            "dataset_rows": int(len(dataset)),
            "sklearn_runtime": sklearn.__version__,
            "calibration_status": "not_evaluated",
        }, "application/json; charset=utf-8"

    if method == "GET" and path == "/api/models":
        loaded = _load_models()
        metrics = _load_model_metrics()
        missing = [name for name in MODEL_NAMES if name not in metrics]
        if missing:
            raise ValueError(f"Persisted model comparison is missing models: {missing}")
        return HTTPStatus.OK, {
            "models": [
                {
                    "model_name": name,
                    "model_label": MODEL_LABELS[name],
                    "loaded": name in loaded,
                    "validation_metrics": metrics[name]["validation_metrics"],
                    "test_metrics": metrics[name]["test_metrics"],
                    "selected_threshold": metrics[name]["selected_threshold"],
                    "calibration_status": "not_evaluated",
                    "metric_target": "rainfall-derived proxy",
                }
                for name in MODEL_NAMES
            ],
            "source": "Persisted Phase 7 model comparison; metrics are not recalculated by the dashboard.",
            "scientific_warning": SCIENTIFIC_WARNING,
        }, "application/json; charset=utf-8"

    if method == "GET" and path == "/api/metadata":
        return HTTPStatus.OK, _metadata(_load_dataset()), "application/json; charset=utf-8"

    if method == "GET" and path == "/api/reference":
        query = parse_qs(environ.get("QUERY_STRING", ""))
        try:
            reference_date = date.fromisoformat(query["reference_date"][0])
        except (KeyError, IndexError, ValueError) as exc:
            raise ApiRequestError(
                HTTPStatus.UNPROCESSABLE_ENTITY,
                "Provide reference_date as a valid ISO date (YYYY-MM-DD).",
            ) from exc
        return HTTPStatus.OK, _reference_payload(_dataset_row(reference_date)), "application/json; charset=utf-8"

    if method == "GET" and path == "/api/explainability":
        return HTTPStatus.OK, _load_explainability(), "application/json; charset=utf-8"

    if method == "POST" and path in {"/api/predict", "/api/scenario"}:
        is_scenario = path == "/api/scenario"
        request = _validate_request(_read_json_body(environ), scenario=is_scenario)
        payload = _scenario(request) if is_scenario else _predict(request)
        return HTTPStatus.OK, payload, "application/json; charset=utf-8"

    if path.startswith("/api/") and path not in {
        "/api/health", "/api/models", "/api/metadata", "/api/reference",
        "/api/explainability", "/api/predict", "/api/scenario",
    }:
        raise ApiRequestError(HTTPStatus.NOT_FOUND, "API endpoint not found.")
    if path in {"/api/health", "/api/models", "/api/metadata", "/api/reference", "/api/explainability"}:
        raise ApiRequestError(HTTPStatus.METHOD_NOT_ALLOWED, "Method not allowed.")
    raise ApiRequestError(HTTPStatus.NOT_FOUND, "Page not found.")


def app(environ: dict[str, Any], start_response: Any) -> list[bytes]:
    try:
        status, payload, content_type = _dispatch(environ)
        if content_type.startswith("application/json"):
            return _json_response(start_response, status, payload)
        return _response(start_response, status, payload, content_type)
    except ApiRequestError as error:
        return _json_response(start_response, error.status, {"detail": str(error)})
    except (FileNotFoundError, OSError, ValueError, TypeError, KeyError) as error:
        return _json_response(
            start_response,
            HTTPStatus.INTERNAL_SERVER_ERROR,
            {"detail": f"Dashboard could not complete the request: {error}"},
        )


def serve() -> None:
    is_render = os.environ.get("RENDER", "").lower() == "true"
    host = "0.0.0.0" if is_render else "127.0.0.1"
    port = int(os.environ.get("PORT", "8000"))
    with make_server(host, port, app) as server:
        print(f"ClimateGuard AI dashboard listening on {host}:{port}")
        server.serve_forever()


if __name__ == "__main__":
    serve()

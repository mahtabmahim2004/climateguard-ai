from __future__ import annotations

import io
import json
from typing import Any
from urllib.parse import urlencode

from wsgiref.util import setup_testing_defaults

import climateguard.webapp as webapp
from climateguard.webapp import app


def request(
    path: str,
    *,
    method: str = "GET",
    body: dict[str, Any] | None = None,
    query: dict[str, str] | None = None,
) -> tuple[int, Any, str]:
    environ: dict[str, Any] = {}
    setup_testing_defaults(environ)
    if query:
        path = f"{path}?{urlencode(query)}"
    raw_body = json.dumps(body).encode("utf-8") if body is not None else b""
    path_info, _, query_string = path.partition("?")
    environ.update(
        {
            "REQUEST_METHOD": method,
            "PATH_INFO": path_info,
            "QUERY_STRING": query_string,
            "CONTENT_LENGTH": str(len(raw_body)),
            "CONTENT_TYPE": "application/json",
            "wsgi.input": io.BytesIO(raw_body),
        }
    )
    status_headers: list[Any] = []

    def start_response(status: str, headers: list[tuple[str, str]]) -> None:
        status_headers.extend([status, headers])

    body_bytes = b"".join(app(environ, start_response))
    status_code = int(status_headers[0].split(" ", 1)[0])
    content_type = dict(status_headers[1])["Content-Type"]
    if content_type.startswith("application/json"):
        return status_code, json.loads(body_bytes), content_type
    return status_code, body_bytes.decode("utf-8"), content_type


def valid_inputs() -> dict[str, Any]:
    return {
        "reference_date": "2024-12-31",
        "temperature": 20.0,
        "rainfall": 12.0,
        "humidity": 75.0,
        "wind_speed": 2.5,
        "pressure": 100.8,
        "model_name": "random_forest",
    }


def test_health_loads_saved_models_and_dataset() -> None:
    status, body, _ = request("/api/health")
    assert status == 200
    assert body["status"] == "ok"
    assert set(body["loaded_models"]) == {
        "logistic_regression",
        "random_forest",
        "gradient_boosting",
    }
    assert body["dataset_rows"] == 3646
    assert body["calibration_status"] == "not_evaluated"


def test_prediction_returns_all_model_outputs_and_local_explanation() -> None:
    status, body, _ = request("/api/predict", method="POST", body=valid_inputs())
    assert status == 200
    assert body["target_type"] == "rainfall-derived proxy risk"
    assert set(body["model_outputs"]) == {
        "logistic_regression",
        "random_forest",
        "gradient_boosting",
    }
    assert 0 <= body["model_outputs"]["random_forest"]["probability"] <= 1
    assert body["model_outputs"]["random_forest"]["calibration_status"] == "not_evaluated"
    assert body["local_explanation"]["top_contributing_features"]
    assert "not an observed flood prediction" in body["scientific_warning"]


def test_prediction_rejects_out_of_range_or_missing_history_date() -> None:
    invalid_value = valid_inputs()
    invalid_value["rainfall"] = -1
    invalid_status, _, _ = request("/api/predict", method="POST", body=invalid_value)
    unavailable_date = valid_inputs()
    unavailable_date["reference_date"] = "2015-01-01"
    unavailable_status, unavailable_body, _ = request(
        "/api/predict",
        method="POST",
        body=unavailable_date,
    )
    assert invalid_status == 422
    assert unavailable_status == 422
    assert "processed NASA POWER" in unavailable_body["detail"]


def test_model_metadata_and_explainability_endpoints_use_saved_artifacts() -> None:
    models_status, models, _ = request("/api/models")
    metadata_status, metadata, _ = request("/api/metadata")
    explanation_status, explanation, _ = request("/api/explainability")
    reference_status, reference, _ = request(
        "/api/reference",
        query={"reference_date": "2024-12-31"},
    )
    assert models_status == metadata_status == 200
    assert explanation_status == reference_status == 200
    assert len(models["models"]) == 3
    assert models["source"].startswith("Persisted Phase 7")
    assert metadata["calibration_status"] == "not_evaluated"
    assert metadata["dataset_coverage"]["rows"] == 3646
    assert explanation["global_feature_importance"]
    assert reference["reference_date"] == "2024-12-31"


def test_scenario_endpoint_reuses_phase11_scenario_engine() -> None:
    inputs = valid_inputs()
    inputs.update({"rainfall_change": 0.2, "humidity_change": -0.1})
    status, body, _ = request("/api/scenario", method="POST", body=inputs)
    assert status == 200
    assert 0 <= body["baseline_probability"] <= 1
    assert 0 <= body["scenario_probability"] <= 1
    assert body["probability_delta"] == body["scenario_probability"] - body["baseline_probability"]
    assert body["calibration_status"] == "not_evaluated"
    assert "not real flood warnings" in body["scientific_warning"]


def test_scenario_rejects_perturbations_outside_physical_input_domain() -> None:
    inputs = valid_inputs()
    inputs.update({"humidity": 100, "humidity_change": 0.1})
    status, body, _ = request("/api/scenario", method="POST", body=inputs)
    assert status == 422
    assert "humidity perturbation" in body["detail"].lower()


def test_dashboard_serves_browser_ui_and_assets() -> None:
    page_status, page, page_type = request("/")
    script_status, script, script_type = request("/static/dashboard.js")
    style_status, style, style_type = request("/static/dashboard.css")
    assert page_status == script_status == style_status == 200
    assert "ClimateGuard AI" in page
    assert "text/html" in page_type
    assert 'const API = "/api"' in script
    assert "javascript" in script_type
    assert ":root{" in style
    assert "text/css" in style_type
    assert "fonts.googleapis.com" not in style


def test_local_server_configuration_preserves_loopback_and_default_port(monkeypatch: Any) -> None:
    monkeypatch.delenv("RENDER", raising=False)
    monkeypatch.delenv("PORT", raising=False)
    captured: list[tuple[str, int]] = []

    class FakeServer:
        def __enter__(self) -> FakeServer:
            return self

        def __exit__(self, *args: Any) -> None:
            return None

        def serve_forever(self) -> None:
            return None

    def fake_make_server(host: str, port: int, application: Any) -> FakeServer:
        captured.append((host, port))
        return FakeServer()

    monkeypatch.setattr(webapp, "make_server", fake_make_server)
    webapp.serve()
    assert captured == [("127.0.0.1", 8000)]


def test_render_server_uses_public_bind_and_render_port(monkeypatch: Any) -> None:
    monkeypatch.setenv("RENDER", "true")
    monkeypatch.setenv("PORT", "10000")
    captured: list[tuple[str, int]] = []

    class FakeServer:
        def __enter__(self) -> FakeServer:
            return self

        def __exit__(self, *args: Any) -> None:
            return None

        def serve_forever(self) -> None:
            return None

    def fake_make_server(host: str, port: int, application: Any) -> FakeServer:
        captured.append((host, port))
        return FakeServer()

    monkeypatch.setattr(webapp, "make_server", fake_make_server)
    webapp.serve()
    assert captured == [("0.0.0.0", 10000)]

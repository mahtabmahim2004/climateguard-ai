const API = "/api";
const MODEL_LABELS = {
  logistic_regression: "Logistic Regression",
  random_forest: "Random Forest",
  gradient_boosting: "Gradient Boosting",
};
const COLORS = ["var(--mint)", "var(--blue)", "var(--violet)"];
const state = { metadata: null, models: [], explainability: null, reference: null, lastInputs: null };

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const safeNumber = (value, digits = 3) => Number(value).toFixed(digits);
const escapeHtml = value => String(value).replace(/[&<>"']/g, character => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
})[character]);

async function api(path, options = {}) {
  const response = await fetch(`${API}${path}`, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail || body);
    throw new Error(message || `Request failed (${response.status}).`);
  }
  return body;
}

function showPage(pageName) {
  const knownPage = document.getElementById(`page-${pageName}`) ? pageName : "overview";
  $$(".page").forEach(page => page.classList.toggle("active", page.id === `page-${knownPage}`));
  $$(".nav-link").forEach(link => link.classList.toggle("active", link.dataset.page === knownPage));
  const active = $(`.nav-link[data-page="${knownPage}"]`);
  $("#page-crumb").textContent = active ? active.textContent.trim() : "Overview";
  if (knownPage === "scenarios") syncScenarioDate();
}

function navigate() {
  showPage(location.hash.slice(1) || "overview");
}

function chartRows(models) {
  return models.map(model => ({
    name: model.model_label,
    accuracy: model.test_metrics.accuracy,
    f1: model.test_metrics.f1_score,
    auc: model.test_metrics.roc_auc,
  }));
}

function renderMetricChart(target, models) {
  const rows = chartRows(models);
  target.innerHTML = rows.map(row => `
    <div class="model-chart-row">
      <span>${escapeHtml(row.name)}</span>
      <div class="triple-bars">
        <i style="width:${Math.max(0, Math.min(100, row.accuracy * 100))}%;background:var(--mint)"></i>
        <i style="width:${Math.max(0, Math.min(100, row.f1 * 100))}%;background:var(--blue)"></i>
        <i style="width:${Math.max(0, Math.min(100, row.auc * 100))}%;background:var(--violet)"></i>
      </div>
      <output>${safeNumber(row.accuracy, 2)}</output>
    </div>`).join("");
}

function renderModels() {
  const models = state.models;
  if (!models.length) return;
  renderMetricChart($("#overview-model-chart"), models);
  renderMetricChart($("#models-chart"), models);
  $("#models-table").innerHTML = `<table><thead><tr><th>MODEL</th><th>ACCURACY</th><th>PRECISION</th><th>RECALL</th><th>F1 SCORE</th><th>ROC-AUC</th><th>THRESHOLD</th></tr></thead><tbody>${models.map(model => {
    const metrics = model.test_metrics;
    return `<tr><td>${escapeHtml(model.model_label)}</td><td class="score-cell">${safeNumber(metrics.accuracy, 4)}</td><td>${safeNumber(metrics.precision, 4)}</td><td>${safeNumber(metrics.recall, 4)}</td><td class="score-cell">${safeNumber(metrics.f1_score, 4)}</td><td>${safeNumber(metrics.roc_auc, 4)}</td><td>${safeNumber(model.selected_threshold, 2)}</td></tr>`;
  }).join("")}</tbody></table>`;
}

function renderImportance(rows) {
  const top = rows.slice(0, 10);
  const max = Math.max(...top.map(row => Number(row.importance)), 0.000001);
  $("#importance-chart").innerHTML = top.map(row => `<div class="importance-row"><span title="${escapeHtml(row.feature)}">${escapeHtml(row.feature)}</span><div class="importance-track"><i style="width:${Number(row.importance) / max * 100}%"></i></div><output>${safeNumber(row.importance, 3)}</output></div>`).join("");
}

function renderDirectionality(rows) {
  $("#directionality-list").innerHTML = rows.slice(0, 14).map(row => {
    const direction = row.direction || "mixed";
    const percent = Number(row.correlation_with_risk_probability);
    return `<div class="direction-row"><span>${escapeHtml(row.feature)}</span><output class="${direction}">${percent >= 0 ? "+" : ""}${safeNumber(percent, 2)} · ${escapeHtml(direction)}</output></div>`;
  }).join("");
}

function renderPdp(rows) {
  const rainfall = rows.find(row => row.feature === "rainfall");
  if (!rainfall || rainfall.grid_values.length < 2) {
    $("#pdp-chart").textContent = "No persisted rainfall response curve is available.";
    return;
  }
  const width = 700, height = 190, left = 48, right = 16, top = 12, bottom = 30;
  const values = rainfall.partial_dependence_values.map(Number);
  const min = Math.min(...values), max = Math.max(...values);
  const span = Math.max(max - min, 0.000001);
  const points = values.map((value, index) => {
    const x = left + index * (width - left - right) / Math.max(1, values.length - 1);
    const y = top + (max - value) * (height - top - bottom) / span;
    return [x, y];
  });
  const line = points.map((point, index) => `${index ? "L" : "M"}${point[0]},${point[1]}`).join(" ");
  const area = `${line} L${points.at(-1)[0]},${height - bottom} L${points[0][0]},${height - bottom} Z`;
  const firstX = Number(rainfall.grid_values[0]), lastX = Number(rainfall.grid_values.at(-1));
  $("#pdp-chart").innerHTML = `<svg class="pdp-svg" viewBox="0 0 ${width} ${height}" role="img" aria-label="Persisted rainfall partial-dependence-style curve">
    <defs><linearGradient id="pdpFill" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="var(--mint)" stop-opacity=".22"/><stop offset="1" stop-color="var(--mint)" stop-opacity="0"/></linearGradient></defs>
    <line class="grid-line" x1="${left}" y1="${top + 12}" x2="${width - right}" y2="${top + 12}"/><line class="grid-line" x1="${left}" y1="${(height + top - bottom) / 2}" x2="${width - right}" y2="${(height + top - bottom) / 2}"/><line class="grid-line" x1="${left}" y1="${height - bottom}" x2="${width - right}" y2="${height - bottom}"/>
    <text x="2" y="${top + 15}">${safeNumber(max, 2)}</text><text x="2" y="${height - bottom}">${safeNumber(min, 2)}</text><path class="area" d="${area}"/><path class="curve" d="${line}"/>${points.map(point => `<circle cx="${point[0]}" cy="${point[1]}" r="3"/>`).join("")}<text x="${left}" y="${height - 5}">${safeNumber(firstX, 0)} mm/day</text><text x="${width - right}" y="${height - 5}" text-anchor="end">${safeNumber(lastX, 0)} mm/day</text>
  </svg>`;
}

async function loadReference(date, fillForm = true) {
  if (!date) return null;
  const record = await api(`/reference?reference_date=${encodeURIComponent(date)}`);
  state.reference = record;
  if (fillForm) {
    for (const feature of ["temperature", "rainfall", "humidity", "wind_speed", "pressure"]) {
      $(`#${feature}`).value = record[feature];
    }
  }
  state.lastInputs = { ...record, model_name: $("#prediction-model").value };
  return record;
}

function formInputs(form) {
  const data = new FormData(form);
  return {
    reference_date: data.get("reference_date"),
    temperature: Number(data.get("temperature")),
    rainfall: Number(data.get("rainfall")),
    humidity: Number(data.get("humidity")),
    wind_speed: Number(data.get("wind_speed")),
    pressure: Number(data.get("pressure")),
    model_name: data.get("model_name"),
  };
}

function showError(element, error) {
  element.textContent = error.message || String(error);
  element.classList.remove("hidden");
}

function riskText(probability, band) {
  return `${escapeHtml(band)} proxy-risk band`;
}

function renderPrediction(result) {
  const selected = result.model_outputs[result.selected_model];
  const outputs = Object.entries(result.model_outputs);
  const explanation = result.local_explanation.top_contributing_features || [];
  const maxEffect = Math.max(...explanation.map(item => Math.abs(item.effect_on_probability)), 0.000001);
  $("#prediction-results").innerHTML = `
    <div class="result-summary"><div class="eyebrow">SELECTED MODEL · ${escapeHtml(selected.model_label)}</div><h3>Proxy risk probability</h3><div class="probability">${(selected.probability * 100).toFixed(1)}%</div><div><span class="risk-tag">● ${riskText(selected.probability, selected.proxy_risk_band)}</span></div></div>
    <div class="domain-row"><span class="domain-mark">${selected.in_distribution ? "●" : "!"}</span><strong>${selected.in_distribution ? "Within" : "Outside"} training-feature distribution</strong><span>${escapeHtml(selected.ood_reason)}</span></div>
    <div class="model-output-grid">${outputs.map(([name, output]) => `<article class="model-output"><div class="model-output-top"><strong>${escapeHtml(output.model_label)}</strong><span>${(output.probability * 100).toFixed(1)}%</span></div><div class="prob-track"><span style="width:${output.probability * 100}%"></span></div><div class="model-output-foot"><span>${riskText(output.probability, output.proxy_risk_band)}</span><span>calibration: not evaluated</span></div></article>`).join("")}</div>
    <article class="explanation-card"><h3>Local explanation · selected model</h3>${explanation.map(item => `<div class="contribution-row"><span>${escapeHtml(item.feature)}</span><div class="contribution-track"><i style="width:${Math.abs(item.effect_on_probability) / maxEffect * 100}%;background:${item.effect_on_probability < 0 ? "var(--blue)" : "var(--mint)"}"></i></div><output>${item.effect_on_probability >= 0 ? "+" : ""}${safeNumber(item.effect_on_probability, 3)}</output></div>`).join("")}<p class="form-footnote">${escapeHtml(result.scientific_warning)}</p></article>`;
}

async function onPredict(event) {
  event.preventDefault();
  const form = event.currentTarget, button = $(".submit-button", form), error = $("#prediction-error");
  error.classList.add("hidden");
  button.disabled = true;
  $("span:first-child", button).textContent = "Running models…";
  try {
    const inputs = formInputs(form);
    const result = await api("/predict", { method: "POST", body: JSON.stringify(inputs) });
    state.lastInputs = inputs;
    renderPrediction(result);
  } catch (cause) {
    showError(error, cause);
  } finally {
    button.disabled = false;
    $("span:first-child", button).textContent = "Run prediction";
  }
}

async function onScenario(event) {
  event.preventDefault();
  const form = event.currentTarget, button = $(".submit-button", form), error = $("#scenario-error");
  error.classList.add("hidden");
  button.disabled = true;
  $("span:first-child", button).textContent = "Evaluating scenario…";
  try {
    const date = $("#scenario-date").value;
    const current = state.lastInputs && state.lastInputs.reference_date === date
      ? state.lastInputs
      : await loadReference(date, true);
    const request = {
      ...current,
      reference_date: date,
      model_name: $("#scenario-model").value,
      rainfall_change: Number($("#rainfall-change").value) / 100,
      humidity_change: Number($("#humidity-change").value) / 100,
    };
    const result = await api("/scenario", { method: "POST", body: JSON.stringify(request) });
    $("#scenario-results").innerHTML = `<article class="scenario-result"><div class="eyebrow">${escapeHtml(MODEL_LABELS[result.model_name])} · ${escapeHtml(result.reference_date)}</div><h3>Controlled scenario response</h3><div class="scenario-values"><div class="scenario-value"><small>BASELINE PROXY PROBABILITY</small><strong>${(result.baseline_probability * 100).toFixed(1)}%</strong></div><div class="scenario-value"><small>SCENARIO PROXY PROBABILITY</small><strong>${(result.scenario_probability * 100).toFixed(1)}%</strong></div><div class="scenario-value"><small>PROBABILITY DELTA</small><strong class="delta-value">${result.probability_delta >= 0 ? "+" : ""}${(result.probability_delta * 100).toFixed(2)} pp</strong></div><div class="scenario-value"><small>INPUT DOMAIN</small><strong>${result.in_distribution ? "Within range" : "OOD flag"}</strong></div></div><div class="scenario-band"><span>Baseline band <strong>${escapeHtml(result.baseline_proxy_risk_band)}</strong></span><span>Scenario band <strong>${escapeHtml(result.scenario_proxy_risk_band)}</strong></span></div><p class="scenario-foot">Rainfall feature family: ${result.rainfall_change >= 0 ? "+" : ""}${(result.rainfall_change * 100).toFixed(0)}% · Same-day humidity: ${result.humidity_change >= 0 ? "+" : ""}${(result.humidity_change * 100).toFixed(0)}%<br>${escapeHtml(result.ood_reason)}<br>${escapeHtml(result.scientific_warning)}</p></article>`;
  } catch (cause) {
    showError(error, cause);
  } finally {
    button.disabled = false;
    $("span:first-child", button).textContent = "Run scenario response";
  }
}

async function handleDateChange(event) {
  try {
    await loadReference(event.currentTarget.value, true);
    $("#scenario-date").value = event.currentTarget.value;
  } catch (cause) {
    showError($("#prediction-error"), cause);
  }
}

function syncScenarioDate() {
  if (state.lastInputs) $("#scenario-date").value = state.lastInputs.reference_date;
}

async function initialize() {
  try {
    const [health, metadata, models, explainability] = await Promise.all([
      api("/health"), api("/metadata"), api("/models"), api("/explainability"),
    ]);
    state.metadata = metadata;
    state.models = models.models;
    state.explainability = explainability;
    $("#sidebar-health").textContent = `${health.loaded_models.length} models · API healthy`;
    $("#runtime-label").textContent = `API healthy · sklearn ${health.sklearn_runtime}`;
    $("#metric-rows").textContent = Number(metadata.dataset_coverage.rows).toLocaleString();
    $("#coverage-summary").textContent = `${metadata.dataset_coverage.first_reference_date.slice(0, 4)} — ${metadata.dataset_coverage.last_reference_date.slice(0, 4)}`;
    $("#prediction-date").min = metadata.dataset_coverage.first_reference_date;
    $("#prediction-date").max = metadata.dataset_coverage.last_reference_date;
    $("#scenario-date").min = metadata.dataset_coverage.first_reference_date;
    $("#scenario-date").max = metadata.dataset_coverage.last_reference_date;
    $("#prediction-date").value = metadata.dataset_coverage.last_reference_date;
    $("#scenario-date").value = metadata.dataset_coverage.last_reference_date;
    renderModels();
    renderImportance(explainability.global_feature_importance);
    renderDirectionality(explainability.feature_directionality);
    renderPdp(explainability.partial_dependence_analysis);
    await loadReference(metadata.dataset_coverage.last_reference_date);
  } catch (cause) {
    $("#sidebar-health").textContent = "API unavailable";
    $("#runtime-label").textContent = "API unavailable";
    showError($("#global-error"), cause);
  }
}

$("#prediction-form").addEventListener("submit", onPredict);
$("#scenario-form").addEventListener("submit", onScenario);
$("#prediction-date").addEventListener("change", handleDateChange);
$("#rainfall-change").addEventListener("input", event => {
  const value = Number(event.currentTarget.value);
  $("#rainfall-output").textContent = `${value > 0 ? "+" : ""}${value}%`;
});
$("#humidity-change").addEventListener("input", event => {
  const value = Number(event.currentTarget.value);
  $("#humidity-output").textContent = `${value > 0 ? "+" : ""}${value}%`;
});
$("#theme-toggle").addEventListener("click", () => {
  const theme = document.documentElement.dataset.theme === "light" ? "dark" : "light";
  document.documentElement.dataset.theme = theme;
  localStorage.setItem("climateguard-theme", theme);
});
document.documentElement.dataset.theme = localStorage.getItem("climateguard-theme") || "dark";
window.addEventListener("hashchange", navigate);
window.addEventListener("DOMContentLoaded", () => { navigate(); initialize(); });

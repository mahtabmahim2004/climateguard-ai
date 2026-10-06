# ClimateGuard AI

**A research-oriented Bangladesh rainfall-risk proxy modeling project**

ClimateGuard AI is an end-to-end, reproducible environmental machine-learning project built around real NASA POWER daily meteorological data for Dhaka, Bangladesh. It demonstrates source-aware acquisition, temporal feature engineering, leakage-conscious chronological evaluation, model interpretation, uncertainty/OOD checks, controlled robustness and scenario analysis, and explicit scientific safeguards. Its classifier learns a transparent rainfall-derived proxy label; it does **not** predict observed floods or provide an operational flood warning.

> **Scientific scope:** Every model metric, probability, risk band, explanation, and scenario output in this repository refers to the rainfall-derived proxy task only. It is not validated flood-event performance.

## Problem statement and scientific objective

Bangladesh experiences serious flood hazards, but a meteorological time series without independently verified flood-event labels cannot support a supervised claim about observed flooding. This project makes that constraint explicit. Its objective is to build and audit a reproducible proxy-modeling workflow, examine what the models learn about a rainfall rule, and preserve the boundary between meteorological observations, hydrological observations, proxy labels, model outputs, and real-world flood outcomes.

The target `flood_risk_proxy` is **1** when the 7-day rainfall total is at least 60 mm and same-day rainfall is at least 10 mm; it is **0** otherwise. It is defined from rainfall, not from observed flood reports, BWDB water levels, or an official flood threshold. Rainfall and rolling-rainfall inputs are also model features, so strong model scores primarily show that the models can reproduce this constructed rule. They are not evidence of flood forecasting skill.

## Architecture and pipeline

1. **Acquire and preserve source data.** Retain daily NASA POWER observations and a separate, limited BWDB station snapshot with provenance and quality reports.
2. **Validate and prepare.** Normalize the source schema, validate dates and values, compute past-only rolling and lag features, then construct the documented rainfall proxy.
3. **Align sources without manufacturing overlap.** Compare NASA POWER and BWDB coverage. Since their available dates do not overlap, keep the datasets separate and do not create a fused supervised dataset.
4. **Train and evaluate baselines.** Fit preprocessing and classical classifiers using a strict chronological train/validation/test design.
5. **Analyze model behavior.** Produce proxy-task feature explanations, robustness/stability checks, OOD assessments, and controlled input-perturbation scenarios.
6. **Audit reproducibility and scientific scope.** Inventory artifacts, verify target/split/source constraints, check saved-model compatibility, and retain explicit WARNs for evidence gaps.

The implementation is under `src/climateguard/`; phase-specific research notes and data definitions are documented in the project root.

## Data sources and coverage

### NASA POWER — meteorological modeling source

- Daily Dhaka point at latitude 23.8103, longitude 90.4125.
- Coverage: **2015-01-01 through 2024-12-31** (3,653 source rows).
- Variables: temperature (`T2M`), corrected precipitation (`PRECTOTCORR`), relative humidity (`RH2M`), wind speed (`WS2M`), and surface pressure (`PS`).
- The source CSV is retained under `data/raw/`; the corresponding quality report records its schema, date coverage, and missing-value checks.
- After rolling/lag feature construction and removal of rows without required history, `data/processed/flood_model_dataset.csv` contains **3,646 rows**, dated 2015-01-08 through 2024-12-31.

### BWDB — separate observed hydrology source

- One station: SW42 / Dhaka_Mill Barrack on the Buriganga River.
- Available snapshot: **2026-08-01 through 2026-08-31** (31 observations).
- The preserved raw HTML snapshot and the cleaned/canonical tables agree row-for-row on date, water level, and station metadata.
- NASA POWER ends in 2024 and this BWDB snapshot begins in 2026: there is **no temporal overlap**. BWDB observations are not proxy labels, are not merged into the modeling data, and do not establish official flood/no-flood ground truth or a flood threshold.
- Local agreement with the retained snapshot does not independently authenticate the remote source or prove historical handling before that snapshot was saved.

## Feature engineering and target

The 22 model inputs combine:

- Meteorological measurements: temperature, rainfall, humidity, wind speed, and pressure.
- Rainfall history: daily/rolling totals and lagged rainfall.
- Lagged meteorology: selected temperature, humidity, wind, and pressure values.
- Calendar descriptors: month, day of year, and day of week.

Rolling and lag features use current/past observations. Initial rows without the necessary feature history are excluded. The target is the rainfall rule described above; the rainfall variables that define it are present among the predictors. Therefore, this is a proxy-rule modeling exercise, not an independent flood-event prediction experiment.

## Models and temporal evaluation

The repository evaluates Logistic Regression, Random Forest, and Gradient Boosting using the persisted pipeline artifacts in `data/processed/models/`. Train-only preprocessing is wrapped with the estimators in scikit-learn pipelines.

| Split | Dates | Rows |
|---|---|---:|
| Train | 2015-01-08 – 2021-12-31 | 2,550 |
| Validation | 2022-01-01 – 2023-12-31 | 730 |
| Test | 2024-01-01 – 2024-12-31 | 366 |

The periods are chronological and non-overlapping. Validation supports model/threshold analysis; the 2024 test period remains a separate held-out evaluation period.

### Recorded proxy-task results

The persisted Phase 7 comparison reports these held-out test metrics:

| Model | Accuracy | F1 | ROC-AUC |
|---|---:|---:|---:|
| Logistic Regression | 0.9399 | 0.8514 | 0.9884 |
| Random Forest | 1.0000 | 1.0000 | 1.0000 |
| Gradient Boosting | 1.0000 | 1.0000 | 1.0000 |

These are scores against the constructed rainfall proxy. In particular, perfect tree-model scores are consistent with learning a label directly defined by rainfall features; they must not be presented as flood-prediction performance or evidence of real-world generalization.

## Calibration, uncertainty, and robustness

- **Calibration:** Utilities implement sigmoid/isotonic calibration and Brier/log-loss/reliability metrics; tests exercise them on synthetic fixtures. The repository has no persisted model-specific calibration evaluation for the saved project models. Calibration of project-model probabilities is therefore **unverified**. New scenario evaluations default to `not_evaluated`; `well_calibrated` strings in existing Phase 11 outputs are legacy default metadata, not measurement evidence.
- **Uncertainty and OOD:** The project exposes proxy-risk bands and a feature-distribution-based in/out-of-distribution check. OOD is a descriptive input-distribution flag, not a confidence interval, safety assessment, or flood warning.
- **Robustness and stability:** Phase 9 utilities and tests examine controlled perturbations and temporal/model stability. Their interpretation is limited to the proxy-task model and available data.
- **Thresholds:** Model decision thresholds are analysis choices for the proxy label, not official flood or warning thresholds.

## Explainability and scenario analysis

Phase 10 artifacts include global and permutation importance, directionality, partial-dependence-style summaries, local examples, and a trust report. These describe model behavior for the rainfall proxy; they do not establish causality.

Phase 11 performs controlled perturbations to meteorological model inputs and records changes in proxy-model probabilities, risk bands, explanations, and OOD status. It is **model stress testing**, not an official climate scenario, climate projection, hydrological simulation, flood forecast, or warning.

## Reproducibility and runtime

The project pins NumPy 2.1.3, pandas 2.2.3, scikit-learn 1.6.1, Matplotlib 3.9.2, seaborn 0.13.2, and pytest 8.3.3 in `requirements.txt`. The validated local runtime is Python 3.12.10; no Python-version constraint is declared in package metadata. Pytest uses a project-local temporary base directory on Windows.

The persisted logistic regression, random forest, and gradient boosting joblib pipelines each contain scikit-learn 1.6.1 metadata and load under the pinned 1.6.1 runtime without `InconsistentVersionWarning`. The separate global environment previously failed to load a `ColumnTransformer` due to `_RemainderColsList`; use the pinned project environment. This supports reproducibility in the tested project runtime, not byte-for-byte identity across arbitrary environments.

Phase 12 checks dataset/schema/target/split/source invariants, repeatable dataset fingerprints, artifact presence, scientific guardrails, and saved-model loadability. Its three scientific WARNs remain visible because external BWDB authenticity and pre-snapshot date/interpolation history cannot be established from local files. Calibration also remains WARN because project-model calibration results are not persisted. None is silently changed to PASS.

## Project structure

```text
.
├── data/
│   ├── raw/                 # Preserved source inputs
│   ├── processed/           # Datasets, model outputs, audit/evaluation reports
│   └── external/            # Dataset/source manifest
├── notebooks/               # EDA template
├── scripts/                 # Project scripts
├── src/climateguard/
│   ├── data/                # Ingestion, cleaning, coverage, alignment
│   ├── features/            # Meteorological/hydrological features
│   ├── models/              # Training, evaluation, interpretation, scenarios
│   └── validation/          # Reproducibility and scientific audit
├── tests/                   # Unit and phase acceptance tests
├── PHASE*.md                # Phase-specific methods and limitations
├── requirements.txt
└── pytest.ini
```

Local virtual environments, caches, and temporary test data are not project deliverables and should not be committed.

## Setup

From the repository root, using PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

The complete source datasets and saved model artifacts are local project inputs/outputs; the raw and processed dataset directories are ignored by `.gitignore` by default. Ensure the required local artifacts are present before running validation.

## Validation

Run the final documented test and compile checks from the project root:

```powershell
$env:PATH = "$PWD\.venv\Scripts;$env:PATH"
$env:PYTHONPATH = 'src'
python -m pytest -q
python -m compileall src
```

For the focused Phase 12 integration acceptance tests:

```powershell
$env:PATH = "$PWD\.venv\Scripts;$env:PATH"
$env:PYTHONPATH = 'src'
python -m pytest -q tests/test_phase12_reproducibility.py
```

The final completion evidence is recorded in `data/processed/final_project_completion_report.json`; Phase 12 audit and reproducibility reports remain alongside it.

## Responsible science and limitations

- The target is a rainfall-derived proxy, not observed flood ground truth.
- Authoritative flood labels and validated flood thresholds are unavailable.
- NASA POWER and BWDB coverage do not overlap; no fused supervised dataset exists.
- BWDB coverage is one station and a limited 31-day snapshot, separate from model training.
- External source authenticity and transformations before the preserved BWDB raw snapshot cannot be independently verified.
- Calibration evidence for persisted project models is absent; do not imply calibrated probabilities.
- A classifier probability is a probability for the proxy task, not a real-world flood probability. `LOW`/`MEDIUM`/`HIGH` are proxy-risk bands only.
- Explanations are descriptive, not causal. Scenario outputs are controlled model perturbations, not physical flood simulations or official climate scenarios.
- Perfect tree-model scores reflect prediction of a target constructed from rainfall features and do not establish flood forecasting skill.
- This repository is not operational flood-warning infrastructure and must not be used as a substitute for official guidance.

ClimateGuard AI follows responsible-science principles: preserve provenance, separate observations from derived labels and model outputs, avoid unsupported causal/operational claims, report evidence gaps, and retain warnings when historical or external evidence is insufficient.

## Final project status

**Final phase: Phase 13.** Phases 1–12 are retained with their scientific results and artifacts. The final completion audit and validation evidence are recorded in `data/processed/final_project_completion_report.json`.

**CLIMATEGUARD AI — PROJECT COMPLETE**  
**FINAL PHASE: PHASE 13**  
**NO FURTHER PROJECT PHASES.**

## Local research dashboard

The project also includes a local browser interface over the **existing** Phase 7 model pipelines and Phase 9–11 analysis utilities/artifacts. It does not retrain models, create flood labels, or add an operational warning service. Prediction and scenario outputs remain rainfall-derived proxy risk.

Install dependencies in the project environment, then from the repository root start the API and dashboard together:

```powershell
$env:PATH = "$PWD\.venv\Scripts;$env:PATH"
$env:PYTHONPATH = 'src'
python -m climateguard.webapp
```

Open <http://127.0.0.1:8000> for the dashboard. The standard-library WSGI API serves the static browser assets; a separate web-framework install, JavaScript toolchain, or build step is not required.

Dashboard endpoints are `GET /api/health`, `GET /api/models`, `GET /api/metadata`, `GET /api/reference?reference_date=YYYY-MM-DD`, `GET /api/explainability`, `POST /api/predict`, and `POST /api/scenario`. Available reference dates and their lag/rolling history come from `data/processed/flood_model_dataset.csv`. The interface edits only same-day meteorological values; it retains the selected real record's prior-day history rather than inventing lagged inputs. Rainfall edits update current rainfall and the stored rolling totals by the change in same-day rainfall. Scenario controls uniformly perturb the rainfall feature family and perturb same-day humidity, using the existing Phase 11 scenario engine.

The dashboard displays persisted Phase 7 evaluation metrics and Phase 10 explainability artifacts; it does not recalculate evaluation scores. Local outputs are proxy-model probability and scenario response, not real-world flood probability, physical flood simulations, climate projections, or official warnings. Persisted calibration evaluation for the saved project models is absent, so calibration is shown as **not evaluated**. See [Responsible science and limitations](#responsible-science-and-limitations) before interpreting any output.

Focused API tests: `python -m pytest -q tests/test_web_api.py`.

### Windows double-click launcher

For a local convenience launcher, double-click `scripts\create_climateguard_shortcut.vbs` once to create a **ClimateGuard AI** shortcut on the current Windows user's Desktop. The shortcut uses the repository-relative `scripts\start_climateguard_hidden.vbs` wrapper, which launches `scripts\start_climateguard.bat` without leaving its command window in front. The BAT resolves the project root from its own location, uses only the existing `.venv\Scripts\python.exe`, sets `PYTHONPATH=src`, starts the existing `python -m climateguard.webapp`, waits for `/api/health`, and opens the default browser at <http://127.0.0.1:8000>. If that health endpoint already responds, it opens the browser without starting another server. Startup output is written to `%TEMP%\ClimateGuardAI-server.log`; the launcher never installs packages, creates a virtual environment, changes project data, or retrains models.

To recreate the shortcut after moving or deleting it, double-click `scripts\create_climateguard_shortcut.vbs` again from this repository. To stop the hidden server safely, open PowerShell and run the following; it stops a listener on port 8000 only when its process is Python running this project's webapp module, and otherwise leaves it alone:

```powershell
$listener = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
if ($listener) {
    $server = Get-CimInstance Win32_Process -Filter "ProcessId=$($listener.OwningProcess)"
    $expectedPython = (Resolve-Path '.\.venv\Scripts\python.exe' -ErrorAction SilentlyContinue).Path
    if ($server -and $expectedPython -and $server.Name -match '^python(w)?\.exe$' -and
        $server.CommandLine.Contains($expectedPython) -and
        $server.CommandLine -match '-m\s+climateguard\.webapp') {
        Stop-Process -Id $server.ProcessId
    } else {
        Write-Host "Port 8000 is owned by another process; it was not stopped."
    }
}
```

This is only a local launch convenience for the completed dashboard. It does not change the dashboard, add a background service, or make the project an operational flood-warning system.

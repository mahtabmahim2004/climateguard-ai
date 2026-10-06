# Phase 12: Reproducibility and Final Validation

## Purpose and scope

Phase 12 consolidates evidence from Phases 1–11 into a reusable reproducibility check, an actual-artifact manifest, a scientific audit, and a pipeline-health report. It validates the repository's current research pipeline; it does not add a forecast service or establish real-world flood-prediction skill.

The reusable validation implementation is `src/climateguard/validation/reproducibility.py`. The existing orchestration API remains `src/climateguard/models/final_integration.py`, which calls the shared validator and preserves the existing Phase 12 integration outputs.

## Reproducibility architecture

The reproducibility module checks:

- dataset presence, readability, nonempty row count, schema, and expected feature columns
- target definition against the actual dataset values
- observed date coverage and chronological train/validation/test ranges
- expected persisted model availability
- Phase 8 NASA POWER/BWDB coverage and overlap status
- stable canonical dataset fingerprints across repeated reads
- scientific guardrails and prior-phase outputs

`seed` and `repeats` are recorded in the reproducibility summary. The current check fingerprints the existing processed dataset; it does not retrain models. A reproducibility PASS therefore confirms stable data/artifact consistency, not independent model-training reproducibility or forecasting validity.

## Data sources and coverage

### OBSERVED DATA

- NASA POWER Dhaka daily meteorological source: 2015-01-01 through 2024-12-31.
- BWDB station SW42 / Dhaka_Mill Barrack water-level observations: 2026-08-01 through 2026-08-31, 31 reported daily observations.
- These are separate source records. The verified coverage report records no temporal overlap.

No fused NASA/BWDB training dataset is present or created. BWDB water level is an observation, not an official flood label.

## Dataset, target, and features

The processed NASA-derived modeling table is `data/processed/flood_model_dataset.csv` (3,646 rows; dates 2015-01-08 through 2024-12-31 in the current repository state). Its schema contains `date`, the meteorological and derived feature columns, and `flood_risk_proxy`.

### PROXY TARGET

`flood_risk_proxy` is 1 when same-day rainfall is at least 10 mm and the 7-day rolling rainfall total is at least 60 mm; otherwise it is 0. This is a rainfall-derived proxy target, not observed flood ground truth. There are no official flood/no-flood labels in the BWDB status artifact, and no official flood threshold has been established.

The model features include temperature, rainfall, humidity, wind speed, pressure; current and rolling/lagged rainfall; selected lagged meteorological values; and calendar fields (`month`, `day_of_year`, `day_of_week`). Feature checks use the expected model feature list in `climateguard.models.dataset`.

## Temporal splits and models

The current chronological partitions are:

| Partition | Date range |
|---|---|
| Train | 2015-01-08 through 2021-12-31 |
| Validation | 2022-01-01 through 2023-12-31 |
| Test | 2024-01-01 through 2024-12-31 |

The temporal validation checks that all periods are populated and do not overlap. Test predictions are kept as a separate evaluation artifact. The evaluated baseline model families are Logistic Regression, Random Forest, and Gradient Boosting; preprocessing is fitted through the existing training pipeline.

## Calibration, uncertainty, and interpretation

Calibration utilities and tests are available for the proxy task. The current repository does not have a separate persisted Phase 9 calibration summary, so pipeline health reports calibration as `WARN` rather than claiming a saved report exists.

### MODEL-DERIVED OUTPUT and MODEL PROBABILITY

A model probability is the classifier's probability for the rainfall-derived proxy task. It is not a probability of observed flooding. `LOW`, `MEDIUM`, and `HIGH` are proxy-risk bands only. OOD status is a descriptive check against training-feature statistics, not real-world safety or danger.

Phase 10 contains global/permutation importance, directionality, partial-dependence-style responses, local examples, and a trust report. These are descriptive model explanations and do not establish causality.

## Phase 11 scenario analysis

### SCENARIO OUTPUT

Phase 11 applies controlled feature perturbations to model inputs and compares baseline and scenario proxy-model outputs. It is stress testing of the existing model, not an official climate scenario, climate projection, flood simulation, or government warning. It does not create new observations or flood labels. OOD checks remain available during scenario evaluation.

## Artifact manifest, scientific audit, and pipeline health

Phase 12 writes these reports into `data/processed/`:

- `phase12_artifact_manifest.json`: existing, identified Phase 1–11 artifacts only; CSV row count, schema, and available date coverage are included. Missing or hypothetical artifacts are not represented as existing.
- `phase12_scientific_audit.json`: explicit PASS/WARN/FAIL checks for the target, ground truth, source fusion, date/interpolation limits, thresholds, causal claims, probability interpretation, scenario scope, OOD, temporal evaluation, test separation, and documented limitations.
- `phase12_pipeline_health.json`: explicit status for the data and feature pipelines, model pipeline, temporal evaluation, calibration, uncertainty, explainability, scenario analysis, tests, documentation, and artifacts.
- `phase12_reproducibility_summary.json`: dataset/schema/feature/target/date/source/model/guardrail checks and repeated canonical fingerprints.

The audit reports `WARN` when repository contents cannot independently prove a historical upstream fact (for example, external authenticity or that no upstream date alteration/interpolation ever occurred). For BWDB, Phase 12 additionally reparses the preserved HTML snapshot and compares dates, water levels, station IDs/names, river, and district against both the cleaned and canonical CSVs. The current three tables match exactly (31 rows; 2026-08-01 through 2026-08-31). This verifies local snapshot-to-output consistency only; it does not independently authenticate the remote source or establish what happened before the snapshot was saved. Therefore, the three scientific audit checks remain WARN and are explicitly classified as non-blocking evidence limitations. They concern the separate BWDB observations, which do not overlap or enter the NASA-derived proxy training dataset.

Calibration has no persisted model-specific evaluation report in the repository. The Phase 9 calibration tests use deterministic synthetic fixtures, not the persisted project model predictions. Existing Phase 11 scenario outputs contain `calibration_status: "well_calibrated"`, a legacy value produced by the helper's former default rather than a measured result; Phase 12 records it as unsupported metadata and does not treat it as calibration evidence. New scenario evaluations default to `not_evaluated`. Calibration therefore remains WARN. This does not change the existing proxy-model probability calculations or scenario results, but those probabilities must not be described as empirically calibrated.

### Completion gate

The final integration may be marked COMPLETE with WARN statuses only when each remaining warning is explicitly classified as a non-blocking evidence limitation, no audit/health component is FAIL, all required artifacts are present, saved models load under the pinned runtime, dataset/research validation passes, and the actual dedicated tests, full test suite, and compileall results are all PASS. Missing validation results, any FAIL, or any unclassified warning blocks completion. Phase 12 does not promote WARN to PASS.

The three source-history warnings are non-blocking because the separate BWDB observations are not used for training/evaluation and do not affect the rainfall-proxy methodology; local raw-to-output agreement is also recorded. The calibration warning is retained and non-blocking for this integration gate because calibration is not applied to the stored Phase 10/11 predictions, and calibration health does not change scenario arithmetic. The unsupported `well_calibrated` metadata is explicitly disclaimed; no calibration result is inferred. This is not a claim that calibration has been validated.

`run_final_integration()` records actual command statuses through its `validation_results` argument (`phase12_tests`, `full_test_suite`, `compileall`). Do not pass PASS unless the corresponding command completed successfully. If no results are supplied, the completion gate remains blocked rather than assuming success.

## Validation commands

From the project root in PowerShell:

```powershell
$env:PATH = "$PWD\.venv\Scripts;$env:PATH"
$env:PYTHONPATH='src'
python -m pytest -q tests/test_phase12_reproducibility.py
python -m pytest -q
python -m compileall src
```

Final completion-gate run (2026-10-06, project venv): the dedicated Phase 12 suite passed **21 tests**; the full suite passed **123 tests** with **6 scikit-learn `OptimizeWarning: Unknown solver options: iprint` warnings**; `compileall src` completed successfully. No `InconsistentVersionWarning` occurred while loading the persisted models.

The venv should be created and installed from `requirements.txt` before validation. The repository pins scikit-learn to 1.6.1. Phase 12 records both the runtime version and the scikit-learn version embedded in every saved model, and attempts to load each existing model without rewriting it.

### Serialized model compatibility finding

The current three `.joblib` pipelines are pickle-based scikit-learn artifacts. Direct inspection of their embedded `_sklearn_version` metadata confirms **1.6.1** for logistic regression, random forest, and gradient boosting. Under the project-pinned scikit-learn **1.6.1** runtime, all three load successfully without `InconsistentVersionWarning`; Phase 12 reports this as the current compatibility result. An earlier report incorrectly described the embedded version as 1.9.1 and is superseded by this direct artifact inspection.

The separate global Python environment previously encountered `AttributeError: Can't get attribute '_RemainderColsList'` when loading a saved pipeline. That is evidence that loading is not portable across the environments tested, not evidence that the current artifacts were serialized by 1.9.1. Use the project venv and its pinned dependencies for this repository's reproducibility workflow. No model was regenerated or changed: regenerating could change Phase 10/11 results. This check establishes reproducibility in the pinned project runtime, not byte-for-byte reproducibility across arbitrary environments.

Pytest uses the project-local `.pytest-run-temp` directory to avoid scanning restricted per-user Windows temporary paths.

The Phase 12 entry point is `climateguard.models.final_integration.run_final_integration()`. It retains the existing final-integration interface and now emits the manifest, audit, and health reports alongside the existing Phase 12 reports.

## Known limitations

- `flood_risk_proxy` is a rainfall-rule target rather than verified flood ground truth.
- Current BWDB observations are from one station and do not overlap the NASA POWER modeling period.
- No fused NASA/BWDB supervised training table exists.
- No official flood threshold is established.
- Calibration has an implementation and tests but no dedicated persisted Phase 9 report in the current artifacts.
- The audit cannot establish external BWDB authenticity or prove that no date alteration/interpolation happened before the preserved raw snapshot; the raw-to-cleaned transformation matches exactly, but these audit items remain WARN.
- The existing Phase 11 `well_calibrated` status is a default field and not calibration evidence. The actual calibration state of persisted project models remains unverified.
- Compatibility evidence applies to the saved models and the current project-pinned runtime; the separate global interpreter failure demonstrates cross-environment portability risk.
- Model performance and probability outputs describe the proxy task only; no causal or operational flood-forecasting claim is made.

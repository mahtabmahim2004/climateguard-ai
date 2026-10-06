# Phase 10: Explainability and Trust Layer

## 1. Objective

This phase adds a lightweight, reproducible explainability and trust layer for the rainfall-derived proxy-risk model. The output is intended to support interpretation of the model while preserving the scientific distinction between:

- rainfall-derived proxy risk
- observed hydrological measurements
- official flood ground truth

This explainability layer does not claim real flood forecasting skill or create flood labels.

## 2. Model scope

The analysis applies only to the current proxy-risk classifier trained on NASA POWER meteorological variables and the rainfall-derived `flood_risk_proxy` target.

## 3. Explainability methods

The project uses the following deterministic explainability checks:

- global feature importance based on tree importances when available
- permutation importance for a robustness-oriented ranking
- local prediction explanations for individual rows
- feature directionality measured by correlation with model risk probability
- partial-dependence-style response analysis for each selected feature
- explanation stability across bootstrap resamples

## 4. Scientific guardrails

- No flood labels were fabricated.
- No official flood threshold was established.
- No NASA POWER and BWDB merge was performed for the explainability layer.
- No new prediction claim was made beyond proxy-risk interpretation.
- The output is a trust and interpretation report for an environmental proxy model, not for operational flood warning.

## 5. Generated artifacts

The explainability module writes the following artifacts into `data/processed/`:

- `phase10_global_feature_importance.csv`
- `phase10_permutation_importance.csv`
- `phase10_feature_directionality.json`
- `phase10_partial_dependence.json`
- `phase10_local_examples.json`
- `phase10_model_trust_report.json`

## 6. Validation approach

The explainability functions are validated through focused unit tests to confirm that:

- feature importance is generated
- permutation importance is computed
- local explanations are returned
- directionality is summarized
- partial dependence is available
- trust-report output is produced
- artifact files are saved

## 7. Final status

Phase 10 is complete as an explainability and trust layer for the proxy-risk model.
The outputs are scientifically limited to the current rainfall-derived proxy target and do not replace official flood ground truth.

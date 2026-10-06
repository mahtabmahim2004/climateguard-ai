# Phase 7: Scientific ML Modeling and Temporal Evaluation

## 1. Objective

This phase applies a leakage-safe, chronological ML workflow to the verified NASA POWER dataset using the existing rainfall-derived proxy target (`flood_risk_proxy`). The objective is to evaluate classical tabular baselines under realistic temporal constraints while preserving the important scientific distinction between proxy-risk modeling and actual flood ground truth.

## 2. Source dataset

- Source: NASA POWER reanalysis meteorological observations for Dhaka, Bangladesh.
- Dataset: `data/processed/flood_model_dataset.csv`
- Time range: 2015-01-01 through 2024-12-31
- Target used: `flood_risk_proxy`
- Important limitation: this target is rainfall-derived and is not an authoritative flood/no-flood label set.

## 3. Scientific framing

The project continues to preserve the distinction between:

- rainfall-derived proxy risk
- observed hydrological measurements from BWDB
- official flood/no-flood ground truth, which is not currently available

The BWDB hydrological observation layer remains separate and is not merged into the NASA POWER modeling dataset.

## 4. Temporal evaluation design

A strict chronological split was used to prevent leakage:

- Train: 2015-01-08 through 2021-12-31
- Validation: 2022-01-01 through 2023-12-31
- Test: 2024-01-01 through 2024-12-31

This split ensures that no future information leaks into earlier windows and reflects realistic operational deployment conditions.

## 5. Models evaluated

The workflow evaluates classical baselines suitable for tabular environmental data:

- Logistic Regression
- Random Forest
- Gradient Boosting

All preprocessing such as imputation and scaling was fit only on the training data and then applied to validation/test data using sklearn `Pipeline` and `ColumnTransformer` semantics.

## 6. Threshold analysis

A validation-set threshold sweep was used to choose an operational probability threshold for the proxy model only. The selected threshold is not an official flood alert threshold and should not be interpreted as a real-world flood warning threshold.

## 7. Model comparison and interpretability

The project generates:

- `data/processed/phase7_model_comparison.json`
- `data/processed/phase7_feature_importance.csv`
- `data/processed/phase7_test_predictions.csv`
- `data/processed/phase7_error_analysis.json`
- `data/processed/phase7_threshold_analysis.json`

For tree-based models, feature rankings are preserved and interpreted as relative importance within the proxy-risk target representation rather than real flood causality.

## 8. Ground-truth and limitations

The model is evaluated against a proxy target only. This means:

- performance is a measure of proxy-risk discrimination, not confirmed flood forecasting skill
- the target is not authoritative flood ground truth
- real flood/no-flood labels are not available in the current project data
- the BWDB dataset is a separate hydrological observation layer and cannot be treated as supervised flood labels because it has no validated flood threshold and no temporal overlap with the NASA POWER target period

## 9. What this phase does not claim

This phase does not claim:

- real flood prediction capability
- a validated flood threshold
- official flood/no-flood labels
- national flood ground truth
- a merged BWDB/NASA supervised dataset
- any Phase 8 or later implementation

## 10. Test results

The focused Phase 7 tests confirm:

- chronological splitting
- no train/test overlap
- no temporal leakage
- train-only preprocessing
- proper target validation
- threshold selection
- metric calculation
- prediction output schema
- model comparison generation
- feature importance generation

## 11. Final status

The Phase 7 workflow has been implemented and validated with a leakage-safe, chronological evaluation of the rainfall-derived proxy target. The results should be interpreted as a scientifically honest proxy-risk benchmark rather than proof of real-world flood forecasting skill.

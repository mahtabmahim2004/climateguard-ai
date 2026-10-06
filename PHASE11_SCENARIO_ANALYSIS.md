# Phase 11: Scenario Analysis and Stress Testing

## 1. Objective

Phase 11 adds a controlled scenario-analysis layer for the rainfall-derived proxy-risk model. The goal is to study how the model responds when meteorological inputs are perturbed in a controlled, physically interpretable way. Persisted project-model calibration has not been empirically verified.

This analysis is intentionally limited to model interpretation and stress testing. It does not attempt to simulate official flood forecasting, claim real flood behavior, or construct new flood labels.

## 2. Scientific framing

The supervised target remains the rainfall-derived `flood_risk_proxy`.

This target is not:

- official flood occurrence
- observed flooding ground truth
- a government flood-warning probability
- a real-world flood simulation

The system therefore treats all scenario outputs as "proxy-model scenario analysis" results.

## 3. Scenario engine

The Phase 11 implementation uses a reusable Python scenario engine in `src/climateguard/models/scenarios.py`. The engine supports:

- scenario creation
- controlled feature perturbations
- baseline-vs-scenario probability evaluation
- risk-band transition checks
- OOD propagation using the Phase 9 logic
- explanation comparison before and after perturbation
- stress-test summarization
- monotonicity sanity checks

Key functions include:

- `create_scenario(...)`
- `apply_feature_perturbation(...)`
- `evaluate_scenario(...)`
- `compare_scenarios(...)`
- `run_scenario(...)`
- `run_scenario_matrix(...)`
- `summarize_stress_tests(...)`
- `analyze_monotonicity(...)`

## 4. Scenario definitions

Scenario definitions use only meteorological features that are present in the current dataset. The engine does not invent unavailable climate variables.

Examples include:

- rainfall increase
- rainfall decrease
- humidity increase
- humidity decrease
- temperature increase
- temperature decrease
- wind-speed adjustment
- multi-feature controlled meteorological scenarios

Scenario perturbations remain relative and are constrained by the model's observed feature distribution. OOD conditions are explicitly flagged when a scenario leaves the training distribution.

## 5. Perturbation methodology

Perturbations are applied as controlled relative changes to the selected feature. Example behavior:

- +10% rainfall
- -20% rainfall
- +15% humidity
- -10% humidity

The implementation preserves the original baseline observation and replaces only the changed feature values for the scenario calculation. It does not alter the target definition or generate synthetic flood labels.

## 6. OOD handling

OOD propagation uses the Phase 9 distribution check based on training feature means and standard deviations. If the perturbed value moves substantially beyond the training feature distribution, the scenario is marked as out-of-distribution and a reason is recorded.

The engine records:

- in-distribution status
- OOD reason
- changed features
- magnitude of change

OOD status is descriptive only. It is not evidence of real-world flood behavior.

## 7. Probability response

For every scenario the following are recorded:

- baseline probability
- scenario probability
- probability delta
- percentage change when mathematically meaningful
- baseline risk band
- scenario risk band
- risk-band transition indicator

The outputs are always described as:

"model probability for rainfall-derived proxy risk"

and never as actual flood probability.

Calibration status is `not_evaluated` unless a caller supplies status supported by model-specific evidence. The existing Phase 11 result files retain their original `well_calibrated` field unchanged; that value came from the former helper default and is not a measured calibration result. Interpret those historical fields as unsupported metadata, not a scientific finding.

## 8. Explanation response

The scenario engine compares local explanations before and after perturbation through the existing explainability layer. This allows the project to inspect whether feature contributions shift in scientifically plausible directions under controlled changes.

The comparison records:

- top contributing features before scenario
- top contributing features after scenario
- contribution direction
- contribution magnitude
- changed feature contribution

No causal claim is made. The objective is interpretation, not causality.

## 9. Stress-test findings

The summary layer identifies:

- largest proxy-risk probability increase
- largest proxy-risk probability decrease
- strongest sensitivity features
- scenarios crossing risk bands
- scenarios becoming OOD
- scenarios with unstable explanations

The language is intentionally framed as proxy-risk behavior rather than flood danger.

## 10. Sanity checks

The implementation includes a monotonicity and sanity check for controlled feature sweeps. This does not force the model to be monotonic; it simply records whether the probability response is generally increasing, decreasing, or non-monotonic under a controlled perturbation sequence.

If the model behaves unexpectedly, the analysis reports that behavior rather than modifying the model to produce a more convenient pattern.

## 11. Artifacts

The project writes the following Phase 11 outputs to `data/processed/`:

- `phase11_scenario_results.json`
- `phase11_stress_test_summary.json`
- `phase11_scenario_matrix.csv`
- `phase11_sanity_checks.json`
- `phase11_proxy_probability_comparison.png`
- `phase11_rainfall_scenario_response.png`

These files are reusable analysis artifacts and are intended to support scientific review of the proxy-model stress tests.

## 12. Scientific limitations

This phase is deliberately constrained to model analysis. It does not:

- fabricate flood labels
- fabricate weather observations
- create synthetic training data
- merge NASA POWER and BWDB datasets
- interpolate hydrological records
- claim causal relationships
- claim real-world flood forecasting skill
- suggest official flood warning behavior

The scenario results are controlled model experiments for the rainfall-derived proxy target only.

## 13. Final status

Phase 11 completes the scenario-analysis and stress-testing layer for the current proxy-risk model while preserving the scientific guardrails established in earlier phases.

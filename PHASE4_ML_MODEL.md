# Phase 4 — Flood ML Model Development

## Objective

This phase develops the first machine-learning pipeline for Bangladesh flood-risk prediction using the verified NASA POWER dataset in `data/raw/nasa_power_dhaka_daily_2015_2024.csv`.

This is a prototype meteorological risk model only. It does not claim to predict observed flood events.

## Data source

- Source: NASA POWER daily meteorology
- Coordinate: latitude 23.8103, longitude 90.4125
- Date range: 2015-01-01 to 2024-12-31
- Variables used: T2M, PRECTOTCORR, RH2M, WS2M, PS
- File: `data/raw/nasa_power_dhaka_daily_2015_2024.csv`

## Modeling dataset preparation

The raw NASA POWER file was loaded without modifying the original data. A modeling dataset was constructed with the following fields:

- date
- latitude
- longitude
- temperature
- rainfall
- humidity
- wind_speed
- pressure
- rainfall_1d
- rainfall_3d_total
- rainfall_7d_total
- rainfall_14d_total
- lag features for rainfall, temperature, humidity, wind_speed, and pressure
- month
- day_of_year
- day_of_week
- flood_risk_proxy

## Flood-risk proxy definition

Observed flood labels are not available in the current NASA POWER dataset. Therefore, the project uses a rainfall-driven proxy target rather than a ground-truth flood-event label.

The proxy is defined as:

- `flood_risk_proxy = 1` if the 7-day rolling rainfall total is at least 60 mm and the current-day rainfall is at least 10 mm
- otherwise `flood_risk_proxy = 0`

This is a prototype meteorological flood-risk proxy, not an observed flood-event label.

The threshold is intentionally simple, transparent, and reproducible. It reflects elevated hydrological stress caused by sustained rainfall and short-term rainfall intensity without using any future information.

## Leakage prevention strategy

The following rules were enforced:

- Only current and past observations were used to build rolling and lag features.
- No future rainfall or meteorological variables were used as features.
- The target was constructed from the same-day and prior rainfall accumulation only.
- Model splits were created chronologically, not randomly.
- Rows with invalid lag or rolling features were removed after feature construction.

## Temporal split

The model uses strict chronological splits:

- Train: 2015-01-08 to 2021-12-31
- Validation: 2022-01-01 to 2023-12-31
- Test: 2024-01-01 to 2024-12-31

This ordering ensures `train_date < validation_date < test_date` and avoids temporal leakage.

## Models used

The project trained the following baseline classifiers:

1. Logistic Regression
2. Random Forest Classifier

These are simple, interpretable models intended for a first phase of flood-risk modeling.

## Results

### Overall class distribution

- Overall rows: 3,646
- Class 0: 2,948
- Class 1: 698

### Validation metrics

Logistic Regression:

- Accuracy: 0.9534
- Precision: 0.7778
- Recall: 0.9825
- F1-score: 0.8682
- ROC-AUC: 0.98997

Random Forest:

- Accuracy: 1.0000
- Precision: 1.0000
- Recall: 1.0000
- F1-score: 1.0000
- ROC-AUC: 1.0000

### Test metrics

Logistic Regression:

- Accuracy: 0.9344
- Precision: 0.7386
- Recall: 0.9848
- F1-score: 0.8442
- ROC-AUC: 0.9882

Random Forest:

- Accuracy: 1.0000
- Precision: 1.0000
- Recall: 1.0000
- F1-score: 1.0000
- ROC-AUC: 1.0000

## Model artifacts

Saved under `data/processed/models/`:

- `logistic_regression.joblib`
- `random_forest.joblib`

## Limitations

- The target is a rainfall proxy, not a verified flood event label.
- No observed flood labels or hydrological flood records were present in the available NASA POWER dataset.
- A true flood prediction model still requires authoritative flood-event data from agencies such as BWDB or FFWC, or other verified historical flood records.
- This phase is intentionally limited to prototype ML methodology and not production forecasting.

## Next steps

- Acquire verified historical flood-event records from legitimate public or institution sources.
- Merge rainfall, temperature, and hydrological variables into a richer dataset.
- Extend the proxy methodology into a more robust event definition when real labels exist.
- Add interpretable feature analysis and uncertainty checks in later development.

Observed flood labels are NOT available in the current NASA POWER dataset; flood_risk_proxy is therefore a prototype meteorological risk proxy, not ground truth.

# Data pipeline

## Purpose

This phase focuses only on data acquisition, organization, validation, cleaning, feature-preparation scaffolding, and exploratory-data-analysis readiness for the future Bangladesh flood-risk model.

## Pipeline stages

1. Data acquisition
   - Download only verified public datasets.
   - Store original data under `data/raw/` without modifying the source files.

2. Data validation
   - Check required columns.
   - Validate types and date parsing.
   - Check duplicate rows and missing values.
   - Validate geographic ranges and suspicious numeric values.

3. Data cleaning
   - Normalize column names.
   - Convert date fields.
   - Remove exact duplicates.
   - Standardize numeric values.
   - Sort records chronologically.

4. Feature preparation
   - Generate date-derived features such as year, month, day, and season.
   - Create lag and rolling statistics where the data supports them.
   - Ensure methods do not rely on future observations.

5. Exploratory data analysis
   - Inspect dataset shape, distributions, temporal coverage, and missingness.
   - Use notebooks to prepare research-ready summaries.

## Scope control

This phase does not include:

- model training
- prediction APIs
- dashboard development
- deployment infrastructure
- database services
- real-time alerting

## Current status

- Data pipeline modules created in `src/climateguard/data/`
- Source-aware ingestion interfaces created for BMD, BWDB, NASA POWER, and ERA5-style datasets
- Canonical schema and provenance utilities created for future dataset integration
- Feature-preparation functions created in `src/climateguard/features/engineering.py`
- No verified local flood dataset is yet available in the repository

## Phase 3 status

This repository is currently in a verified-source workflow: the system knows what to ingest and how to validate it, but no real raw dataset has been downloaded locally. The project remains reproducible without fabricated data and does not generate flood labels unless a legitimate source is available.

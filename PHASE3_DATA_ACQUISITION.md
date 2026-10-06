# Phase 3 data acquisition

## Goal

Phase 3 focuses on preparing the project for real-world Bangladesh flood-risk research using legitimate public and scientific sources only.

## Phase 3.2 actual acquisition status

A real NASA POWER dataset was successfully downloaded and verified for a Dhaka, Bangladesh point.

- File: `data/raw/nasa_power_dhaka_daily_2015_2024.csv`
- Coordinate: latitude 23.8103, longitude 90.4125
- Date range: 2015-01-01 to 2024-12-31
- Variables: T2M, PRECTOTCORR, RH2M, WS2M, PS
- Retrieval date: 2026-10-05
- Status: `VERIFIED_LOCAL`

This file was downloaded from the official NASA POWER daily API and kept in raw form without column edits, missing-value imputation, or row filtering.

## Source categories

### 1. Bangladesh Meteorological Department (BMD)

- Purpose: daily or sub-daily meteorological variables, including rainfall, temperature, humidity, and pressure
- Access: official public website or institutional data access channel
- Status: verified source, not locally available in this repository

### 2. Bangladesh Water Development Board (BWDB)

- Purpose: river level and discharge data for hydrological features
- Access: official hydrology or water resources source
- Status: verified source, not locally available in this repository

### 3. NASA POWER

- Purpose: climate and meteorological variables for Bangladesh and surrounding regions
- Access: NASA POWER public web portal
- Status: successfully verified locally for Dhaka, Bangladesh
- Local file: `data/raw/nasa_power_dhaka_daily_2015_2024.csv`

### 4. Copernicus ERA5 / ECMWF

- Purpose: reanalysis climate variables with strong geospatial coverage
- Access: Copernicus Climate Data Store
- Status: verified source, not locally available in this repository

## Raw data placement

When a real dataset is downloaded, place it under:

- `data/raw/`
- `data/processed/` for cleaned outputs
- `data/external/` for metadata and manifests

The project intentionally does not ship large raw files into Git. The repository is designed to remain runnable even when data is not yet downloaded.

## Ingestion process

1. Download a verified file from one of the approved sources.
2. Place the original file in `data/raw/` without modifying it.
3. Use the project loader utilities from `src/climateguard/data/`.
4. Validate required columns and date/coordinate integrity.
5. Apply cleaning and canonical schema mapping.
6. Export a reproducible quality report.

## Canonical schema

The project uses a canonical structure based on the Phase 2 data dictionary. It supports temporal, geographic, meteorological, hydrological, and environmental variables.

Important note: the target variable `flood_event` or `flood_risk` is not created unless a legitimate source or justification is available. This project intentionally does not fabricate labels.

## Validation and cleaning

The project uses the following standards:

- required-column checks
- missing-value detection
- duplicate detection
- date parsing
- numeric conversion
- geographic range validation
- chronological sorting
- source provenance metadata

## EDA

Once a real file is placed in `data/raw/`, the notebook workflow at `notebooks/phase2_eda_template.ipynb` or a new Phase 3 notebook can be used to inspect actual data distribution, coverage, and quality.

## Current repository state

A real NASA POWER raw dataset is now present in the repository. The project remains careful not to fabricate labels or synthetic data; the raw file is kept unchanged and the downstream processed data work remains separate.

## Next step toward ML

The next phase should acquire and validate at least one meteorological dataset and one hydrological dataset, then construct a combined canonical dataset with a clear and reproducible provenance trail.

# Data sources

This document records verified and legitimate public data-source categories relevant to the Bangladesh flood-risk project. One NASA POWER dataset has now been downloaded and verified locally.

## 1. Bangladesh government and public institutions

- Bangladesh Meteorological Department
  - Purpose: rainfall, temperature, humidity, and climate observations
  - Status: requires access and format verification
  - Notes: use only official public releases or documented APIs

- Bangladesh Water Development Board
  - Purpose: river level, discharge, or hydrological monitoring data
  - Status: requires access and format verification
  - Notes: suitable for hydrology and flood-risk feature preparation

## 2. Reanalysis and climate scientific datasets

- NASA POWER
  - URL: https://power.larc.nasa.gov/
  - Purpose: meteorological and surface data at regional/global scale
  - Status: successfully downloaded and verified locally for Dhaka, Bangladesh
  - Exact file: `data/raw/nasa_power_dhaka_daily_2015_2024.csv`
  - Coordinate: latitude 23.8103, longitude 90.4125
  - Date range: 2015-01-01 to 2024-12-31
  - Variables: T2M, PRECTOTCORR, RH2M, WS2M, PS
  - Notes: the raw NASA POWER response was retained without modifying the downloaded file

- Copernicus ERA5 / ECMWF reanalysis
  - URL: https://cds.climate.copernicus.eu/
  - Purpose: atmospheric and surface reanalysis fields
  - Status: planned for future ingestion
  - Notes: appropriate for rainfall, pressure, wind, and related features

## 3. Administrative and geographic metadata

- Bangladesh district and upazila boundary data from official GIS/public datasets
  - Purpose: spatial join, location grouping, and geographic coverage analysis
  - Status: requires acquisition and validation

## Important note

A verified NASA POWER raw dataset is now present in `data/raw/`. The repository continues to avoid shipping large files into Git and preserves raw files without modification.

## Phase 5.1 acquisition status

A focused acquisition attempt was made against the official BWDB/FFWC hydrological sources. The public landing pages and API root are legitimate and reachable, but the historical river-level/station observation endpoints remain blocked to unauthenticated access. No real BWDB/FFWC hydrological dataset was downloaded in this environment.

## Phase 3 status

The following source statuses are currently confirmed:

- Bangladesh Meteorological Department: verified public source, not locally available
- Bangladesh Water Development Board: verified public source, not locally available
- NASA POWER: successfully downloaded and verified locally for Dhaka, Bangladesh
- Copernicus ERA5 / ECMWF: verified scientific source, not locally available

Each source has a corresponding ingestion interface in `src/climateguard/data/sources.py`, and the NASA POWER file is now ready for downstream validation and analysis.

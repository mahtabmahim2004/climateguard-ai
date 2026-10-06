# Phase 5.5 — Real Hydrological Dataset Acquisition & Verification

## Objective

This phase attempted to obtain a real, locally saved Bangladesh hydrological observation dataset using only legitimate official access. The objective was to verify whether the public BWDB hydrology system could supply usable historical observations without bypassing security controls or inventing data.

## Official Source

- BWDB hydrology portal: http://www.hydrology.bwdb.gov.bd/
- Official public endpoint: http://www.hydrology.bwdb.gov.bd/includes/get_water_level_datatable.php
- Station used for validation: SW42 (Dhaka_Mill Barrack)
- River: Buriganga

## Acquisition Method

The official BWDB hydrology portal exposes a public "Water Level Data Graphical View" page. The station data table is loaded by the official application using a public POST request to the following endpoint:

- URL: http://www.hydrology.bwdb.gov.bd/includes/get_water_level_datatable.php
- Method: POST
- Request body: `station_id=SW42`

This endpoint is directly referenced by the official BWDB hydrology application UI and returns the last 30 days of water-level observations for the selected station.

## Dataset Obtained

A real official BWDB water-level response was successfully retrieved and saved locally as raw evidence.

Saved raw file:

- `data/raw/phase5_5_hydrological_dataset/bwdb_water_level_SW42_last_30d_raw.html`

Saved provenance metadata:

- `data/raw/phase5_5_hydrological_dataset/bwdb_water_level_SW42_metadata.json`

## Observation Period

- Earliest date in response: 1 August, 2026
- Latest date in response: 31 August, 2026
- Record count: 31

## Station Information

- Station ID: SW42
- Station name: Dhaka_Mill Barrack
- River: Buriganga
- District: Dhaka
- Source map metadata also confirmed: latitude 23.696917, longitude 90.419528, and station values such as danger level and last received data.

## Variables

The official response contains the following measurement variable:

- Water level (mMSL)

Column structure in the raw table output:

- Sl.
- Date
- Water Level (mMSL)

## Validation

Validation checks performed:

1. File exists locally.
2. File is non-empty.
3. Response status is HTTP 200.
4. Source is official BWDB hydrology site.
5. Records were returned from an official public endpoint.
6. Dates are present and historical (August 2026).
7. Station ID is present.
8. Water level values are numeric and recorded in meters above mean sea level.
9. No values were fabricated or manually invented.

Record summary:

- Row count: 31
- Earliest value: 3.29
- Latest value: 3.43
- Missing values: none identified in the returned table
- Unique station count: 1

## Provenance

- Source organization: Bangladesh Water Development Board (BWDB)
- Official URL: http://www.hydrology.bwdb.gov.bd/
- Official route: http://www.hydrology.bwdb.gov.bd/includes/get_water_level_datatable.php
- Retrieval date: 2026-10-06T00:00:00Z (UTC)
- Method: POST with station_id
- Content type: text/html
- File size: 9,254 bytes for the retrieved raw response

## Access Limitations

This dataset is a public official BWDB station-level water-level record covering the last 30 days, not a full national historical archive. The route appears to support per-station historical observation access for a recent window, but it should not be treated as a complete nationwide hydrological archive without further official query and documentation.

## Final Assessment

A real official BWDB historical hydrological dataset was successfully obtained and locally verified through a public official route. This is not synthetic or fabricated data and it was retrieved from the live BWDB hydrology application without bypassing access controls.

REAL BWDB HISTORICAL HYDROLOGICAL DATASET ACQUIRED AND VERIFIED.

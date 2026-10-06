# Phase 5.4 — Official Alternative Hydrological Data Access

## Objective

This phase investigated whether Bangladesh hydrological observations could be obtained through an officially documented public or legitimate alternative route without bypassing authentication or security controls. The investigation was limited to authoritative BWDB and FFWC sources and to public, non-bypass access patterns only.

## Official Sources Investigated

- https://ffwc.gov.bd/
- https://ffwc.gov.bd/app/home
- https://api.ffwc.gov.bd/
- https://bwdb.gov.bd/
- https://swh.bwdb.gov.bd/
- http://www.hydrology.bwdb.gov.bd/

The public hydrology portal at `http://www.hydrology.bwdb.gov.bd/` was treated as an official BWDB-linked hydrology surface because it is a dedicated BWDB hydrology service and exposes station/map-based water-level information from the official domain.

## BWDB Findings

The BWDB hydrology portal is publicly reachable and returned HTTP 200 OK. The site exposes a public map interface that loads water-level/geolocation data through an official PHP endpoint:

- `http://www.hydrology.bwdb.gov.bd/includes/home_page_map_load.php`

The live browser/source inspection showed the page uses a POST request pattern with district selection such as:

- `oparession=waterlavel_mapinfo`
- `district_id=26` (Dhaka)

A real public POST request to the official endpoint returned a successful response containing geolocated hydrological station data. The payload included fields such as:

- `station_id`
- `station_name`
- `lat`
- `lon`
- `river`
- `district`
- `upzla`
- `last_recv_dt`
- `last_recv_data`
- `danger_level`

This confirms that BWDB provides a real public geospatial water-level map layer and an official public AJAX endpoint. However, this is not a public historical archive or downloadable hydrological dataset. It is an operational map-driven station view with recent status values and location metadata rather than a complete historical observation export.

## FFWC Findings

The official FFWC app is publicly reachable at:

- https://ffwc.gov.bd/
- https://ffwc.gov.bd/app/home

The application source and runtime behavior confirm that the official app calls `https://api.ffwc.gov.bd` and routes such as:

- `/data_load/stations-2025/`
- `/data_load/recent-observed/`
- `/data_load/annotate-observed-trend/`
- `/data_load/observed-rainfall/`
- `/data_load/flood-summary/`
- `/data_load/district-flood-alerts-observed-forecast-by-observed-dates/{date}/`

Direct unauthenticated requests to the observed-data routes returned HTTP 403 Forbidden with the body:

- `Access Denied: Invalid Security Header`

This confirms that the FFWC hydrological observation API is protected and not publicly accessible without the required authorization context.

## Public Data Routes

Public and officially accessible route verified:

- `http://www.hydrology.bwdb.gov.bd/includes/home_page_map_load.php` with POST parameters `oparession=waterlavel_mapinfo` and `district_id=26`.

This route returned real, geolocated station data for Dhaka water-level points and recent values.

Publicly blocked/authorized-only route verified:

- `https://api.ffwc.gov.bd/data_load/recent-observed/`
- `https://api.ffwc.gov.bd/data_load/stations-2025/`
- `https://api.ffwc.gov.bd/data_load/annotate-observed-trend/`
- `https://api.ffwc.gov.bd/data_load/observed-rainfall/`
- `https://api.ffwc.gov.bd/data_load/flood-summary/`

These are real FFWC routes used by the official application, but they are not public without authorization.

## Official Data Request / Authorization Routes

No public CSV/JSON historical archive or official download route was verified for FFWC hydrological observations. The FFWC app itself wraps protected hydrological endpoints behind an authenticated/internal access pattern, including token-based Authorization behavior and an internal security header. No legitimate public request form or anonymous data export procedure was identified from the official public FFWC surface.

For BWDB, the public hydrology portal exposes a map interface but not a public historical-data download or data-request endpoint that could be verified as a public dataset route. The public route available is operational/station-view data, not a historic archive.

## Controlled Data Validation

A controlled public request was made to the official BWDB route:

- URL: `http://www.hydrology.bwdb.gov.bd/includes/home_page_map_load.php`
- Method: POST
- Parameters: `oparession=waterlavel_mapinfo&district_id=26`
- Result: HTTP 200 OK
- Validated fields in the response: `station_id`, `station_name`, `river`, `district`, `last_recv_dt`, `last_recv_data`, `danger_level`

This demonstrates that the route returns real current station observations from the official BWDB system. However, it does not provide a downloadable historical dataset, and it is not equivalent to a public hydrological archive. The response is a rendered map payload with station metadata, not a dataset export.

## Security / Access Constraints

- FFWC official hydrological API routes are protected by an internal security check and reject unauthenticated requests with `403 Forbidden` and `Access Denied: Invalid Security Header`.
- BWDB public portal is reachable and exposes map/station data, but the public route does not constitute a verified historical dataset export.
- No credentials, tokens, cookies, or internal headers were used or exposed during this investigation.

## Final Assessment

Real Bangladesh hydrological observations were not obtained through a verified public historical dataset route. The BWDB hydrology portal exposes a public map-driven current station view, and the FFWC app exposes protected hydrological APIs that require authorized access. The legitimate alternative route that exists is therefore access-controlled rather than publicly downloadable. This phase does not prove a public historical dataset is available without institutional authorization.

OFFICIAL HYDROLOGICAL DATA ROUTE EXISTS BUT REQUIRES AUTHORIZED ACCESS.

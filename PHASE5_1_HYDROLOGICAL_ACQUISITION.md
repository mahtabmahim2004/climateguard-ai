# Phase 5.1 — Hydrological acquisition investigation

## 1. Objective

This recovery task was limited to one objective: determine whether real historical Bangladesh river or water-level observations can be acquired from an authoritative BWDB/FFWC source, or whether the official public access remains blocked.

This task did not create synthetic river data, did not modify the NASA POWER raw dataset, and did not proceed into model development.

## 2. Official sources investigated

- Bangladesh Water Development Board (BWDB): https://bwdb.gov.bd/
- Flood Forecasting & Warning Centre (FFWC): https://ffwc.gov.bd/
- FFWC API landing page: https://api.ffwc.gov.bd/
- Candidate BWDB system from earlier investigation: https://swh.bwdb.gov.bd/
- Public BWDB application pages: https://bwdb.gov.bd/sip-database and https://bwdb.gov.bd/water-roundup

## 3. Endpoint discovery

Manual inspection of the official BWDB/FFWC pages showed that the public landing pages are informational and do not expose a working historical hydrological data API or downloadable station archive.

Key endpoint checks performed against the real public URLs:

- https://bwdb.gov.bd/ -> HTTP 200 (HTML landing page only)
- https://ffwc.gov.bd/ -> HTTP 200 (application shell only)
- https://api.ffwc.gov.bd/ -> HTTP 200 (landing page; no real dataset endpoint exposed)
- https://api.ffwc.gov.bd/api -> HTTP 403 Forbidden
- https://api.ffwc.gov.bd/api/ -> HTTP 403 Forbidden
- https://api.ffwc.gov.bd/api/stations -> HTTP 403 Forbidden
- https://api.ffwc.gov.bd/api/river -> HTTP 403 Forbidden
- https://api.ffwc.gov.bd/api/water-level -> HTTP 403 Forbidden
- https://swh.bwdb.gov.bd/ -> DNS resolution failure (`getaddrinfo failed`)
- https://swh.bwdb.gov.bd/hydro -> DNS resolution failure (`getaddrinfo failed`)

## 4. Verified endpoints

The following public endpoints were actually tested and verified:

| URL | HTTP status | Response type | Observation content |
|---|---:|---|---|
| https://bwdb.gov.bd/ | 200 | HTML | Informational public site; no hydrological dataset endpoint exposed |
| https://ffwc.gov.bd/ | 200 | HTML | Front-end application shell; no real river data export endpoint exposed |
| https://api.ffwc.gov.bd/ | 200 | HTML | API landing page; descriptive text only, not a downloadable historical observation source |
| https://api.ffwc.gov.bd/api/stations | 403 | Forbidden | Endpoint exists but is blocked; no dataset served to unauthenticated users |
| https://api.ffwc.gov.bd/api/water-level | 403 | Forbidden | Endpoint exists but is blocked; no dataset served to unauthenticated users |
| https://swh.bwdb.gov.bd/ | DNS error | N/A | Domain unresolved; no verified public service available |

## 5. Authentication requirements

The tested FFWC API routes returned HTTP 403 Forbidden when requested without any authenticated context. This indicates that historical hydrological access is not publicly available to an anonymous client in the current environment.

The public BWDB/FFWC websites do not provide a documented public historical water-level export or station archive that can be downloaded without additional access control or route discovery.

## 6. Actual download attempt

No real hydrological observation file was downloaded under `data/raw/` because there was no verified public historical river-level or water-level endpoint that returned actual observations.

The task therefore stopped at acquisition investigation and did not create a fake, synthetic, or copied hydrological dataset.

## 7. Downloaded file

None.

There is no real BWDB/FFWC hydrological observation file under `data/raw/` in this project state.

## 8. Observation count

Not applicable. No real hydrological observations were successfully downloaded.

## 9. Station count

Not applicable. No real station-level hydrological dataset was retrieved.

## 10. Date range

Not applicable. No real historical river observation archive was downloaded.

## 11. Variables

Not applicable. No real hydrological variable set was retrieved from a public BWDB/FFWC endpoint.

## 12. Data format

No verified hydrological file was retrieved. The public endpoints returned HTML or 403 responses, not machine-readable station or river observation data.

## 13. Data quality observations

- BWDB and FFWC official sites are reachable and legitimate.
- No public historical water-level dataset was available in this environment.
- The FFWC API root is not exposing an unauthenticated hydrological dataset.
- Likely access is gated by internal authorization, restricted service layers, or a protected application route that is not publicly accessible.
- The earlier candidate domain `swh.bwdb.gov.bd` failed to resolve, which confirms it is not publicly available from this environment.

## 14. Access limitations

The exact blocker is that public historical BWDB/FFWC hydrological observations remain inaccessible from this environment without the following normally required conditions:

- internal or authenticated access to the official system
- access to a protected station-data service or application endpoint
- direct permission from the Bangladesh Water Development Board / FFWC to retrieve station archives
- a different public API route or data portal that has not yet been discovered and authenticated

## 15. Final status

Final status: FAILURE

REAL BANGLADESH HYDROLOGICAL DATASET WAS NOT DOWNLOADED; OFFICIAL SOURCE VERIFIED BUT HISTORICAL DATA ACCESS REMAINS BLOCKED.

No real hydrological observations were downloaded, no synthetic data was created, and no unverified dataset was added to `data/raw/`.

# Phase 5.3 — FFWC public access and authorization investigation

## 1. Objective

This phase investigated the legitimate access mechanism behind the official FFWC hydrological application. The goal was to determine whether historical hydrological observations are publicly accessible or whether the official system requires authenticated access. No bypasses, token theft, browser credential extraction, or unauthorized access were attempted.

## 2. FFWC endpoints investigated

Official front end inspected:

- https://ffwc.gov.bd/
- https://ffwc.gov.bd/app/home
- https://api.ffwc.gov.bd/

Official API origins discovered from the application source:

- https://api.ffwc.gov.bd

Observed end points from the official application source / runtime requests:

- https://api.ffwc.gov.bd/data_load/stations-2025/
- https://api.ffwc.gov.bd/data_load/recent-observed/
- https://api.ffwc.gov.bd/data_load/annotate-observed-trend/
- https://api.ffwc.gov.bd/data_load/observed-rainfall/
- https://api.ffwc.gov.bd/data_load/flood-summary/
- https://api.ffwc.gov.bd/data_load/district-flood-alerts-observed-forecast-by-observed-dates/2026-10-06/

## 3. Request methods

The official application uses standard Angular HTTP calls against the `api.ffwc.gov.bd` origin. The data routes observed in the app are predominantly GET endpoints. The same app also contains POST/DELETE routes for user profile and station-management features, but those are not relevant to public historical hydrological access.

## 4. Authentication mechanism

The front-end source contains a token-based authentication flow:

- the app stores a user token in `localStorage` using `setToken()`
- it reads that token using `getToken()`
- it adds a `Authorization` header to outgoing requests when a token is present
- it also adds an internal security header named `x-ffwc-internal-key`
- an internal app secret value is used for that header

This is a legitimate credential/token mechanism, but it is not a public unauthenticated access path. The app is designed to require the token and the internal security header before access is granted.

## 5. Authorization mechanism

The application source includes an HTTP interceptor that checks for a token and a static internal secret before sending protected requests. If the token is absent or the internal security conditions are not satisfied, access is denied.

This is not a public API access pattern. It is an authenticated/service-authorized pattern.

## 6. Public endpoint results

The following requests were made without credentials or special browser session state from this environment:

| Endpoint | Result |
|---|---|
| https://api.ffwc.gov.bd/data_load/recent-observed/ | HTTP 403 Forbidden |
| https://api.ffwc.gov.bd/data_load/observed-rainfall/ | HTTP 403 Forbidden |
| https://api.ffwc.gov.bd/data_load/stations-2025/ | HTTP 403 Forbidden |
| https://api.ffwc.gov.bd/data_load/annotate-observed-trend/ | HTTP 403 Forbidden |
| https://api.ffwc.gov.bd/data_load/flood-summary/ | HTTP 403 Forbidden |
| https://api.ffwc.gov.bd/data_load/district-flood-alerts-observed-forecast-by-observed-dates/2026-10-06/ | HTTP 403 Forbidden |

Observed body text for the blocked responses:

- `Access Denied: Invalid Security Header`

This is a real, direct result from an unauthenticated request. It proves the route exists but is not publicly accessible from this environment.

## 7. Historical endpoint investigation

The application source contains route patterns indicating historical or observed data access, including names such as:

- `recent-observed`
- `observed-rainfall`
- `annotate-observed-trend`
- `stations-2025`
- `district-flood-alerts-observed-forecast-by-observed-dates/{date}`

These route names strongly indicate actual hydrological/observed-data retrieval. However, none of the routes produced a real historical dataset in the unauthenticated environment because they all returned 403 Forbidden.

## 8. Official download options

No public CSV, JSON, or historical station export route was found in the official FFWC application source that returns historical observations to unauthenticated clients. No public historical download endpoint was verified.

## 9. BWDB investigation

Official BWDB contact site and candidate hydrological domain were inspected only as public documentation:

- https://bwdb.gov.bd/
- https://swh.bwdb.gov.bd/

The candidate hydrology domain did not resolve from this environment, and no public historical hydrological data route could be verified from official BWDB public entry points.

## 10. Real public-data test

A single small controlled request was attempted to an actual observation route discovered from the official app:

- https://api.ffwc.gov.bd/data_load/recent-observed/

Result:

- HTTP status: 403 Forbidden
- content type: text/html
- body: `Access Denied: Invalid Security Header`

No actual hydrological observation records were returned. No historical raw data was obtained.

## 11. Access limitations

The exact blocker is not a guessed endpoint or a missing route. The official FFWC app itself calls real API paths on the `api.ffwc.gov.bd` origin, but those endpoints are protected by an internal security check and require institutional authorization or a valid authenticated context that is not publicly available.

This means:

- the observation routes exist,
- the hydrological dataset is likely real,
- but the legitimate public historical-data access path is not available to an unauthenticated user in this environment.

## 12. Exact blocker

The exact blocker is that FFWC hydrological observation endpoints require an authenticated and authorized client context. The application code adds both a token and an internal security header before making protected requests, and direct unauthenticated requests receive `403 Forbidden` with `Access Denied: Invalid Security Header`.

## 13. Recommended legitimate next step

The legitimate next step is not to bypass the security model. The valid next step is to obtain official authorization from the FFWC/BWDB institution, such as:

- authenticated access through the official application context,
- a formally documented API credential from the institution,
- an approved data-sharing mechanism,
- or an authorized public download route that is not blocked behind the security gate.

## 14. Final status

FFWC HISTORICAL HYDROLOGICAL DATA EXISTS BUT REQUIRES AUTHORIZED ACCESS.

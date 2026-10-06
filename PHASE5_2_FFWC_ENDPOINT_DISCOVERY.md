# Phase 5.2 — FFWC endpoint discovery

## 1. Objective

This phase was limited to endpoint discovery from the official FFWC application itself. The goal was to identify the real API route(s) used by the FFWC web app to fetch hydrological/station data without guessing or inventing endpoints.

## 2. Official application inspected

Official application inspected:

- https://ffwc.gov.bd/
- https://ffwc.gov.bd/app/home

The app is an Angular-based front end served directly from the FFWC domain. The application shell includes script bundles and a compiled JavaScript payload.

## 3. JavaScript/configuration sources inspected

The homepage exposes the following app bundle files:

- https://ffwc.gov.bd/runtime.33fc8fdfefd18df5.js
- https://ffwc.gov.bd/polyfills.53c52b7cec6c3212.js
- https://ffwc.gov.bd/scripts.83aca2ea6f86885c.js
- https://ffwc.gov.bd/main.3256d94b31f39e5f.js

The compiled bundle contains the app configuration object:

- `apiUrl: "https://api.ffwc.gov.bd"`
- `mapBaseUrl: "https://api.ffwc.gov.bd"`
- `api3Url: "https://api.ffwc.gov.bd"`

This proves the official application is configured to talk to the `api.ffwc.gov.bd` origin.

## 4. Discovered API base URL

Exact API base URL discovered from the official application source:

- `https://api.ffwc.gov.bd`

This is not a guessed URL; it is embedded directly in the compiled application configuration used by the official FFWC web app.

## 5. Discovered endpoint(s) used by the official application

The live browser network inspection of the official application shows these actual request URLs on the FFWC API origin:

- `https://api.ffwc.gov.bd/data_load/messages/`
- `https://api.ffwc.gov.bd/data_load/second-scroller-messages/`
- `https://api.ffwc.gov.bd/data_load/scroller-messages/`
- `https://api.ffwc.gov.bd/data_load/flood-summary/`
- `https://api.ffwc.gov.bd/data_load/update-date/`
- `https://api.ffwc.gov.bd/data_load/stations-2025/`
- `https://api.ffwc.gov.bd/data_load/district-flood-alerts-observed-forecast-by-observed-dates/2026-10-06/`
- `https://api.ffwc.gov.bd/data_load/annotate-observed-trend/`
- `https://api.ffwc.gov.bd/data_load/recent-observed/`
- `https://api.ffwc.gov.bd/data_load/observed-rainfall/`

These URLs were observed as real requests issued by the official app while loading the FFWC homepage.

## 6. HTTP method and request pattern

Based on the Angular HTTP client usage in the official JS bundle, these paths are hit by standard client-side GET requests. Several routes in the same domain also use POST/DELETE for user profile or station-management endpoints, but the hydrological observation routes relevant to this task are GET endpoints.

- Method: GET
- Base URL: `https://api.ffwc.gov.bd`
- Path pattern: `/data_load/...`
- Date-specific path example: `/data_load/district-flood-alerts-observed-forecast-by-observed-dates/{yyyy-mm-dd}/`

## 7. Parameters, headers, and auth

The exact request details are not publicly exposed in the application bundle beyond the base URL and path patterns, but the live requests from the browser show the app calls the API on the same origin and relies on the site's standard browser session and security headers.

Observed authentication/access behavior:

- Browser app requests succeed in the browser context.
- Direct unauthenticated HTTP requests from this environment receive:
  - HTTP 403 Forbidden
  - body: `Access Denied: Invalid Security Header`

This indicates the FFWC API endpoints are protected and not publicly accessible without the required internal access context or additional authorization.

## 8. Classification

- `https://api.ffwc.gov.bd/data_load/stations-2025/` — metadata / station catalog
- `https://api.ffwc.gov.bd/data_load/recent-observed/` — observation
- `https://api.ffwc.gov.bd/data_load/annotate-observed-trend/` — observation / derived trend
- `https://api.ffwc.gov.bd/data_load/observed-rainfall/` — observation
- `https://api.ffwc.gov.bd/data_load/district-flood-alerts-observed-forecast-by-observed-dates/{date}/` — mixed observed + forecast summary
- `https://api.ffwc.gov.bd/data_load/flood-summary/` — summary / other
- `https://api.ffwc.gov.bd/data_load/messages/` — metadata / UI content

The route names strongly indicate that the application is using actual observed hydrological data endpoints, but they are not publicly downloadable in the current environment without proper authorization.

## 9. Real request result

The following verified endpoint was requested directly from this environment:

- `https://api.ffwc.gov.bd/data_load/recent-observed/`
- HTTP status: `403 Forbidden`
- Content-Type: `text/html; charset=utf-8`
- Response body: `Access Denied: Invalid Security Header`

Additional real requests also returned 403 for the other observed-data endpoints, including:

- `https://api.ffwc.gov.bd/data_load/stations-2025/`
- `https://api.ffwc.gov.bd/data_load/annotate-observed-trend/`
- `https://api.ffwc.gov.bd/data_load/observed-rainfall/`
- `https://api.ffwc.gov.bd/data_load/flood-summary/`
- `https://api.ffwc.gov.bd/data_load/district-flood-alerts-observed-forecast-by-observed-dates/2026-10-06/`

No machine-readable hydrological observation payload was returned in this environment.

## 10. Historical data availability

Historical observed hydrological data is not available to this environment through the public FFWC API because the official endpoints are actively denying access with a security-header check. Therefore, a real historical dataset could not be downloaded or verified locally in this phase.

## 11. Exact blocker

The blocker is not a guessed or missing route. The actual official app requests are reaching real FFWC API routes, but those routes require additional authorization or internal browser/server context to return observed hydrological data. The app is protected by a security check that rejects unauthenticated external requests with `Access Denied: Invalid Security Header`.

## 12. Recommended next step

The next valid step is not additional guessing. The next valid step is to obtain the required official FFWC access context, such as:

- authenticated session or token from the official system,
- authorized browser access from within the official network,
- a documented partner API or internal data portal,
- or a validated official download mechanism that is not behind the blocked public interface.

Without that authorization, no real hydrological historical dataset can be downloaded from the public FFWC API in a lawful and verifiable manner.

## 13. Final status

FFWC HYDROLOGICAL ENDPOINT DISCOVERED BUT HISTORICAL OBSERVATION ACCESS REQUIRES ADDITIONAL AUTHORIZATION.

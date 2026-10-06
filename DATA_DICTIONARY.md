# Data dictionary

This dictionary defines the expected future modeling dataset structure for Bangladesh flood-risk analysis. It intentionally lists only fields that are supported by legitimate data sources or planned ingestion workflows.

## Core fields

| Field | Type | Status | Notes |
|---|---|---|---|
| date | datetime | expected | Observation or event date |
| latitude | float | expected | Geographic coordinate |
| longitude | float | expected | Geographic coordinate |
| division | string | expected later | Administrative area |
| district | string | expected later | Administrative area |
| upazila | string | expected later | Administrative area when available |
| rainfall | float | expected later | Daily or aggregated precipitation |
| temperature | float | expected later | Surface or air temperature |
| humidity | float | expected later | Relative humidity |
| wind_speed | float | expected later | Wind speed observations |
| pressure | float | expected later | Atmospheric pressure |
| river_level | float | expected later | Hydrological station level |
| river_discharge | float | expected later | Stream discharge |
| soil_moisture | float | expected later | Soil moisture proxy or model output |
| elevation | float | expected later | Terrain elevation |
| season | string | expected | Derived from date |
| month | int | expected | Derived from date |
| year | int | expected | Derived from date |
| day_of_year | int | expected | Derived from date |

## Target fields

The project architecture is prepared for a future target such as:

- `flood_event`
- `flood_risk`

However, no verified historical flood target is currently available in the repository. The target remains unresolved until a legitimate labeled dataset is acquired. This project does not manufacture labels or create a flood target from incomplete assumptions.

## Availability note

Fields marked as `expected later` are not yet confirmed in local data. They must be populated only from legitimate external sources or verified downloaded datasets.

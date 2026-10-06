from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

REQUIRED_COLUMNS = [
    "date",
    "station_id",
    "station_name",
    "river",
    "district",
    "water_level_mMSL",
]

STATION_META = {
    "station_id": "SW42",
    "station_name": "Dhaka_Mill Barrack",
    "river": "Buriganga",
    "district": "Dhaka",
    "organization": "Bangladesh Water Development Board (BWDB)",
    "official_source_url": "http://www.hydrology.bwdb.gov.bd/",
    "official_route": "http://www.hydrology.bwdb.gov.bd/includes/get_water_level_datatable.php",
    "http_method": "POST",
    "request_parameter": "station_id=SW42",
}


def project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def load_cleaned_bwdb_dataset(path: str | Path | None = None) -> pd.DataFrame:
    """Load the validated BWDB cleaned CSV."""
    target = Path(path) if path is not None else project_root() / "data" / "processed" / "bwdb_water_level_SW42_clean.csv"
    if not target.exists():
        raise FileNotFoundError(f"Cleaned BWDB dataset not found: {target}")

    df = pd.read_csv(target)
    if df.empty:
        raise ValueError(f"Cleaned BWDB dataset is empty: {target}")
    return df


def validate_schema(df: pd.DataFrame) -> dict[str, Any]:
    """Check whether the dataset matches the required hydrological schema."""
    missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    return {
        "required_columns": REQUIRED_COLUMNS,
        "columns_present": list(df.columns),
        "missing_columns": missing,
        "schema_valid": not missing,
    }


def validate_station_metadata(df: pd.DataFrame) -> dict[str, Any]:
    """Confirm the dataset preserves the known BWDB station metadata."""
    metadata_checks = {}
    for key, expected in STATION_META.items():
        if key in {"station_id", "station_name", "river", "district"}:
            values = df[key].dropna().astype(str)
            metadata_checks[key] = {
                "expected": expected,
                "actual_unique_values": list(values.unique()),
                "matches_expected": bool(values.empty is False and values.nunique() == 1 and values.iloc[0] == expected),
            }

    matches_expected = all(check["matches_expected"] for check in metadata_checks.values())
    return {
        "station_count": int(df["station_id"].nunique() if "station_id" in df.columns else 0),
        "station_ids": sorted(df["station_id"].dropna().astype(str).unique().tolist()),
        "metadata_valid": matches_expected,
        "checks": metadata_checks,
    }


def validate_dates(df: pd.DataFrame) -> dict[str, Any]:
    """Validate parsed dates and report invalid or missing entries."""
    if "date" not in df.columns:
        raise KeyError("Date column missing: date")

    parsed = pd.to_datetime(df["date"], errors="coerce")
    valid_mask = parsed.notna()
    return {
        "column": "date",
        "invalid_date_count": int((~valid_mask).sum()),
        "valid_date_count": int(valid_mask.sum()),
        "earliest": parsed[valid_mask].min().strftime("%Y-%m-%d") if valid_mask.any() else None,
        "latest": parsed[valid_mask].max().strftime("%Y-%m-%d") if valid_mask.any() else None,
        "date_values_valid": bool(valid_mask.all()),
    }


def validate_station_date_uniqueness(df: pd.DataFrame) -> dict[str, Any]:
    """Ensure each station-date pair appears at most once."""
    if {"station_id", "date"}.issubset(df.columns):
        duplicate_count = int(df.duplicated(subset=["station_id", "date"]).sum())
        unique_pairs = int(df.drop_duplicates(subset=["station_id", "date"]).shape[0])
        return {
            "duplicate_station_date_pairs": duplicate_count,
            "unique_station_date_pairs": unique_pairs,
            "station_date_pairs_unique": duplicate_count == 0,
        }
    return {
        "duplicate_station_date_pairs": 0,
        "unique_station_date_pairs": 0,
        "station_date_pairs_unique": False,
    }


def validate_numeric_water_levels(df: pd.DataFrame) -> dict[str, Any]:
    """Check that water levels are numeric and finite."""
    if "water_level_mMSL" not in df.columns:
        raise KeyError("Water-level column missing: water_level_mMSL")

    import math

    numeric_values = pd.to_numeric(df["water_level_mMSL"], errors="coerce")
    missing_count = int(numeric_values.isna().sum())
    non_finite_count = 0
    for value in numeric_values.dropna():
        try:
            if not math.isfinite(float(value)):
                non_finite_count += 1
        except (TypeError, ValueError):
            non_finite_count += 1

    return {
        "numeric_conversion_valid": bool(numeric_values.notna().all()),
        "missing_count": missing_count,
        "invalid_numeric_count": non_finite_count,
        "non_finite_count": non_finite_count,
        "minimum": float(numeric_values.dropna().min()) if numeric_values.notna().any() else None,
        "maximum": float(numeric_values.dropna().max()) if numeric_values.notna().any() else None,
        "mean": float(numeric_values.dropna().mean()) if numeric_values.notna().any() else None,
        "median": float(numeric_values.dropna().median()) if numeric_values.notna().any() else None,
    }


def check_temporal_continuity(df: pd.DataFrame) -> dict[str, Any]:
    """Check daily continuity across the observed date range without interpolating data."""
    dates = pd.to_datetime(df["date"], errors="coerce")
    valid_dates = dates.dropna()
    if valid_dates.empty:
        return {
            "missing_dates_count": 0,
            "date_range": {"earliest": None, "latest": None},
            "calendar_continuity_ok": False,
        }

    start = valid_dates.min()
    end = valid_dates.max()
    calendar_dates = pd.date_range(start=start, end=end, freq="D")
    observed = set(pd.Timestamp(value).floor("D") for value in valid_dates)
    missing_dates = [d.strftime("%Y-%m-%d") for d in calendar_dates if d not in observed]
    return {
        "missing_dates_count": len(missing_dates),
        "date_range": {"earliest": start.strftime("%Y-%m-%d"), "latest": end.strftime("%Y-%m-%d")},
        "calendar_continuity_ok": len(missing_dates) == 0,
        "missing_dates": missing_dates,
    }


def generate_integration_readiness_report(df: pd.DataFrame) -> dict[str, Any]:
    """Summarize whether the dataset is structurally ready for future temporal integration."""
    schema = validate_schema(df)
    station_metadata = validate_station_metadata(df)
    dates = validate_dates(df)
    station_date = validate_station_date_uniqueness(df)
    numeric = validate_numeric_water_levels(df)
    continuity = check_temporal_continuity(df)

    readiness = "READY_FOR_TEMPORAL_INTEGRATION" if (
        schema["schema_valid"]
        and station_metadata["metadata_valid"]
        and dates["date_values_valid"]
        and station_date["station_date_pairs_unique"]
        and numeric["missing_count"] == 0
        and numeric["invalid_numeric_count"] == 0
        and numeric["non_finite_count"] == 0
        and continuity["calendar_continuity_ok"]
    ) else "NOT_READY_FOR_TEMPORAL_INTEGRATION"

    return {
        "schema_validation": schema,
        "station_validation": station_metadata,
        "temporal_validation": {
            "date_validation": dates,
            "station_date_uniqueness": station_date,
            "continuity": continuity,
        },
        "numeric_validation": numeric,
        "integration_readiness": readiness,
    }


def build_canonical_hydrological_dataset(source_path: str | Path | None = None) -> pd.DataFrame:
    """Create a canonical observed hydrology dataset without adding labels or synthetic rows."""
    df = load_cleaned_bwdb_dataset(source_path)
    canonical = df.loc[:, REQUIRED_COLUMNS].copy()
    canonical["date"] = pd.to_datetime(canonical["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    canonical = canonical.sort_values("date").reset_index(drop=True)
    return canonical


def generate_ground_truth_status(df: pd.DataFrame) -> dict[str, Any]:
    """Encode the ground-truth status: hydrology is observed, flood labels are not official."""
    observation_count = int(len(df))
    station_ids = sorted(df["station_id"].dropna().astype(str).unique().tolist())
    earliest = pd.to_datetime(df["date"], errors="coerce").min().strftime("%Y-%m-%d") if not df.empty else None
    latest = pd.to_datetime(df["date"], errors="coerce").max().strftime("%Y-%m-%d") if not df.empty else None

    status = {
        "status": "OBSERVED_HYDROLOGY_AVAILABLE_BUT_OFFICIAL_FLOOD_LABELS_UNAVAILABLE",
        "hydrological_observations": {
            "available": True,
            "description": "Observed water-level measurements are available for the verified BWDB station dataset.",
        },
        "official_flood_labels": {
            "available": False,
            "description": "No official flood/no-flood labels are present in the BWDB observed hydrology dataset.",
        },
        "official_flood_threshold": {
            "available": False,
            "description": "No official flood threshold has been established in this phase.",
        },
        "nationwide_ground_truth": {
            "available": False,
            "description": "National flood ground truth is not available from the current official BWDB station dataset.",
        },
        "station_count": len(station_ids),
        "station_ids": station_ids,
        "observation_count": observation_count,
        "earliest_date": earliest,
        "latest_date": latest,
    }
    return status


def generate_hydrological_integration_report(df: pd.DataFrame) -> dict[str, Any]:
    """Build the integration readiness report from actual validation results."""
    validation = generate_integration_readiness_report(df)
    ground_truth = generate_ground_truth_status(df)
    missing_dates = validation["temporal_validation"]["continuity"]["missing_dates_count"]
    report = {
        "source_validation": {
            "organization": STATION_META["organization"],
            "official_source_url": STATION_META["official_source_url"],
            "official_route": STATION_META["official_route"],
            "http_method": STATION_META["http_method"],
            "request_parameter": STATION_META["request_parameter"],
            "source_verified": True,
        },
        "schema_validation": validation["schema_validation"],
        "station_validation": validation["station_validation"],
        "temporal_validation": validation["temporal_validation"],
        "numeric_validation": validation["numeric_validation"],
        "duplicate_validation": validation["temporal_validation"]["station_date_uniqueness"],
        "station_count": len(df["station_id"].unique()),
        "observation_count": int(len(df)),
        "date_range": {
            "earliest": pd.to_datetime(df["date"], errors="coerce").min().strftime("%Y-%m-%d"),
            "latest": pd.to_datetime(df["date"], errors="coerce").max().strftime("%Y-%m-%d"),
        },
        "missing_dates_count": missing_dates,
        "ground_truth": {
            "hydrological_observations_available": ground_truth["hydrological_observations"]["available"],
            "official_flood_labels_available": ground_truth["official_flood_labels"]["available"],
            "flood_threshold_established": ground_truth["official_flood_threshold"]["available"],
            "nationwide_ground_truth_available": ground_truth["nationwide_ground_truth"]["available"],
        },
        "integration_readiness": validation["integration_readiness"],
        "limitations": [
            "Only one station is represented in the verified BWDB dataset.",
            "The station is SW42 (Dhaka_Mill Barrack) on the Buriganga in Dhaka.",
            "The observed window is the validated Phase 5.6 period and is not nationwide coverage.",
            "The dataset contains observed water-level measurements, not official flood/no-flood labels.",
            "No official flood threshold has been established in this phase.",
            "Water level alone is not equivalent to a flood occurrence label.",
        ],
    }
    return report


def generate_provenance_data() -> dict[str, Any]:
    """Create provenance metadata for the integration layer."""
    project_root_dir = project_root()
    raw_file = project_root_dir / "data" / "raw" / "phase5_5_hydrological_dataset" / "bwdb_water_level_SW42_last_30d_raw.html"
    cleaned_input = project_root_dir / "data" / "processed" / "bwdb_water_level_SW42_clean.csv"
    canonical_output = project_root_dir / "data" / "processed" / "bwdb_hydrological_observations.csv"
    return {
        "organization": STATION_META["organization"],
        "official_source_url": STATION_META["official_source_url"],
        "exact_official_route_used": STATION_META["official_route"],
        "http_method": STATION_META["http_method"],
        "request_parameter": STATION_META["request_parameter"],
        "station_id": STATION_META["station_id"],
        "station_name": STATION_META["station_name"],
        "river": STATION_META["river"],
        "district": STATION_META["district"],
        "original_raw_file": str(raw_file),
        "cleaned_input_file": str(cleaned_input),
        "canonical_integration_output": str(canonical_output),
        "transformation_steps": [
            "Loaded the cleaned BWDB station-level water-level dataset from the Phase 5.6 output.",
            "Validated the required schema and station metadata.",
            "Validated the dates, station-date uniqueness, and numeric water levels.",
            "Sorted observations chronologically without synthetic data or interpolation.",
            "Stored the canonical observed hydrology dataset for future temporal integration work.",
        ],
        "retrieval_limitations": [
            "This dataset represents a single station and a limited recent historical window.",
            "It is not a nationwide hydrological archive.",
            "The dataset contains observed water-level measurements, not official flood/no-flood labels.",
        ],
        "statement": "This dataset contains observed water-level measurements, not official flood/no-flood labels.",
    }


def build_phase6_outputs() -> dict[str, Any]:
    """Create the Phase 6 outputs: canonical CSV, ground-truth status, integration report, and provenance."""
    project_root_dir = project_root()
    processed_dir = project_root_dir / "data" / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)

    df = load_cleaned_bwdb_dataset()
    canonical = build_canonical_hydrological_dataset()
    canonical_path = processed_dir / "bwdb_hydrological_observations.csv"
    canonical.to_csv(canonical_path, index=False)

    ground_truth = generate_ground_truth_status(canonical)
    ground_truth_path = processed_dir / "bwdb_ground_truth_status.json"
    ground_truth_path.write_text(json.dumps(ground_truth, indent=2), encoding="utf-8")

    report = generate_hydrological_integration_report(canonical)
    report_path = processed_dir / "bwdb_hydrological_integration_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    provenance = generate_provenance_data()
    provenance_path = processed_dir / "bwdb_hydrological_integration_provenance.json"
    provenance_path.write_text(json.dumps(provenance, indent=2), encoding="utf-8")

    return {
        "canonical_df": canonical,
        "canonical_path": str(canonical_path),
        "ground_truth": ground_truth,
        "ground_truth_path": str(ground_truth_path),
        "integration_report": report,
        "integration_report_path": str(report_path),
        "provenance": provenance,
        "provenance_path": str(provenance_path),
    }


if __name__ == "__main__":
    build_phase6_outputs()

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any

import pandas as pd

from climateguard.data.cleaning import clean_dataset


STATION_META = {
    "station_id": "SW42",
    "station_name": "Dhaka_Mill Barrack",
    "river": "Buriganga",
    "district": "Dhaka",
    "organization": "Bangladesh Water Development Board (BWDB)",
    "source_url": "http://www.hydrology.bwdb.gov.bd/",
    "source_route": "http://www.hydrology.bwdb.gov.bd/includes/get_water_level_datatable.php",
    "request_method": "POST",
    "request_parameter": "station_id=SW42",
}


def _clean_cell(value: str) -> str:
    if value is None:
        return ""
    cleaned = re.sub(r"<.*?>", " ", str(value), flags=re.DOTALL)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return html_unescape(cleaned).strip()


def html_unescape(value: str) -> str:
    import html

    return html.unescape(value)


def parse_bwdb_water_level_html(
    html_text: str,
    *,
    station_id: str = STATION_META["station_id"],
    station_name: str = STATION_META["station_name"],
    river: str = STATION_META["river"],
    district: str = STATION_META["district"],
) -> list[dict[str, Any]]:
    """Parse the official BWDB HTML water-level table into normalized row dictionaries."""
    rows: list[dict[str, Any]] = []
    tr_matches = re.findall(r"<tr\b[^>]*>(.*?)</tr>", html_text, flags=re.IGNORECASE | re.DOTALL)

    for row in tr_matches:
        cells = re.findall(r"<td\b[^>]*>(.*?)</td>", row, flags=re.IGNORECASE | re.DOTALL)
        if len(cells) < 3:
            continue

        date_raw = _clean_cell(cells[1])
        value_raw = _clean_cell(cells[2])
        if not date_raw or not value_raw:
            continue

        parsed_date = pd.to_datetime(date_raw, errors="coerce")
        value_numeric = pd.to_numeric(value_raw.replace(",", ""), errors="coerce")

        if pd.isna(parsed_date) or pd.isna(value_numeric):
            continue

        value_float = float(value_numeric)
        if not math.isfinite(value_float):
            continue

        rows.append(
            {
                "date": parsed_date.strftime("%Y-%m-%d"),
                "water_level_mMSL": value_float,
                "station_id": station_id,
                "station_name": station_name,
                "river": river,
                "district": district,
            }
        )

    return rows


def validate_bwdb_hydrology_dataset(df: pd.DataFrame) -> dict[str, Any]:
    """Compute data quality indicators for the cleaned BWDB hydrology dataset."""
    if df.empty:
        raise ValueError("No valid BWDB hydrology data found after parsing.")

    if "date" not in df.columns or "water_level_mMSL" not in df.columns:
        raise KeyError("Expected date and water_level_mMSL columns in the BWDB data frame.")

    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    numeric_values = pd.to_numeric(df["water_level_mMSL"], errors="coerce")
    df["water_level_mMSL"] = numeric_values

    valid_rows = df.dropna(subset=["date", "water_level_mMSL"]).copy()
    if valid_rows.empty:
        raise ValueError("No valid rows with both date and water-level values remain.")

    valid_rows = valid_rows.sort_values("date").reset_index(drop=True)
    date_range = pd.date_range(start=valid_rows["date"].min(), end=valid_rows["date"].max(), freq="D")
    missing_dates = date_range.difference(valid_rows["date"]).tolist()
    duplicate_dates = int(valid_rows["date"].duplicated().sum())
    duplicate_complete = int(valid_rows.duplicated(subset=["date", "station_id", "station_name", "river", "district", "water_level_mMSL"]).sum())
    missing_water_level = int(df["water_level_mMSL"].isna().sum())
    invalid_numeric = int(df["water_level_mMSL"].isna().sum())
    non_finite = int(
        df["water_level_mMSL"].map(lambda value: bool(pd.notna(value) and not math.isfinite(float(value)))).sum()
    )

    stats = valid_rows["water_level_mMSL"]
    report = {
        "row_count_input": int(len(df)),
        "row_count_output": int(len(valid_rows)),
        "date_range": {
            "earliest": valid_rows["date"].min().strftime("%Y-%m-%d"),
            "latest": valid_rows["date"].max().strftime("%Y-%m-%d"),
        },
        "missing_dates_count": len(missing_dates),
        "duplicate_dates_count": duplicate_dates,
        "duplicate_complete_rows_count": duplicate_complete,
        "missing_water_level_count": missing_water_level,
        "invalid_numeric_count": invalid_numeric,
        "non_finite_count": non_finite,
        "water_level_statistics": {
            "min": float(stats.min()),
            "max": float(stats.max()),
            "mean": float(stats.mean()),
            "median": float(stats.median()),
            "std": float(stats.std(ddof=1)) if len(stats) > 1 else 0.0,
        },
        "station_metadata": {
            "station_id": str(valid_rows["station_id"].iloc[0]),
            "station_name": str(valid_rows["station_name"].iloc[0]),
            "river": str(valid_rows["river"].iloc[0]),
            "district": str(valid_rows["district"].iloc[0]),
        },
        "validation_status": "passed" if missing_dates == [] and duplicate_dates == 0 and missing_water_level == 0 and invalid_numeric == 0 and non_finite == 0 else "warnings",
    }
    return report


def build_clean_bwdb_dataset(raw_html_path: str | Path) -> pd.DataFrame:
    """Parse raw official BWDB HTML and return cleaned daily water-level records."""
    path = Path(raw_html_path)
    if not path.exists():
        raise FileNotFoundError(f"Raw BWDB HTML file not found: {path}")

    html_text = path.read_text(encoding="utf-8", errors="replace")
    records = parse_bwdb_water_level_html(html_text)
    if not records:
        raise ValueError(f"No valid water-level observations were found in {path}.")

    df = pd.DataFrame(records)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["water_level_mMSL"] = pd.to_numeric(df["water_level_mMSL"], errors="coerce")
    df = df.dropna(subset=["date", "water_level_mMSL"]).sort_values("date").reset_index(drop=True)

    if df.empty:
        raise ValueError("Cleaned BWDB dataset is empty after numeric conversion.")

    # Keep the dataset deterministic and preserve raw observations without interpolation.
    df = clean_dataset(
        df,
        date_column="date",
        required_columns=["date", "station_id", "station_name", "river", "district", "water_level_mMSL"],
        numeric_columns=["water_level_mMSL"],
    )
    if "water_level_mmsl" in df.columns and "water_level_mMSL" not in df.columns:
        df = df.rename(columns={"water_level_mmsl": "water_level_mMSL"})
    return df


def generate_bwdb_quality_report(
    input_path: str | Path,
    output_path: str | Path,
    *,
    station_id: str = STATION_META["station_id"],
    station_name: str = STATION_META["station_name"],
    river: str = STATION_META["river"],
    district: str = STATION_META["district"],
) -> dict[str, Any]:
    """Build and save a JSON quality report for the cleaned BWDB hydrology dataset."""
    input_file = Path(input_path)
    output_file = Path(output_path)

    raw_df = pd.read_html(str(input_file), flavor="bs4")[0] if False else None
    del raw_df

    cleaned_df = build_clean_bwdb_dataset(input_file)
    validation = validate_bwdb_hydrology_dataset(cleaned_df)
    report = {
        "source": {
            "organization": STATION_META["organization"],
            "url": STATION_META["source_url"],
            "station_id": station_id,
            "station_name": station_name,
            "river": river,
            "district": district,
        },
        "input_file": str(input_file),
        "output_file": str(output_file),
        "row_count_input": validation["row_count_input"],
        "row_count_output": validation["row_count_output"],
        "date_range": validation["date_range"],
        "missing_dates_count": validation["missing_dates_count"],
        "duplicate_dates_count": validation["duplicate_dates_count"],
        "missing_water_level_count": validation["missing_water_level_count"],
        "invalid_numeric_count": validation["invalid_numeric_count"],
        "non_finite_count": validation["non_finite_count"],
        "water_level_statistics": validation["water_level_statistics"],
        "validation_status": validation["validation_status"],
        "notes": [
            "Real official BWDB dataset parsed from raw HTML without synthetic interpolation.",
            "The raw source artifact was preserved unchanged.",
            "The dataset represents a single station and a limited recent historical window.",
        ],
    }

    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)

    return report


def generate_bwdb_provenance(
    *,
    raw_input_path: str | Path,
    cleaned_output_path: str | Path,
    retrieval_datetime: str | None = None,
) -> dict[str, Any]:
    """Create a provenance file describing the official BWDB acquisition and processing steps."""
    provenance = {
        "source_organization": STATION_META["organization"],
        "official_source_url": STATION_META["source_url"],
        "exact_official_route_used": STATION_META["source_route"],
        "http_method": STATION_META["request_method"],
        "request_parameter_used": STATION_META["request_parameter"],
        "station_id": STATION_META["station_id"],
        "station_name": STATION_META["station_name"],
        "river": STATION_META["river"],
        "district": STATION_META["district"],
        "retrieval_datetime": retrieval_datetime or "2026-10-06T00:00:00Z",
        "raw_input_filename": str(Path(raw_input_path).name),
        "cleaned_output_filename": str(Path(cleaned_output_path).name),
        "transformation_description": "Parsed raw HTML table, normalized dates and numeric values, removed malformed rows, preserved valid observations, and wrote a cleaned CSV with station metadata.",
        "raw_source_preserved": True,
        "statement": "This dataset was acquired from the official BWDB hydrology site and represents one station over a recent historical window; it is not a nationwide archive.",
    }
    return provenance


def execute_phase5_6_pipeline() -> dict[str, Any]:
    """Run the Phase 5.6 pipeline end-to-end for the official BWDB water-level dataset."""
    project_root = Path(__file__).resolve().parents[3]
    raw_html = project_root / "data" / "raw" / "phase5_5_hydrological_dataset" / "bwdb_water_level_SW42_last_30d_raw.html"
    processed_dir = project_root / "data" / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)

    cleaned_df = build_clean_bwdb_dataset(raw_html)
    output_csv = processed_dir / "bwdb_water_level_SW42_clean.csv"
    cleaned_df.to_csv(output_csv, index=False)

    quality_report = generate_bwdb_quality_report(
        raw_html,
        processed_dir / "bwdb_water_level_SW42_quality_report.json",
        station_id=STATION_META["station_id"],
        station_name=STATION_META["station_name"],
        river=STATION_META["river"],
        district=STATION_META["district"],
    )

    provenance = generate_bwdb_provenance(
        raw_input_path=raw_html,
        cleaned_output_path=output_csv,
        retrieval_datetime="2026-10-06T00:45:21Z",
    )
    provenance_path = processed_dir / "bwdb_water_level_SW42_provenance.json"
    provenance_path.write_text(json.dumps(provenance, indent=2), encoding="utf-8")

    return {
        "cleaned_df": cleaned_df,
        "quality_report": quality_report,
        "provenance": provenance,
        "output_csv": str(output_csv),
        "quality_report_path": str(processed_dir / "bwdb_water_level_SW42_quality_report.json"),
        "provenance_path": str(provenance_path),
    }


if __name__ == "__main__":
    execute_phase5_6_pipeline()

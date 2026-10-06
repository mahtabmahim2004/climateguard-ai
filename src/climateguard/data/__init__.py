"""Data loading and processing utilities for ClimateGuard AI."""

from .canonical import build_canonical_dataset, canonicalize_columns
from .cleaning import clean_dataset, normalize_columns
from .coverage import compute_date_frequency, generate_source_coverage_report, summarize_source_coverage
from .loader import list_data_files, load_dataset
from .sources import load_bmd_data, load_bwdb_data, load_era5_data, load_nasa_power_data
from .temporal_alignment import (
    align_datasets,
    analyze_temporal_overlap,
    detect_date_range,
    detect_duplicate_dates,
    detect_missing_dates,
    generate_alignment_report,
    validate_date_column,
)
from .validation import (
    detect_duplicate_rows,
    detect_missing_values,
    export_data_quality_report,
    generate_data_quality_report,
    validate_coordinate_columns,
    validate_required_columns,
)

__all__ = [
    "list_data_files",
    "load_dataset",
    "clean_dataset",
    "normalize_columns",
    "canonicalize_columns",
    "build_canonical_dataset",
    "validate_required_columns",
    "detect_missing_values",
    "detect_duplicate_rows",
    "validate_coordinate_columns",
    "generate_data_quality_report",
    "export_data_quality_report",
    "load_bmd_data",
    "load_bwdb_data",
    "load_nasa_power_data",
    "load_era5_data",
    "validate_date_column",
    "detect_duplicate_dates",
    "detect_missing_dates",
    "detect_date_range",
    "analyze_temporal_overlap",
    "align_datasets",
    "generate_alignment_report",
    "compute_date_frequency",
    "summarize_source_coverage",
    "generate_source_coverage_report",
]

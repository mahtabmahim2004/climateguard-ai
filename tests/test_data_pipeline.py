from pathlib import Path

import pandas as pd
import pytest

from climateguard.data.cleaning import (
    clean_dataset,
    normalize_columns,
    parse_date_column,
    remove_exact_duplicates,
    sort_chronologically,
)
from climateguard.data.loader import list_data_files, load_dataset
from climateguard.data.validation import (
    detect_duplicate_rows,
    detect_missing_values,
    generate_data_quality_report,
    validate_coordinate_columns,
    validate_required_columns,
)
from climateguard.features.engineering import (
    add_date_features,
    add_lag_features,
    add_rolling_statistics,
)


@pytest.fixture
def sample_dataframe() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Date": ["2024-01-01", "2024-01-02", "2024-01-02", "2024-01-04"],
            "Rainfall (mm)": [10.0, None, 13.0, 5.0],
            "Temp C": [25.0, 28.0, 27.0, 30.0],
            "Latitude": [22.1, 23.5, 21.2, 90.5],
            "Longitude": [89.1, 88.8, 89.3, 190.0],
            "Division": ["Sylhet", "Dhaka", "Dhaka", "Chattogram"],
        }
    )


def test_load_dataset_csv() -> None:
    path = Path(__file__).resolve().parents[1] / "data" / "processed" / "sample_test_dataset.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"date": ["2024-01-01"], "rainfall": [10.0]}).to_csv(path, index=False)

    try:
        data = load_dataset(path)
        assert list(data.columns) == ["date", "rainfall"]
        assert data.iloc[0]["rainfall"] == 10.0
    finally:
        path.unlink(missing_ok=True)


def test_loader_directory_listing_returns_files() -> None:
    files = list_data_files("data")
    assert isinstance(files, list)
    assert all(path.is_file() for path in files)


def test_validate_required_columns() -> None:
    df = pd.DataFrame({"date": ["2024-01-01"], "rainfall": [12.5]})

    missing = validate_required_columns(df, ["date", "rainfall", "location"])

    assert missing == ["location"]


def test_missing_values_and_duplicate_counts(sample_dataframe: pd.DataFrame) -> None:
    missing = detect_missing_values(sample_dataframe)
    duplicates = detect_duplicate_rows(sample_dataframe)

    assert missing["Rainfall (mm)"] == 1
    assert duplicates == 0


def test_coordinate_validation() -> None:
    df = pd.DataFrame({"latitude": [22.0, 99.0, None], "longitude": [89.0, 181.0, 90.0]})

    report = validate_coordinate_columns(df)

    assert report["invalid_latitude"] == 2
    assert report["invalid_longitude"] == 1
    assert report["invalid_longitude"] == 1


def test_clean_dataset_normalizes_and_sorts(sample_dataframe: pd.DataFrame) -> None:
    cleaned = clean_dataset(
        sample_dataframe,
        date_column="Date",
        required_columns=["Date", "Rainfall (mm)", "Latitude", "Longitude"],
        numeric_columns=["Rainfall (mm)", "Temp C", "Latitude", "Longitude"],
    )

    assert "date" in cleaned.columns
    assert cleaned["date"].is_monotonic_increasing
    assert cleaned.loc[0, "rainfall_mm"] == 10.0


def test_parse_date_column_and_removed_duplicates() -> None:
    df = pd.DataFrame({"date": ["2024-01-01", "2024-01-01", "2024-01-03"]})

    parsed = parse_date_column(df, "date")
    deduped = remove_exact_duplicates(parsed)

    assert parsed["date"].dtype.kind == "M"
    assert len(deduped) == 2


def test_sort_chronologically() -> None:
    df = pd.DataFrame({"date": ["2024-01-03", "2024-01-01", "2024-01-02"]})

    sorted_df = sort_chronologically(df, "date")

    assert sorted_df["date"].dt.strftime("%Y-%m-%d").tolist() == [
        "2024-01-01",
        "2024-01-02",
        "2024-01-03",
    ]


def test_feature_engineering_creates_time_and_lag_features() -> None:
    df = pd.DataFrame({"date": ["2024-01-01", "2024-01-02", "2024-01-03"], "rainfall": [10.0, 20.0, 30.0]})

    with_date = add_date_features(df)
    with_lag = add_lag_features(with_date, "rainfall", lags=(1, 2))
    with_rolling = add_rolling_statistics(with_lag, "rainfall", windows=(2, 3))

    assert "year" in with_date.columns
    assert "rainfall_lag_1" in with_lag.columns
    assert "rainfall_rolling_mean_2" in with_rolling.columns


def test_data_quality_report_generates_dict() -> None:
    df = pd.DataFrame({"date": ["2024-01-01", "2024-01-02"], "rainfall": [1.0, None], "latitude": [22.0, 33.0], "longitude": [89.0, 91.0]})

    report = generate_data_quality_report(df)

    assert "rows" in report
    assert report["duplicate_rows"] == 0
    assert report["missing_values"]["rainfall"] == 1

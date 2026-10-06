from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

SUPPORTED_DATA_FORMATS = {".csv", ".json", ".parquet", ".pq"}


def list_data_files(directory: str | Path | None = None) -> list[Path]:
    """Return a sorted list of files from a directory.

    The function intentionally ignores directories and only reports files.
    """
    target = Path(directory) if directory is not None else Path.cwd()

    if not target.exists():
        raise FileNotFoundError(f"Directory does not exist: {target}")

    if not target.is_dir():
        raise NotADirectoryError(f"Expected a directory, got: {target}")

    return sorted(path for path in target.iterdir() if path.is_file())


def load_dataset(
    file_path: str | Path,
    *,
    file_format: str | None = None,
    **kwargs: Any,
) -> pd.DataFrame:
    """Load a dataset from CSV, JSON, or Parquet using pandas.

    Parameters
    ----------
    file_path:
        Path to the data file.
    file_format:
        Optional override for file format. If omitted, the suffix is used.
    **kwargs:
        Keyword arguments forwarded to the pandas reader.
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")

    if not path.is_file():
        raise ValueError(f"Expected a file path, received a directory instead: {path}")

    resolved_format = (file_format or path.suffix.lower()).lstrip(".")

    if resolved_format not in {"csv", "json", "parquet", "pq"}:
        supported = ", ".join(sorted(SUPPORTED_DATA_FORMATS))
        raise ValueError(f"Unsupported dataset format: {resolved_format}. Supported: {supported}")

    if resolved_format == "csv":
        return pd.read_csv(path, **kwargs)

    if resolved_format == "json":
        return pd.read_json(path, **kwargs)

    if resolved_format in {"parquet", "pq"}:
        return pd.read_parquet(path, **kwargs)

    raise ValueError(f"Unable to load dataset: {path}")

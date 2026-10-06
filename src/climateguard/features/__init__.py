"""Feature engineering package."""

from .catalog import FEATURE_CATALOG, generate_feature_catalog
from .engineering import placeholder_feature_summary
from .hydro_meteorological import (
    add_hydrological_rolling_features,
    add_meteorological_rolling_features,
    prepare_future_alignment_feature_layer,
)

__all__ = [
    "placeholder_feature_summary",
    "FEATURE_CATALOG",
    "generate_feature_catalog",
    "add_meteorological_rolling_features",
    "add_hydrological_rolling_features",
    "prepare_future_alignment_feature_layer",
]

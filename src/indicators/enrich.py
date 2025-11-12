"""Indicator enrichment module for opt-in indicator computation.

This module provides selective indicator computation on immutable core datasets,
ensuring that only requested indicators are calculated without mutating the
original ingestion result.
"""

import logging
import time
from dataclasses import dataclass
from typing import Any

import pandas as pd
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

from src.io.hash_utils import compute_dataframe_hash
from src.indicators.errors import (
    DuplicateIndicatorError,
    ImmutabilityViolationError,
    UnknownIndicatorError,
)
from src.indicators.registry.builtins import register_builtins
from src.indicators.registry.store import get_registry


logger = logging.getLogger(__name__)

# Core columns that must remain unchanged
CORE_COLUMNS = ["timestamp_utc", "open", "high", "low", "close", "volume", "is_gap"]


@dataclass
class EnrichmentResult:
    """Result of indicator enrichment operation.

    Attributes:
        core: Reference to original core DataFrame (unchanged).
        enriched: New DataFrame with indicator columns appended.
        indicators_applied: List of successfully computed indicator names.
        failed_indicators: List of indicators that failed (non-strict only).
        runtime_seconds: Total enrichment runtime.
    """

    core: pd.DataFrame
    enriched: pd.DataFrame
    indicators_applied: list[str]
    failed_indicators: list[str]
    runtime_seconds: float


def enrich(
    core_ref: Any,  # IngestionResult reference
    indicators: list[str],
    params: dict[str, Any] = None,
    strict: bool = False,
) -> EnrichmentResult:
    """Compute requested indicators on core dataset without mutation.

    Args:
        core_ref: Reference to IngestionResult from ingestion.
        indicators: List of indicator names to compute.
        params: Optional parameters for indicator computation.
        strict: If True, abort on first unknown indicator error.

    Returns:
        EnrichmentResult: Enriched dataset with metadata.

    Raises:
        ValueError: If duplicate indicator names or core ref invalid (always).
        KeyError: If unknown indicator and strict=True.
        ImmutabilityViolationError: If core dataset mutated during enrichment.
    """
    start_time = time.perf_counter()

    # Ensure builtins are registered
    register_builtins()

    # Validate inputs
    if core_ref is None:
        raise ValueError("core_ref cannot be None")

    # Extract core DataFrame (support both IngestionResult and raw DataFrame)
    if hasattr(core_ref, "data"):
        core_df = core_ref.data
    elif isinstance(core_ref, pd.DataFrame):
        core_df = core_ref
    else:
        raise ValueError(
            f"core_ref must be IngestionResult or DataFrame, got {type(core_ref)}"
        )

    if params is None:
        params = {}

    # Check for duplicate indicators
    duplicates = {ind for ind in indicators if indicators.count(ind) > 1}
    if duplicates:
        raise DuplicateIndicatorError(duplicates)

    # Compute hash of core columns before enrichment
    core_hash_before = compute_dataframe_hash(core_df, CORE_COLUMNS)

    # Resolve indicators and check for unknown names
    registry = get_registry()
    failed_indicators: list[str] = []
    indicators_applied: list[str] = []
    enriched_df = core_df.copy()

    # Create progress bar for indicator computation
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
    ) as progress_bar:
        task = progress_bar.add_task(
            "Computing indicators...", total=len(indicators)
        )

        for indicator_name in indicators:
            spec = registry.get(indicator_name)

            if spec is None:
                # Unknown indicator
                available = registry.list_all()
                if strict:
                    raise UnknownIndicatorError(indicator_name, available)

                # Non-strict mode: collect failure and continue
                failed_indicators.append(indicator_name)
                logger.warning(
                    "Unknown indicator '%s' (non-strict mode), skipping",
                    indicator_name,
                )
                progress_bar.advance(task)
                continue

            # Check dependencies
            missing_deps = set(spec.requires) - set(enriched_df.columns)
            if missing_deps:
                error_msg = (
                    f"Indicator '{indicator_name}' requires missing columns: "
                    f"{missing_deps}"
                )
                if strict:
                    raise ValueError(error_msg)

                failed_indicators.append(indicator_name)
                logger.warning("%s (non-strict mode), skipping", error_msg)
                progress_bar.advance(task)
                continue

            # Compute indicator
            try:
                progress_bar.update(
                    task, description=f"Computing {indicator_name}..."
                )
                indicator_params = params.get(indicator_name, spec.params)
                result = spec.compute(enriched_df, indicator_params)

                # Add computed columns to enriched DataFrame
                for col_name, col_series in result.items():
                    enriched_df[col_name] = col_series

                indicators_applied.append(indicator_name)
                # Don't log during progress - causes messy output
                progress_bar.advance(task)

            except Exception as e:  # pylint: disable=broad-except
                error_msg = f"Error computing indicator '{indicator_name}': {e}"
                if strict:
                    raise ValueError(error_msg) from e

                failed_indicators.append(indicator_name)
                logger.warning("%s (non-strict mode), skipping", error_msg)
                progress_bar.advance(task)

    # Verify immutability: core columns must not have changed
    core_hash_after = compute_dataframe_hash(enriched_df, CORE_COLUMNS)
    if core_hash_before != core_hash_after:
        raise ImmutabilityViolationError(core_hash_before, core_hash_after)

    runtime = time.perf_counter() - start_time

    logger.info(
        "Enrichment complete: %d indicators applied, %d failed, %.3f seconds",
        len(indicators_applied),
        len(failed_indicators),
        runtime,
    )

    return EnrichmentResult(
        core=core_df,
        enriched=enriched_df,
        indicators_applied=indicators_applied,
        failed_indicators=failed_indicators,
        runtime_seconds=runtime,
    )

"""Indicator input extraction for strategy preprocessing.

This module provides utilities to extract indicator input requirements from
strategies and validate that indicator data is available before signal generation.
"""

import logging
from typing import Optional

import numpy as np
import polars as pl

from src.strategy.base import Strategy


logger = logging.getLogger(__name__)


class IndicatorInputExtractor:
    """Extract and validate indicator inputs from strategy requirements.

    Ensures that all indicators declared by a strategy are available in the
    dataset before signal generation begins. Supports indicator registry audit
    as required by FR-003 (indicator mapping) and FR-004 (strategy ownership).

    Example:
        >>> extractor = IndicatorInputExtractor(strategy)
        >>> extractor.validate_inputs(df)
        >>> indicator_names = extractor.get_indicator_names()
    """

    def __init__(self, strategy: Strategy):
        """Initialize indicator input extractor.

        Args:
            strategy: Strategy instance declaring indicator requirements
        """
        self.strategy = strategy
        self._indicator_names: Optional[list[str]] = None
        self._validated = False

    def get_indicator_names(self) -> list[str]:
        """Get ordered list of indicator names from strategy.

        Returns:
            List of indicator names in declaration order

        Raises:
            ValueError: If strategy metadata missing or invalid
        """
        if self._indicator_names is not None:
            return self._indicator_names

        if not hasattr(self.strategy, "metadata"):
            msg = "Strategy must provide metadata property"
            logger.error(msg)
            raise ValueError(msg)

        metadata = self.strategy.metadata
        if not hasattr(metadata, "required_indicators"):
            msg = "Strategy metadata must declare required_indicators"
            logger.error(msg)
            raise ValueError(msg)

        self._indicator_names = list(metadata.required_indicators)
        logger.debug(
            "Extracted %d indicator names from strategy '%s'",
            len(self._indicator_names),
            metadata.name,
        )

        return self._indicator_names

    def validate_inputs(self, df: pl.DataFrame) -> None:
        """Validate that all required indicators exist in DataFrame.

        Args:
            df: Polars DataFrame containing indicator columns

        Raises:
            ValueError: If any required indicators are missing
        """
        indicator_names = self.get_indicator_names()
        missing_cols = set(indicator_names) - set(df.columns)

        if missing_cols:
            msg = "Missing required indicator columns: %s"
            logger.error(msg, sorted(missing_cols))
            raise ValueError(msg % str(sorted(missing_cols)))

        self._validated = True
        logger.info(
            "Validated %d indicator inputs: %s",
            len(indicator_names),
            indicator_names,
        )

    def validate_arrays(self, indicator_arrays: dict[str, np.ndarray]) -> None:
        """Validate that all required indicators exist in array dictionary.

        Args:
            indicator_arrays: Dictionary mapping indicator names to NumPy arrays

        Raises:
            ValueError: If any required indicators are missing
        """
        indicator_names = self.get_indicator_names()
        missing_names = set(indicator_names) - set(indicator_arrays.keys())

        if missing_names:
            msg = "Missing required indicator arrays: %s"
            logger.error(msg, sorted(missing_names))
            raise ValueError(msg % str(sorted(missing_names)))

        self._validated = True
        logger.debug(
            "Validated %d indicator arrays present",
            len(indicator_names),
        )

    def is_validated(self) -> bool:
        """Check if inputs have been validated.

        Returns:
            True if validate_inputs or validate_arrays was called successfully
        """
        return self._validated

    def extract_indicator_mapping(self) -> dict[str, int]:
        """Extract ordered indicator mapping (name -> index).

        Returns:
            Dictionary mapping indicator names to their declaration order index

        Raises:
            ValueError: If strategy metadata missing
        """
        indicator_names = self.get_indicator_names()
        return {name: idx for idx, name in enumerate(indicator_names)}

    def get_zero_indicator_flag(self) -> bool:
        """Check if strategy declares zero indicators.

        Returns:
            True if strategy declares no indicators (edge case)
        """
        indicator_names = self.get_indicator_names()
        return len(indicator_names) == 0

"""
Reproducibility service for backtest determinism.

This module tracks all inputs and operations that affect backtest results,
computing a cumulative hash that uniquely identifies a complete backtest run.
This enables verification that two runs with identical inputs produce identical
outputs, as required by Constitution Principle VI.

The service accumulates:
- Strategy parameters hash
- Data manifest reference
- Candle processing order
- Random seed (if applicable)
- Software version
"""

import hashlib
import logging
from datetime import datetime


logger = logging.getLogger(__name__)


class ReproducibilityTracker:
    """
    Tracks backtest inputs for reproducibility verification.

    Accumulates cryptographic hashes of all inputs and operations that affect
    backtest results. The final hash serves as a fingerprint of the entire run.

    Attributes:
        parameters_hash: SHA-256 hash of strategy parameters.
        manifest_ref: Reference to data manifest file.
        candle_count: Number of candles processed.
        version: Software version string.
        start_time: UTC timestamp when tracking started.
        _hash_accumulator: Running SHA-256 hash.

    Examples:
        >>> from datetime import datetime, timezone
        >>> tracker = ReproducibilityTracker(
        ...     parameters_hash="a1b2c3d4...",
        ...     manifest_ref="data/manifests/EURUSD_M5_2025-01.json",
        ...     version="0.1.0"
        ... )
        >>> tracker.update_candle_count(100)
        >>> hash_value = tracker.finalize()
        >>> len(hash_value)
        64
    """

    def __init__(
        self,
        parameters_hash: str,
        manifest_ref: str,
        version: str = "0.1.0",
    ):
        """
        Initialize reproducibility tracker.

        Args:
            parameters_hash: SHA-256 hash of strategy parameters.
            manifest_ref: Path to data manifest file.
            version: Software version string (default "0.1.0").
        """
        self.parameters_hash = parameters_hash
        self.manifest_ref = manifest_ref
        self.version = version
        self.start_time = datetime.utcnow()
        self.candle_count = 0
        self._finalized_hash: str | None = None  # Cache finalized hash

        # Initialize hash accumulator
        self._hash_accumulator = hashlib.sha256()
        self._hash_accumulator.update(parameters_hash.encode("utf-8"))
        self._hash_accumulator.update(manifest_ref.encode("utf-8"))
        self._hash_accumulator.update(version.encode("utf-8"))

        logger.debug(
            "Reproducibility tracker initialized: params_hash=%s..., manifest=%s, version=%s",
            parameters_hash[:16],
            manifest_ref,
            version,
        )

    def update_candle_count(self, count: int) -> None:
        """
        Update the number of candles processed.

        Args:
            count: Total candles processed so far.

        Examples:
            >>> tracker = ReproducibilityTracker("hash123", "manifest.json")
            >>> tracker.update_candle_count(100)
            >>> tracker.candle_count
            100
        """
        self.candle_count = count
        logger.debug("Candle count updated: %d", count)

    def add_event(self, event_type: str, event_data: str) -> None:
        """
        Record a backtest event in the hash accumulator.

        Use this to track significant events that should affect reproducibility,
        such as signal generation or trade execution.

        Args:
            event_type: Type of event (e.g., "SIGNAL_GENERATED", "TRADE_CLOSED").
            event_data: Event details (e.g., signal ID, execution ID).

        Examples:
            >>> tracker = ReproducibilityTracker("hash123", "manifest.json")
            >>> tracker.add_event("SIGNAL_GENERATED", "signal_abc123")
            >>> tracker.add_event("TRADE_CLOSED", "execution_xyz789")
        """
        event_str = f"{event_type}|{event_data}"
        self._hash_accumulator.update(event_str.encode("utf-8"))
        logger.debug("Event recorded: %s - %s...", event_type, event_data[:32])

    def finalize(self) -> str:
        """
        Compute final reproducibility hash.

        Incorporates candle count and returns the cumulative SHA-256 hash.
        This hash uniquely identifies the backtest run's inputs and operations.

        The result is cached after first call to ensure idempotency.

        Returns:
            64-character hexadecimal SHA-256 hash string.

        Examples:
            >>> tracker = ReproducibilityTracker("hash123", "manifest.json")
            >>> tracker.update_candle_count(1000)
            >>> tracker.add_event("SIGNAL_GENERATED", "sig1")
            >>> final_hash = tracker.finalize()
            >>> len(final_hash)
            64
        """
        # Return cached hash if already finalized
        if self._finalized_hash is not None:
            return self._finalized_hash

        # Add candle count to final hash
        self._hash_accumulator.update(str(self.candle_count).encode("utf-8"))

        final_hash = self._hash_accumulator.hexdigest()

        # Cache the result
        self._finalized_hash = final_hash

        logger.info(
            "Reproducibility hash finalized: %s... (candles=%d, version=%s)",
            final_hash[:16],
            self.candle_count,
            self.version,
        )

        return final_hash

    def verify(self, expected_hash: str) -> bool:
        """
        Verify that finalized hash matches expected value.

        Args:
            expected_hash: Expected SHA-256 hash to compare against.

        Returns:
            True if hashes match, False otherwise.

        Examples:
            >>> tracker = ReproducibilityTracker("hash123", "manifest.json")
            >>> tracker.update_candle_count(100)
            >>> hash1 = tracker.finalize()
            >>> tracker.verify(hash1)
            True
            >>> tracker.verify("wrong_hash")
            False
        """
        actual_hash = self.finalize()
        matches = actual_hash == expected_hash

        if matches:
            logger.info("Reproducibility verification PASSED")
        else:
            logger.warning(
                "Reproducibility verification FAILED: expected=%s..., actual=%s...",
                expected_hash[:16],
                actual_hash[:16],
            )

        return matches

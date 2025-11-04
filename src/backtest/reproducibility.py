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

**Partition Metadata Integration (Feature 004-timeseries-dataset):**

When using partition-based backtesting (test/validation splits), reproducibility
tracking should reference the partition metadata file to ensure consistent data:

1. **Metadata Reference**: Instead of raw file manifests, reference the partition
   metadata.json which contains:
   - Exact row counts (total_rows, test_rows, validation_rows)
   - Timestamp ranges (start_timestamp, end_timestamp, validation_start_timestamp)
   - Build timestamp and source files
   - Gap/overlap counts

2. **Partition-Aware Tracking**: For split-mode backtests, create separate
   reproducibility trackers for test and validation partitions:

   ```python
   # Test partition tracker
   test_tracker = ReproducibilityTracker(
       parameters_hash=params_hash,
       manifest_ref="price_data/processed/eurusd/metadata.json#test",
       version="0.1.0"
   )

   # Validation partition tracker
   val_tracker = ReproducibilityTracker(
       parameters_hash=params_hash,
       manifest_ref="price_data/processed/eurusd/metadata.json#validation",
       version="0.1.0"
   )
   ```

3. **Benefits**:
   - Ensures exact same partition boundaries across runs
   - Prevents accidental data contamination (test/validation mixing)
   - Enables verification that validation metrics came from held-out data
   - Documents which dataset version was used (via build_timestamp)

4. **Verification**: When comparing backtest runs, verify:
   - Same partition metadata (by hash or timestamp)
   - Same strategy parameters
   - Same software version
   → Identical results guaranteed (SC-004)

Implementation: T037
"""

# pylint: disable=line-too-long

import hashlib
import json
import logging
from datetime import datetime
from typing import Any, Sequence


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


def generate_deterministic_run_id(
    strategies: Sequence[str],
    weights: Sequence[float],
    data_manifest_refs: Sequence[str],
    config_params: dict[str, Any] | None = None,
    seed: int = 0,
) -> str:
    """
    Generate a deterministic SHA-256 based run identifier for multi-strategy runs.

    Combines strategy names, weights, data manifest references, optional
    configuration parameters, and a seed into a stable hash. Ensures
    identical inputs yield identical IDs across runs (FR-018, SC-008).

    Args:
        strategies: Ordered list of strategy names.
        weights: Ordered list of strategy weights.
        data_manifest_refs: List of data manifest file paths/checksums.
        config_params: Optional dict of global configuration parameters.
        seed: Random seed for reproducibility (default 0).

    Returns:
        Lowercase hexadecimal SHA-256 hash (truncated to 16 characters).

    Examples:
        >>> generate_deterministic_run_id(
        ...     strategies=["alpha", "beta"],
        ...     weights=[0.6, 0.4],
        ...     data_manifest_refs=["data/manifests/eurusd.json"]
        ... )  # doctest: +ELLIPSIS
        '...'
        >>> id1 = generate_deterministic_run_id(["alpha"], [1.0], ["data.json"])
        >>> id2 = generate_deterministic_run_id(["alpha"], [1.0], ["data.json"])
        >>> id1 == id2
        True
    """
    # Build canonical representation
    payload = {
        "strategies": list(strategies),
        "weights": [float(w) for w in weights],
        "data_manifest_refs": list(data_manifest_refs),
        "config_params": config_params or {},
        "seed": seed,
    }

    # Serialize to stable JSON (sorted keys)
    canonical_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))

    # Hash with SHA-256
    hash_obj = hashlib.sha256(canonical_json.encode("utf-8"))
    full_hash = hash_obj.hexdigest()

    # Truncate to 16 characters for readability
    return full_hash[:16]

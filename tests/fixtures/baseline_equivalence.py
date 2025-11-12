"""Baseline equivalence fixture ingestion helper for testing.

This module provides utilities for loading and comparing baseline test fixtures
to verify that optimized implementations produce equivalent results.
"""

import json
import logging
from pathlib import Path

import numpy as np


logger = logging.getLogger(__name__)


def load_baseline_fixture(fixture_path: str) -> dict:
    """Load baseline test fixture from JSON file.

    Args:
        fixture_path: Path to JSON fixture file

    Returns:
        Dictionary containing baseline data

    Raises:
        FileNotFoundError: If fixture file does not exist
        ValueError: If fixture file is invalid JSON
    """
    fixture_file = Path(fixture_path)

    if not fixture_file.exists():
        msg = "Baseline fixture not found: %s"
        logger.error(msg, fixture_path)
        raise FileNotFoundError(msg % fixture_path)

    try:
        with open(fixture_path, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        msg = "Invalid JSON in baseline fixture: %s"
        logger.error(msg, str(e))
        raise ValueError(msg % str(e)) from e

    logger.info("Loaded baseline fixture from %s", fixture_path)

    return data


def save_baseline_fixture(data: dict, fixture_path: str) -> None:
    """Save baseline test fixture to JSON file.

    Args:
        data: Dictionary containing baseline data
        fixture_path: Path to JSON fixture file
    """
    fixture_file = Path(fixture_path)
    fixture_file.parent.mkdir(parents=True, exist_ok=True)

    with open(fixture_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)

    logger.info("Saved baseline fixture to %s", fixture_path)


def compare_signal_counts(
    baseline_count: int, actual_count: int, tolerance: int = 0
) -> tuple[bool, str]:
    """Compare signal counts for equivalence.

    Args:
        baseline_count: Expected signal count from baseline
        actual_count: Actual signal count from implementation
        tolerance: Acceptable difference (default: 0 for exact match)

    Returns:
        Tuple of (is_equivalent, message)
    """
    diff = abs(actual_count - baseline_count)

    if diff <= tolerance:
        msg = "Signal count match: baseline=%d, actual=%d (diff=%d)"
        logger.info(msg, baseline_count, actual_count, diff)
        return True, msg % (baseline_count, actual_count, diff)

    msg = "Signal count mismatch: baseline=%d, actual=%d (diff=%d, tolerance=%d)"
    logger.error(msg, baseline_count, actual_count, diff, tolerance)
    return False, msg % (baseline_count, actual_count, diff, tolerance)


def compare_trade_counts(
    baseline_count: int, actual_count: int, tolerance: int = 0
) -> tuple[bool, str]:
    """Compare trade counts for equivalence.

    Args:
        baseline_count: Expected trade count from baseline
        actual_count: Actual trade count from implementation
        tolerance: Acceptable difference (default: 0 for exact match)

    Returns:
        Tuple of (is_equivalent, message)
    """
    diff = abs(actual_count - baseline_count)

    if diff <= tolerance:
        msg = "Trade count match: baseline=%d, actual=%d (diff=%d)"
        logger.info(msg, baseline_count, actual_count, diff)
        return True, msg % (baseline_count, actual_count, diff)

    msg = "Trade count mismatch: baseline=%d, actual=%d (diff=%d, tolerance=%d)"
    logger.error(msg, baseline_count, actual_count, diff, tolerance)
    return False, msg % (baseline_count, actual_count, diff, tolerance)


def compare_pnl_values(
    baseline_pnl: float, actual_pnl: float, tolerance_pct: float = 0.5
) -> tuple[bool, str]:
    """Compare PnL values for equivalence with percentage tolerance.

    Args:
        baseline_pnl: Expected PnL from baseline
        actual_pnl: Actual PnL from implementation
        tolerance_pct: Acceptable percentage difference (default: 0.5%)

    Returns:
        Tuple of (is_equivalent, message)
    """
    if baseline_pnl == 0.0:
        # Handle zero baseline case
        if abs(actual_pnl) < 1e-10:
            return True, "PnL match: both zero"
        msg = "PnL mismatch: baseline=0, actual=%.4f"
        logger.error(msg, actual_pnl)
        return False, msg % actual_pnl

    pct_diff = abs((actual_pnl - baseline_pnl) / baseline_pnl) * 100.0

    if pct_diff <= tolerance_pct:
        msg = "PnL match: baseline=%.4f, actual=%.4f (diff=%.2f%%)"
        logger.info(msg, baseline_pnl, actual_pnl, pct_diff)
        return True, msg % (baseline_pnl, actual_pnl, pct_diff)

    msg = "PnL mismatch: baseline=%.4f, actual=%.4f (diff=%.2f%%, tolerance=%.2f%%)"
    logger.error(msg, baseline_pnl, actual_pnl, pct_diff, tolerance_pct)
    return False, msg % (baseline_pnl, actual_pnl, pct_diff, tolerance_pct)


def compare_arrays(
    baseline_arr: np.ndarray,
    actual_arr: np.ndarray,
    name: str = "array",
    atol: float = 1e-8,
    rtol: float = 1e-5,
) -> tuple[bool, str]:
    """Compare NumPy arrays for equivalence.

    Args:
        baseline_arr: Expected array from baseline
        actual_arr: Actual array from implementation
        name: Name of array for logging (default: 'array')
        atol: Absolute tolerance (default: 1e-8)
        rtol: Relative tolerance (default: 1e-5)

    Returns:
        Tuple of (is_equivalent, message)
    """
    # Check shape match
    if baseline_arr.shape != actual_arr.shape:
        msg = "%s shape mismatch: baseline=%s, actual=%s"
        logger.error(msg, name, baseline_arr.shape, actual_arr.shape)
        return False, msg % (name, baseline_arr.shape, actual_arr.shape)

    # Check value equivalence
    if np.allclose(baseline_arr, actual_arr, atol=atol, rtol=rtol):
        msg = "%s values match (atol=%.2e, rtol=%.2e)"
        logger.info(msg, name, atol, rtol)
        return True, msg % (name, atol, rtol)

    # Find maximum difference for reporting
    max_diff = np.max(np.abs(baseline_arr - actual_arr))
    msg = "%s values mismatch: max_diff=%.6e (atol=%.2e, rtol=%.2e)"
    logger.error(msg, name, max_diff, atol, rtol)
    return False, msg % (name, max_diff, atol, rtol)


class EquivalenceReport:
    """Report of equivalence validation results.

    Tracks multiple comparisons and provides overall pass/fail status.
    """

    def __init__(self):
        """Initialize empty equivalence report."""
        self.comparisons: list[tuple[str, bool, str]] = []

    def add_comparison(self, name: str, passed: bool, message: str) -> None:
        """Add a comparison result to the report.

        Args:
            name: Name of comparison
            passed: Whether comparison passed
            message: Detailed message about comparison
        """
        self.comparisons.append((name, passed, message))
        logger.debug("Added comparison '%s': %s", name, "PASS" if passed else "FAIL")

    def all_passed(self) -> bool:
        """Check if all comparisons passed.

        Returns:
            True if all comparisons passed, False otherwise
        """
        return all(passed for _, passed, _ in self.comparisons)

    def get_summary(self) -> str:
        """Get summary of equivalence validation.

        Returns:
            Multi-line string summary of all comparisons
        """
        lines = ["Equivalence Validation Report", "=" * 50]

        for name, passed, message in self.comparisons:
            status = "✓ PASS" if passed else "✗ FAIL"
            lines.append(f"{status}: {name}")
            lines.append(f"  {message}")

        overall = "✓ ALL PASSED" if self.all_passed() else "✗ SOME FAILED"
        lines.append("=" * 50)
        lines.append(f"Overall: {overall} ({len(self.comparisons)} comparisons)")

        return "\n".join(lines)

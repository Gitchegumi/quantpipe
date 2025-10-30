"""
Latency sampling and percentile computation.

This module tracks processing latency samples and computes statistical
summaries (mean, p95, p99). Useful for performance monitoring and ensuring
the backtest meets latency requirements (SC-010: <100ms p95).
"""

import logging
from collections.abc import Sequence

import numpy as np
from numpy.typing import NDArray


logger = logging.getLogger(__name__)


class LatencySampler:
    """
    Collects and analyzes latency samples.

    Accumulates latency measurements (in milliseconds) and computes statistical
    summaries including mean, median, and percentiles.

    Attributes:
        samples: List of latency samples in milliseconds.

    Examples:
        >>> sampler = LatencySampler()
        >>> sampler.add_sample(10.5)
        >>> sampler.add_sample(15.2)
        >>> sampler.add_sample(12.8)
        >>> sampler.mean()
        12.833...
        >>> sampler.p95()
        14.95...
    """

    def __init__(self):
        """Initialize empty latency sampler."""
        self.samples: list[float] = []

    def add_sample(self, latency_ms: float) -> None:
        """
        Add a latency sample.

        Args:
            latency_ms: Latency measurement in milliseconds.

        Examples:
            >>> sampler = LatencySampler()
            >>> sampler.add_sample(5.0)
            >>> len(sampler.samples)
            1
        """
        self.samples.append(latency_ms)

    def add_samples(self, latencies_ms: Sequence[float]) -> None:
        """
        Add multiple latency samples.

        Args:
            latencies_ms: Sequence of latency measurements in milliseconds.

        Examples:
            >>> sampler = LatencySampler()
            >>> sampler.add_samples([5.0, 10.0, 15.0])
            >>> len(sampler.samples)
            3
        """
        self.samples.extend(latencies_ms)

    def mean(self) -> float:
        """
        Compute mean latency.

        Returns:
            Mean latency in milliseconds, or NaN if no samples.

        Examples:
            >>> sampler = LatencySampler()
            >>> sampler.add_samples([10.0, 20.0, 30.0])
            >>> sampler.mean()
            20.0
        """
        if not self.samples:
            return np.nan

        return float(np.mean(self.samples))

    def median(self) -> float:
        """
        Compute median latency.

        Returns:
            Median latency in milliseconds, or NaN if no samples.

        Examples:
            >>> sampler = LatencySampler()
            >>> sampler.add_samples([10.0, 20.0, 30.0])
            >>> sampler.median()
            20.0
        """
        if not self.samples:
            return np.nan

        return float(np.median(self.samples))

    def percentile(self, p: float) -> float:
        """
        Compute arbitrary percentile.

        Args:
            p: Percentile to compute (0-100).

        Returns:
            Latency at given percentile in milliseconds, or NaN if no samples.

        Examples:
            >>> sampler = LatencySampler()
            >>> sampler.add_samples([10.0, 20.0, 30.0, 40.0, 50.0])
            >>> sampler.percentile(95)
            48.0
        """
        if not self.samples:
            return np.nan

        return float(np.percentile(self.samples, p))

    def p95(self) -> float:
        """
        Compute 95th percentile latency.

        Returns:
            95th percentile latency in milliseconds, or NaN if no samples.

        Examples:
            >>> sampler = LatencySampler()
            >>> sampler.add_samples([10.0, 20.0, 30.0, 40.0, 50.0])
            >>> sampler.p95()
            48.0
        """
        return self.percentile(95)

    def p99(self) -> float:
        """
        Compute 99th percentile latency.

        Returns:
            99th percentile latency in milliseconds, or NaN if no samples.

        Examples:
            >>> sampler = LatencySampler()
            >>> sampler.add_samples(list(range(1, 101)))  # 1-100 ms
            >>> sampler.p99()
            99.0
        """
        return self.percentile(99)

    def summary(self) -> dict[str, float]:
        """
        Get summary statistics.

        Returns:
            Dictionary with mean, median, p95, p99 latencies.

        Examples:
            >>> sampler = LatencySampler()
            >>> sampler.add_samples([10.0, 20.0, 30.0])
            >>> summary = sampler.summary()
            >>> summary["mean"]
            20.0
            >>> summary["p95"]
            29.0
        """
        return {
            "mean": self.mean(),
            "median": self.median(),
            "p95": self.p95(),
            "p99": self.p99(),
            "count": len(self.samples),
        }

    def reset(self) -> None:
        """
        Clear all samples.

        Examples:
            >>> sampler = LatencySampler()
            >>> sampler.add_samples([10.0, 20.0])
            >>> sampler.reset()
            >>> len(sampler.samples)
            0
        """
        self.samples.clear()
        logger.debug("Latency sampler reset")


def compute_percentiles(
    values: NDArray[np.float64], percentiles: Sequence[float]
) -> dict[str, float]:
    """
    Compute multiple percentiles from array of values.

    Args:
        values: Array of numeric values.
        percentiles: List of percentiles to compute (0-100).

    Returns:
        Dictionary mapping percentile labels to values.

    Examples:
        >>> import numpy as np
        >>> values = np.array([10.0, 20.0, 30.0, 40.0, 50.0])
        >>> result = compute_percentiles(values, [50, 95, 99])
        >>> result["p50"]
        30.0
        >>> result["p95"]
        48.0
    """
    if len(values) == 0:
        return {f"p{int(p)}": np.nan for p in percentiles}

    result = {}
    for p in percentiles:
        result[f"p{int(p)}"] = float(np.percentile(values, p))

    return result

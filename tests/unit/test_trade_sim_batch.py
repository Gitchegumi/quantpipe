"""Unit tests for batch trade simulation module.

Tests vectorized simulation logic, fidelity vs baseline (FR-006, SC-006),
optional JIT paths, and speedup validation (SC-002: ≥10× improvement).
"""

# pylint: disable=unused-import, fixme

import pytest
from src.backtest.trade_sim_batch import (
    simulate_trades_batch,
    simulate_trades_batch_jit,
)


class TestBatchSimulation:
    """Test suite for batch trade simulation functions."""

    def test_simulate_trades_batch_basic(self):
        """Batch simulation returns results for all entries."""
        # TODO: Implement test with mock entries and price data

    def test_fidelity_vs_baseline(self):
        """Batch results match baseline within tolerances (FR-006)."""
        # TODO: Implement fidelity comparison test
        # - Price difference ≤ 1e-6
        # - Index exact match
        # - PnL difference ≤ 0.01%

    def test_jit_path_optional(self):
        """JIT path raises NotImplementedError until implemented."""
        # TODO: Test guarded import and fallback logic

    # TODO: Add tests for:
    # - Same-bar exit edge case (duration == 1)
    # - Overlapping trades performance (remains within SC-001)
    # - Stop loss / take profit accuracy

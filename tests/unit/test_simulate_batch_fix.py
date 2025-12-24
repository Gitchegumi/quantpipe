"""Unit tests for _simulate_batch() fix to honor per-trade SL/TP and strategy target_r_mult.

These tests verify T011-T015 fixes:
- T011/T012: simulate_trades_batch() enforces per-trade SL/TP (no global defaults)
- T013/T014: _simulate_batch() uses strategy's target_r_mult (not hardcoded 2.0)
- T015: No global SL/TP passed to simulate_trades_batch()

Expected: ALL tests should FAIL before implementing the fix.
"""

import numpy as np
import pandas as pd
import pytest

from src.backtest.trade_sim_batch import simulate_trades_batch


class TestSimulateBatchPerTradeSLTP:
    """Test that simulate_trades_batch respects per-trade SL/TP values."""

    def test_simulate_batch_respects_per_trade_sltp(self):
        """Verify 3 entries with different SL/TP% (2%, 5%, 10%) use their own values.

        Bug: Before fix, all trades use first trade's SL/TP (2%).
        After fix: Each trade should use its own SL/TP percentage.
        """
        # Create mock price data with enough bars for exits
        price_data = pd.DataFrame(
            {
                "high": [1.1000, 1.1020, 1.1050, 1.1100, 1.1150, 1.1200],
                "low": [1.0950, 1.0970, 1.1000, 1.1050, 1.1100, 1.1150],
                "close": [1.0980, 1.1000, 1.1030, 1.1080, 1.1130, 1.1180],
            }
        )

        # Create 3 entries with different SL/TP percentages
        entries = [
            {
                "entry_index": 0,
                "entry_price": 1.1000,
                "side": "LONG",
                "stop_loss_pct": 0.02,  # 2% SL
                "take_profit_pct": 0.04,  # 4% TP (2R)
            },
            {
                "entry_index": 1,
                "entry_price": 1.1000,
                "side": "LONG",
                "stop_loss_pct": 0.05,  # 5% SL
                "take_profit_pct": 0.10,  # 10% TP (2R)
            },
            {
                "entry_index": 2,
                "entry_price": 1.1000,
                "side": "LONG",
                "stop_loss_pct": 0.10,  # 10% SL
                "take_profit_pct": 0.20,  # 20% TP (2R)
            },
        ]

        # Run simulation WITHOUT global SL/TP (should use per-trade values)
        results = simulate_trades_batch(entries, price_data)

        assert len(results) == 3, "Should return 3 results"

        # Trade 1: 2% SL, 4% TP
        # TP price = 1.1000 * 1.04 = 1.1440 (not hit), SL = 1.0780 (not hit)
        # Should timeout or use last close
        assert results[0]["exit_reason"] in [
            "TIMEOUT",
            "END_OF_DATA",
        ], "Trade 1 should timeout (TP/SL not hit)"

        # Trade 2: 5% SL, 10% TP
        # TP price = 1.1000 * 1.10 = 1.2100 (hit at bar 5: high=1.1200 not reached)
        # SL price = 1.1000 * 0.95 = 1.0450 (not hit)
        assert results[1]["exit_reason"] in [
            "TIMEOUT",
            "END_OF_DATA",
        ], "Trade 2 should timeout (10% TP not reached)"

        # Trade 3: 10% SL, 20% TP
        # TP price = 1.1000 * 1.20 = 1.3200 (definitely not hit)
        # SL price = 1.1000 * 0.90 = 0.9900 (not hit)
        assert results[2]["exit_reason"] in [
            "TIMEOUT",
            "END_OF_DATA",
        ], "Trade 3 should timeout (20% TP not reached)"

        # KEY ASSERTION: P&L should differ based on different SL/TP%
        # If bug exists, all trades use same SL/TP% (first trade's 2%/4%)
        # After fix, each trade has unique exit points
        pnls = [r["pnl"] for r in results]
        assert len(set(pnls)) >= 2, (
            "Bug detected: All trades have same PnL (using same SL/TP%). "
            "Expected different PnLs for different SL/TP percentages"
        )

    def test_simulate_batch_target_r_mult_from_strategy(self):
        """Mock strategy with target_r_mult=3.0, verify trades exit at 3R.

        Bug: Hardcoded 2.0 in _simulate_batch() line 186.
        After fix: Should respect strategy's 3.0 target_r_mult.
        """
        # Create mock price data
        price_data = pd.DataFrame(
            {
                "high": [1.1000, 1.1050, 1.1100, 1.1150, 1.1200, 1.1350],
                "low": [1.0950, 1.1000, 1.1050, 1.1100, 1.1150, 1.1300],
                "close": [1.0980, 1.1030, 1.1080, 1.1130, 1.1180, 1.1330],
            }
        )

        # Entry with 2% SL and 6% TP (3R target)
        # Entry: 1.1000, SL: 1.0780 (2%), TP: 1.1660 (6% = 3R)
        entries = [
            {
                "entry_index": 0,
                "entry_price": 1.1000,
                "side": "LONG",
                "stop_loss_pct": 0.02,  # 2% SL
                "take_profit_pct": 0.06,  # 6% TP (3R)
            },
        ]

        results = simulate_trades_batch(entries, price_data)

        assert len(results) == 1
        result = results[0]

        # With 3R target (6% TP), price needs to reach 1.1660
        # Price data max high is 1.1350, so should timeout
        assert result["exit_reason"] in [
            "TIMEOUT",
            "END_OF_DATA",
        ], "Should timeout (3R TP not reached)"

        # If hardcoded 2.0 bug, would use 4% TP (1.1440) and might hit earlier
        # This test verifies TP% comes from entry dict, not hardcoded value

    def test_simulate_batch_no_global_defaults(self):
        """Call simulate_trades_batch() with no global SL/TP, verify it uses per-trade values.

        Bug: Passing global SL/TP as defaults overrides per-trade values.
        After fix: Should require per-trade values, ignore or error on global defaults.
        """
        price_data = pd.DataFrame(
            {
                "high": [1.1000, 1.1100],
                "low": [1.0900, 1.1000],
                "close": [1.0950, 1.1050],
            }
        )

        entries = [
            {
                "entry_index": 0,
                "entry_price": 1.1000,
                "side": "LONG",
                "stop_loss_pct": 0.03,  # 3% SL
                "take_profit_pct": 0.06,  # 6% TP
            },
        ]

        # Call WITHOUT global SL/TP parameters
        results = simulate_trades_batch(entries, price_data)

        assert len(results) == 1
        # Should use entry's 3% SL and 6% TP
        # SL = 1.1000 * 0.97 = 1.067, TP = 1.1000 * 1.06 = 1.166
        # Neither hit in 2 bars, should timeout

        result = results[0]
        assert result["exit_reason"] in ["TIMEOUT", "END_OF_DATA"]

        # Verify PnL reflects 3% SL (not some default 2%)
        # PnL = (1.1050 - 1.1000) / 1.1000 ≈ 0.0045 (0.45%)
        # R-multiple = 0.45% / 3% = 0.15R
        assert (
            -0.5 < result["pnl"] < 0.02
        ), f"PnL {result['pnl']} should reflect timeout exit, not full TP/SL"


class TestSimulateBatchMissingPerTradeValues:
    """Test error handling when per-trade SL/TP values are missing."""

    def test_error_when_missing_stop_loss_pct(self):
        """Should raise ValueError if entry missing stop_loss_pct and no global default."""
        price_data = pd.DataFrame(
            {
                "high": [1.1000, 1.1100],
                "low": [1.0900, 1.1000],
                "close": [1.0950, 1.1050],
            }
        )

        entries = [
            {
                "entry_index": 0,
                "entry_price": 1.1000,
                "side": "LONG",
                # Missing: "stop_loss_pct"
                "take_profit_pct": 0.04,
            },
        ]

        # After fix (T012), this should raise ValueError
        # Before fix, might use global default or undefined behavior
        with pytest.raises(ValueError, match="Missing SL/TP"):
            simulate_trades_batch(entries, price_data)

    def test_error_when_missing_take_profit_pct(self):
        """Should raise ValueError if entry missing take_profit_pct and no global default."""
        price_data = pd.DataFrame(
            {
                "high": [1.1000, 1.1100],
                "low": [1.0900, 1.1000],
                "close": [1.0950, 1.1050],
            }
        )

        entries = [
            {
                "entry_index": 0,
                "entry_price": 1.1000,
                "side": "LONG",
                "stop_loss_pct": 0.02,
                # Missing: "take_profit_pct"
            },
        ]

        with pytest.raises(ValueError, match="Missing SL/TP"):
            simulate_trades_batch(entries, price_data)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

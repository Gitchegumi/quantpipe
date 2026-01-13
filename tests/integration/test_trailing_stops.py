import unittest
from unittest.mock import MagicMock, patch
import pandas as pd
import numpy as np
import pytest
from datetime import datetime, timedelta

from src.backtest.trade_sim_batch import simulate_trades_batch
from src.risk.config import StopPolicyConfig


class TestTrailingStops(unittest.TestCase):
    def setUp(self):
        # Create synthetic price data: Uptrend then crash
        # Price goes 100 -> 110 -> 105 -> 120 -> 90
        # channel width (High-Low) approx 2.0
        dates = pd.date_range(start="2024-01-01", periods=100, freq="1min")
        self.df = pd.DataFrame(
            {
                "timestamp_utc": dates,
                "open": np.linspace(100, 110, 100),
                "high": np.linspace(101, 111, 100),
                "low": np.linspace(99, 109, 100),
                "close": np.linspace(100, 110, 100),
            }
        )
        # Add a sharp drop at index 50
        self.df.loc[50:, "open"] = np.linspace(110, 90, 50)
        self.df.loc[50:, "high"] = np.linspace(111, 91, 50)
        self.df.loc[50:, "low"] = np.linspace(109, 89, 50)  # Low drops below 100
        self.df.loc[50:, "close"] = np.linspace(110, 90, 50)

        self.indicators = {
            "atr": np.full(100, 1.0),  # ATR = 1.0
            "sma_50": np.linspace(95, 105, 100),  # SMA rising below price
        }

    def test_atr_trailing_long(self):
        """Test ATR trailing stop for a LONG position."""
        # Entry at index 0, Price 100.
        # Stop Distance = 3.0 (Mult 3.0 * ATR 1.0) -> avoids immediate noise stop.
        # Initial SL = 97.0.

        entries = [
            {
                "entry_index": 0,
                "entry_price": 100.0,
                "side": "LONG",
                "take_profit_pct": 0.5,
                "stop_loss_pct": 0.05,  # Initial 95
            }
        ]

        trailing_config = {"type": "ATR_Trailing", "multiplier": 3.0}

        results = simulate_trades_batch(
            entries,
            self.df,
            trailing_config=trailing_config,
            indicators=self.indicators,
        )

        res = results[0]
        self.assertEqual(res["exit_reason"], "STOP_LOSS")
        # Should persist until the drop at index 50
        self.assertGreater(res["exit_price"], 95.0)
        self.assertTrue(
            50 <= res["exit_index"] <= 60,
            f"Exit index {res['exit_index']} too early, expected >50",
        )

    def test_ma_trailing_long(self):
        """Test MA trailing stop for a LONG position."""
        entries = [
            {
                "entry_index": 0,
                "entry_price": 100.0,
                "side": "LONG",
                "take_profit_pct": 0.5,
                "stop_loss_pct": 0.10,
            }
        ]

        trailing_config = {"type": "MA_Trailing", "ma_col": "sma_50"}

        results = simulate_trades_batch(
            entries,
            self.df,
            trailing_config=trailing_config,
            indicators=self.indicators,
        )

        res = results[0]
        self.assertEqual(res["exit_reason"], "STOP_LOSS")
        self.assertGreater(res["exit_price"], 95.0)

    def test_fixed_pips_trailing_short(self):
        """Test Fixed Pips trailing for a SHORT position."""
        # Modify data: Downtrend 100 -> 90
        # High-Low spread 2.0
        dates = pd.date_range(start="2024-01-01", periods=100, freq="1min")
        df_short = pd.DataFrame(
            {
                "timestamp_utc": dates,
                "open": np.linspace(100, 90, 100),
                "high": np.linspace(101, 91, 100),
                "low": np.linspace(99, 89, 100),
                "close": np.linspace(100, 90, 100),
            }
        )
        # Spike up at 60 (later to allow trailing)
        df_short.loc[60:, "open"] = np.linspace(90, 110, 40)
        df_short.loc[60:, "high"] = np.linspace(91, 111, 40)
        df_short.loc[60:, "low"] = np.linspace(89, 109, 40)
        df_short.loc[60:, "close"] = np.linspace(90, 110, 40)

        entries = [
            {
                "entry_index": 0,
                "entry_price": 100.0,
                "side": "SHORT",
                "take_profit_pct": 0.5,
                "stop_loss_pct": 0.10,  # Initial SL 110
            }
        ]

        # Fixed pips 3.0 (300 pips)
        trailing_config = {"type": "FixedPips_Trailing", "pips": 300, "pip_size": 0.01}

        results = simulate_trades_batch(
            entries,
            df_short,
            trailing_config=trailing_config,
            indicators=self.indicators,
        )

        res = results[0]
        self.assertEqual(res["exit_reason"], "STOP_LOSS")
        # It should exit at the spike (index 60+)
        self.assertGreater(res["exit_index"], 60)
        # Trailed lower than 110
        self.assertLess(res["exit_price"], 110.0)

    def test_trailing_trigger_activation(self):
        """Test that trailing only activates after trigger R-multiple is reached."""
        # Entry 100, SL 98 (2.0 dist = 1R).
        # Trigger 1.0R = Price 102.

        # Scenario A: Price goes to 101 (0.5R), then crashes.
        # Should stop at Initial SL (98).
        df_fail = pd.DataFrame(
            {
                "timestamp_utc": pd.date_range("2024-01-01", periods=10, freq="1min"),
                "open": np.full(10, 100.0),
                "high": np.array(
                    [100, 101.5, 95, 95, 95, 95, 95, 95, 95, 95]
                ),  # Max 101.5 < 102
                "low": np.array([99, 100, 90, 90, 90, 90, 90, 90, 90, 90]),
                "close": np.full(10, 95.0),
            }
        )

        entries = [
            {
                "entry_index": 0,
                "entry_price": 100.0,
                "side": "LONG",
                "take_profit_pct": 0.10,
                "stop_loss_pct": 0.02,  # 2% -> 2.0 dist -> SL 98.0
            }
        ]

        trailing_config = {"type": "ATR_Trailing", "multiplier": 1.5, "trigger_r": 1.0}

        indicators = {"atr": np.full(10, 1.0)}

        results = simulate_trades_batch(
            entries, df_fail, trailing_config=trailing_config, indicators=indicators
        )
        res = results[0]
        self.assertEqual(res["exit_reason"], "STOP_LOSS")
        self.assertAlmostEqual(
            res["exit_price"],
            98.0,
            places=4,
            msg="Should stop at initial SL if trigger not reached",
        )

        # Scenario B: Price goes to 103 (1.5R), then crashes.
        # Trigger reached. Max High 103. ATR Stop (1.5) -> 103 - 1.5 = 101.5.
        # Crash to 90. Exit at 101.5.
        df_success = pd.DataFrame(
            {
                "timestamp_utc": pd.date_range("2024-01-01", periods=10, freq="1min"),
                "open": np.full(10, 100.0),
                "high": np.array(
                    [100, 103.0, 90, 90, 90, 90, 90, 90, 90, 90]
                ),  # Max 103 > 102
                "low": np.array([99, 102.0, 80, 80, 80, 80, 80, 80, 80, 80]),
                "close": np.full(10, 90.0),
            }
        )

        results = simulate_trades_batch(
            entries, df_success, trailing_config=trailing_config, indicators=indicators
        )
        res = results[0]
        self.assertEqual(res["exit_reason"], "STOP_LOSS")
        self.assertGreater(
            res["exit_price"], 100.0, "Should have trailed significantly above entry"
        )


if __name__ == "__main__":
    unittest.main()

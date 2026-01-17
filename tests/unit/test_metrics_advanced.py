"""
Unit tests for advanced metrics (Feature 027).
"""

import pytest
import numpy as np
from datetime import datetime, timedelta, timezone

from src.models.core import TradeExecution
from src.backtest.metrics import (
    compute_metrics,
    compute_sortino_ratio,
    compute_avg_duration,
    compute_streaks,
)


@pytest.fixture
def sample_executions():
    base_time = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
    return [
        TradeExecution(
            signal_id="1",
            open_timestamp=base_time,
            close_timestamp=base_time + timedelta(hours=1),
            entry_fill_price=1.0,
            exit_fill_price=1.1,
            exit_reason="TARGET",
            pnl_r=1.0,
            slippage_entry_pips=0,
            slippage_exit_pips=0,
        ),
        TradeExecution(
            signal_id="2",
            open_timestamp=base_time + timedelta(days=1),
            close_timestamp=base_time + timedelta(days=1, hours=2),
            entry_fill_price=1.0,
            exit_fill_price=0.9,
            exit_reason="STOP",
            pnl_r=-1.0,
            slippage_entry_pips=0,
            slippage_exit_pips=0,
        ),
        TradeExecution(
            signal_id="3",
            open_timestamp=base_time + timedelta(days=2),
            close_timestamp=base_time + timedelta(days=2, hours=3),
            entry_fill_price=1.0,
            exit_fill_price=1.2,
            exit_reason="TARGET",
            pnl_r=2.0,
            slippage_entry_pips=0,
            slippage_exit_pips=0,
        ),
    ]


def test_avg_duration(sample_executions):
    # Durations: 1h (3600s), 2h (7200s), 3h (10800s)
    # Mean: 2h (7200s)
    avg = compute_avg_duration(sample_executions)
    assert avg == 7200.0


def test_streaks():
    # Sequence: +5, +2, -1, -1, -1, +3
    pnl = np.array([5.0, 2.0, -1.0, -1.0, -1.0, 3.0])

    assert compute_streaks(pnl, win=True) == 2
    assert compute_streaks(pnl, win=False) == 3


def test_sortino_ratio():
    # Returns: +1, -1, +2
    # Mean = 2/3 = 0.666...
    # Downside: -1 is current. 0 for others.
    # Semi-variance = (min(0, 1)^2 + min(0, -1)^2 + min(0, 2)^2) / 3
    # = (0 + 1 + 0) / 3 = 0.333...
    # Downside Dev = sqrt(0.333...) = 0.577...
    # Sortino = 0.666... / 0.577... = 1.1547...

    pnl = np.array([1.0, -1.0, 2.0])
    ratio = compute_sortino_ratio(pnl)

    # Validation calculation
    exp_mean = 2.0 / 3.0
    exp_dev = np.sqrt(1.0 / 3.0)
    exp_sortino = exp_mean / exp_dev

    assert ratio == pytest.approx(exp_sortino, 0.001)


def test_sortino_no_losses():
    pnl = np.array([1.0, 2.0, 3.0])
    assert compute_sortino_ratio(pnl) == np.inf


def test_full_metrics_integration(sample_executions):
    metrics = compute_metrics(sample_executions)

    # Check new fields
    assert metrics.avg_trade_duration_seconds == 7200.0
    assert metrics.sortino_ratio > 0
    # PnL: +1, -1, +2
    # Streak Win: 1 (Pos 0), then Loss, then Win (Pos 2). Streak is 1.
    # Wait, Pos 0 is Win. Pos 1 is Loss. Pos 2 is Win.
    # Max Streak Win = 1.
    assert metrics.max_consecutive_wins == 1
    assert metrics.max_consecutive_losses == 1

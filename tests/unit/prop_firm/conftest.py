"""
Fixtures for Prop Firm unit tests.
"""

from datetime import UTC, datetime, timedelta

import pytest

from src.models.core import TradeExecution
from src.risk.prop_firm.models import ChallengeConfig


@pytest.fixture()
def base_config():
    return ChallengeConfig(
        program_id="TEST_10K",
        account_size=10000.0,
        max_daily_loss_pct=0.04,  # 4% ($400)
        max_total_drawdown_pct=0.05,  # 5% ($500)
        profit_target_pct=0.10,  # 10% ($1000)
        min_trading_days=3,
        drawdown_type="TRAILING",
        drawdown_mode="CLOSED_BALANCE",
    )


@pytest.fixture()
def create_trade():
    def _create(pnl_val: float, date_offset_days: int = 0, risk_amount: float = 100.0):
        base_time = datetime(2025, 1, 1, 12, 0, tzinfo=UTC)
        ts = base_time + timedelta(days=date_offset_days)

        # pnl_r = pnl_val / risk_amount
        pnl_r = pnl_val / risk_amount if risk_amount != 0 else 0

        return TradeExecution(
            signal_id="test",
            direction="LONG",
            open_timestamp=ts,
            entry_fill_price=1.0,
            close_timestamp=ts + timedelta(hours=1),
            exit_fill_price=1.1,
            exit_reason="TARGET",
            pnl_r=pnl_r,
            risk_amount=risk_amount,
            slippage_entry_pips=0,
            slippage_exit_pips=0,
        )

    return _create


@pytest.fixture()
def scaling_config():
    from src.risk.prop_firm.models import ScalingConfig

    return ScalingConfig(
        review_period_months=4,
        profit_target_pct=0.10,
        increments=[10000.0, 20000.0, 40000.0],
    )

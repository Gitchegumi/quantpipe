"""
Evaluator for Prop Firm rules (CTI).
"""

from datetime import UTC, datetime
from typing import Optional

from src.models.core import TradeExecution

from .models import ChallengeConfig, LevelResult


def evaluate_challenge(
    executions: list[TradeExecution],
    config: ChallengeConfig,
    level_id: int = 1,
    start_date: Optional[datetime] = None,
) -> LevelResult:
    """
    Evaluate a sequence of trades against CTI rules.

    Args:
        executions: List of completed trades.
        config: Challenge configuration.
        level_id: Identifier for this level/attempt segment.
        start_date: Override start date (e.g. for resets). If None, uses first trade open.

    Returns:
        LevelResult object containing status and metrics.
    """
    if not executions:
        return LevelResult(
            level_id=level_id,
            start_tier_balance=config.account_size,
            end_balance=config.account_size,
            status="INCOMPLETE",  # Or 'NO_TRADES'
            start_date=datetime.now(UTC),
            end_date=datetime.now(UTC),
            trade_count=0,
            pnl=0.0,
            metrics=None,
        )

    # Sort executions by close time
    sorted_execs = sorted(executions, key=lambda x: x.close_timestamp)

    start_time = start_date if start_date else sorted_execs[0].open_timestamp
    end_time = sorted_execs[-1].close_timestamp

    current_balance = config.account_size

    # Pre-calculate daily balances
    daily_start_balances = {}  # date -> float
    current_day = start_time.date()
    daily_start_balances[current_day] = current_balance

    # Drawdown limits
    max_total_dd_amount = config.account_size * config.max_total_drawdown_pct

    peak_balance = config.account_size
    low_balance = config.account_size

    profitable_days = set()

    failure_reason = None
    failure_date = None
    status = "IN_PROGRESS"

    total_net_pnl = 0.0

    idx = 0
    for idx, trade in enumerate(sorted_execs):
        trade_date = trade.close_timestamp.date()

        # New Day Logic
        if trade_date > current_day:
            daily_start_balances[trade_date] = current_balance
            current_day = trade_date

        # Calculate PnL in dollars
        pnl_dollars = trade.pnl_r * trade.risk_amount

        if trade.risk_amount == 0 and trade.pnl_r != 0:
            # Attempt fallback based on percent
            estimated_risk = config.account_size * (trade.risk_percent or 0.01)
            pnl_dollars = trade.pnl_r * estimated_risk

        total_net_pnl += pnl_dollars
        current_balance += pnl_dollars

        # Track Peak Balance
        if current_balance > peak_balance:
            peak_balance = current_balance

        if current_balance < low_balance:
            low_balance = current_balance

        # Track Profitable Days
        if pnl_dollars > 0:
            profitable_days.add(trade_date)

        # 1. Total Drawdown
        if config.drawdown_type == "STATIC":
            dd_floor = config.account_size - max_total_dd_amount
            if current_balance < dd_floor:
                status = "FAILED_DRAWDOWN"
                failure_reason = f"Static Drawdown Violation: Bal {current_balance:.2f} < Floor {dd_floor:.2f}"
                failure_date = trade.close_timestamp
                break
        else:
            # TRAILING (Classic HWM)
            dd_floor = peak_balance - max_total_dd_amount
            if current_balance < dd_floor:
                status = "FAILED_DRAWDOWN"
                failure_reason = f"Trailing Drawdown Violation: Bal {current_balance:.2f} < Floor {dd_floor:.2f} (Peak {peak_balance:.2f})"
                failure_date = trade.close_timestamp
                break

        # 2. Daily Loss
        if config.max_daily_loss_pct is not None:
            day_start_bal = daily_start_balances.get(trade_date, config.account_size)
            daily_loss_limit = day_start_bal - (
                config.account_size * config.max_daily_loss_pct
            )

            if current_balance < daily_loss_limit:
                status = "FAILED_DAILY"
                failure_reason = f"Daily Loss Violation: Bal {current_balance:.2f} < Limit {daily_loss_limit:.2f} (DayStart {day_start_bal:.2f})"
                failure_date = trade.close_timestamp
                break

        # 3. Time Limit (if set)
        if config.max_time_days:
            elapsed = (trade.close_timestamp - start_time).days
            if elapsed > config.max_time_days:
                status = "FAILED_TIME"
                failure_reason = (
                    f"Time Limit Violation: {elapsed} > {config.max_time_days}"
                )
                failure_date = trade.close_timestamp
                break

    # End of Loop - Check Success
    if status == "IN_PROGRESS":
        target_amount = config.account_size * config.profit_target_pct
        current_profit = current_balance - config.account_size

        if current_profit >= target_amount:
            if len(profitable_days) >= config.min_trading_days:
                status = "PASSED"

    # Calculate standard metrics for this level
    from src.backtest.metrics import calculate_metrics

    level_metrics = None
    if executions:
        trades_in_level = sorted_execs[: idx + 1] if failure_date else sorted_execs

        if trades_in_level:
            ms = calculate_metrics(trades_in_level)
            level_metrics = ms

    return LevelResult(
        level_id=level_id,
        start_tier_balance=config.account_size,
        end_balance=current_balance,
        status=status,
        start_date=start_time,
        end_date=end_time if failure_date is None else failure_date,
        trade_count=len(executions) if failure_date is None else idx + 1,
        pnl=total_net_pnl,
        metrics=level_metrics,
        failure_reason=failure_reason,
    )

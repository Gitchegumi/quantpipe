"""
Scaling logic for CTI Prop Firm progression.
"""

from datetime import datetime, timedelta, date, timezone
from typing import List, Optional, Dict
from dateutil.relativedelta import relativedelta

from src.models.core import TradeExecution, MetricsSummary
from src.backtest.metrics import calculate_metrics

from .models import ChallengeConfig, ScalingConfig, LifeResult, ScalingReport


def evaluate_scaling(
    executions: List[TradeExecution],
    challenge_config: ChallengeConfig,
    scaling_config: ScalingConfig,
) -> ScalingReport:
    """
    Simulate scaling progression with resets and periodic reviews.

    Args:
        executions: Full history of trades.
        challenge_config: Base challenge rules (drawdown limits).
        scaling_config: Scaling rules (review period, increments).

    Returns:
        ScalingReport containing multiple lives.
    """
    if not executions:
        return ScalingReport(lives=[], total_duration_days=0, active_life_index=-1)

    # Sort trades
    sorted_execs = sorted(executions, key=lambda x: x.close_timestamp)

    lives: List[LifeResult] = []

    # State
    current_tier_idx = 0
    start_tier_balance = scaling_config.increments[0]

    # Base account size from challenge config (used for scaling factor reference if needed,
    # but scaling plan increments are absolute amounts usually.
    # If increments match account_size, scale factor is 1.0.
    # If starting at 10k and increment is 10k, factor 1.0.
    # If resizing is needed: Scale = CurrentTier / InitialSetupAccountSize.
    # We assume 'challenge_config.account_size' is the basis for the backtest's risk sizing.
    base_account_size = challenge_config.account_size

    current_balance = start_tier_balance
    current_life_trades: List[TradeExecution] = []
    current_life_start = sorted_execs[0].open_timestamp
    # For the first life, min_review_date is relative to the start of the first trade.
    # For subsequent lives, it's relative to the start of that life (which is the end of the previous life).
    # This variable will be updated when a new life starts.
    min_review_date = current_life_start + relativedelta(
        months=scaling_config.review_period_months
    )

    # Daily Balance Tracking for Loss Limit
    daily_start_balances = {}
    current_day = current_life_start.date()
    daily_start_balances[current_day] = current_balance

    peak_balance = current_balance

    # Metrics tracking per profit target/review period
    # To check "2 profitable months", we need to track monthly PnL accumulator.
    monthly_pnls = {}  # Year-Month -> float

    life_id_counter = 1

    # Loop state
    i = 0
    while i < len(sorted_execs):
        trade = sorted_execs[i]
        trade_date = trade.close_timestamp.date()
        trade_month = (trade.close_timestamp.year, trade.close_timestamp.month)

        # 1. Update Day (carry over balance)
        if trade_date > current_day:
            daily_start_balances[trade_date] = current_balance
            current_day = trade_date

        # 2. Virtual PnL
        scale_factor = start_tier_balance / base_account_size

        # Calculate Base PnL (as if on base account)
        base_pnl = trade.pnl_r * trade.risk_amount
        if trade.risk_amount == 0 and trade.pnl_r != 0:
            # Fallback
            base_pnl = trade.pnl_r * (base_account_size * (trade.risk_percent or 0.01))

        # Scale it
        scaled_pnl = base_pnl * scale_factor

        current_balance += scaled_pnl
        current_life_trades.append(
            trade
        )  # Note: this trade object has original values. Maybe clone?
        # For metrics calculation later we might want adjusted values.
        # But calculates_metrics uses pnl_r which matches.
        # Dollar metrics might be wrong if computed on original trades.
        # But standard metrics are R-based.

        # Update monthly PnL
        monthly_pnls[trade_month] = monthly_pnls.get(trade_month, 0.0) + scaled_pnl

        # Update Peak
        if current_balance > peak_balance:
            peak_balance = current_balance

        # 3. Check Failure Rules
        status = "IN_PROGRESS"

        # Drawdown Limit Handling
        # Need to fetch max_drawdown_amount for CURRENT TIER.
        # Usually it is % of Current Tier or Fixed Amount scaled?
        # ChallengeConfig has max_total_drawdown_pct.
        max_dd_amount = start_tier_balance * challenge_config.max_total_drawdown_pct

        # Daily Loss
        max_daily_loss_pct = challenge_config.max_daily_loss_pct

        failed = False
        fail_reason = ""

        # Check Total Drawdown
        if challenge_config.drawdown_type == "STATIC":
            floor = start_tier_balance - max_dd_amount
        else:
            floor = peak_balance - max_dd_amount

        if current_balance < floor:
            status = "FAILED_DRAWDOWN"
            failed = True

        # Check Daily Loss
        if not failed and max_daily_loss_pct:
            day_start = daily_start_balances.get(
                trade_date, current_balance
            )  # Fallback if same day
            limit = day_start - (start_tier_balance * max_daily_loss_pct)
            if current_balance < limit:
                status = "FAILED_DAILY"
                failed = True

        # Review Check (if not failed)
        promoted = False
        if not failed:

            # We only check for promotion if we have passed the minimum review period (e.g. 4 months)
            if trade.close_timestamp >= min_review_date:
                # Check Promotion Criteria
                profit = current_balance - start_tier_balance
                target = start_tier_balance * scaling_config.profit_target_pct

                if profit >= target:
                    # Target Hit! Now check "Profitable Months" in the LAST X months window.
                    # Window: [Current Time - Review Period, Current Time]
                    window_start = trade.close_timestamp - relativedelta(
                        months=scaling_config.review_period_months
                    )

                    prof_months_count = 0
                    current_month_key = (
                        trade.close_timestamp.year,
                        trade.close_timestamp.month,
                    )

                    # Iterate daily/monthly PnLs to find profitable months.
                    # Note: "With two of those months closing in profit".
                    # Typically implies we only count fully closed months, OR months that have ended relative to NOW?
                    # But monthly_pnls stores accumulated PnL for (Year, Month).
                    # We iterate the keys.
                    for (y, m), pnl_val in monthly_pnls.items():
                        # Determine "end of month" or just use month start for filtering?
                        # Let's say a month "falls within" the window if it overlaps?
                        # "Last 4 months" relative to May 15th are Jan 15-May 15.
                        # Months entirely or mostly in that window: Feb, Mar, Apr.
                        # May is partial. Jan is partial.
                        # Simplest interpretation: Look at months strictly between Window Start and Current?
                        # Or just check last N chronological months excluding current?

                        # Let's use: Count any month (y,m) where (y,m) != current_month
                        # AND (y,m) is chronologically AFTER or EQUAL to the month of window_start.
                        # Example: Current May (5). Window Start Jan (1).
                        # Months in window: 1, 2, 3, 4. (Excluding 5).
                        # If pnl > 0 for 2 of them => Pass.

                        # Construct a date for comparison (start of month)
                        m_date = datetime(y, m, 1, tzinfo=window_start.tzinfo)

                        # Check strictly AFTER window start date?
                        # Or simply >= month of window start?
                        # Let's check strict timestamps logic to be safe.
                        # m_date >= window_start? (Jan 1 >= Jan 15? No. So Jan excluded. Correct).
                        # Feb 1 >= Jan 15? Yes. Feb included. Correct.

                        if (y, m) == current_month_key:
                            continue  # Ignore current partial month

                        if m_date >= window_start and pnl_val > 0:
                            prof_months_count += 1

                    if prof_months_count >= 2:
                        # Promote!
                        status = "PROMOTED"
                        promoted = True

        # 4. Handle State Change (Fail or Promote)
        if failed or promoted:
            # Close Life
            life_result = LifeResult(
                life_id=life_id_counter,
                start_tier_balance=start_tier_balance,
                end_balance=current_balance,
                status=status,
                start_date=current_life_start,
                end_date=trade.close_timestamp,
                trade_count=len(current_life_trades),
                pnl=current_balance - start_tier_balance,
                metrics=calculate_metrics(current_life_trades),  # R-metrics
            )
            lives.append(life_result)
            life_id_counter += 1

            # Setup Next Life
            if failed:
                # RESET Logic
                current_tier_idx = 0  # Back to start
                start_tier_balance = scaling_config.increments[0]
            else:  # promoted
                # Scale Up
                current_tier_idx = min(
                    current_tier_idx + 1, len(scaling_config.increments) - 1
                )
                start_tier_balance = scaling_config.increments[current_tier_idx]

            # Reset Life State
            current_balance = start_tier_balance
            current_life_trades = []
            current_life_start = trade.close_timestamp  # Start next life immediately?
            # Or open of NEXT trade?
            # Using current close as boundary.
            peak_balance = current_balance
            monthly_pnls = {}
            daily_start_balances = {trade_date: current_balance}

            if i + 1 < len(sorted_execs):
                next_review_date = sorted_execs[i + 1].open_timestamp + relativedelta(
                    months=scaling_config.review_period_months
                )
            else:
                next_review_date = datetime.max.replace(tzinfo=timezone.utc)

        # Advance loop
        i += 1

    # Close Final Life (always report active life state)
    life_result = LifeResult(
        life_id=life_id_counter,
        start_tier_balance=start_tier_balance,
        end_balance=current_balance,
        status="IN_PROGRESS",  # Always IN_PROGRESS if we ran out of data
        start_date=current_life_start,
        end_date=(
            sorted_execs[-1].close_timestamp if sorted_execs else current_life_start
        ),
        trade_count=len(current_life_trades),
        pnl=current_balance - start_tier_balance,
        metrics=calculate_metrics(current_life_trades),
    )
    lives.append(life_result)

    return ScalingReport(
        lives=lives,
        total_duration_days=(
            sorted_execs[-1].close_timestamp - sorted_execs[0].open_timestamp
        ).days,
        active_life_index=len(lives) - 1,
    )

"""
Scaling logic for CTI Prop Firm progression.
"""

from datetime import datetime

from dateutil.relativedelta import relativedelta

from src.backtest.metrics import calculate_metrics
from src.models.core import TradeExecution

from .models import ChallengeConfig, LifeResult, ScalingConfig, ScalingReport


def evaluate_scaling(
    executions: list[TradeExecution],
    challenge_config: ChallengeConfig,
    scaling_config: ScalingConfig,
    cost_map: dict[float, float] | None = None,
) -> ScalingReport:
    """
    Simulate scaling progression with resets and periodic reviews.

    Args:
        executions: Full history of trades.
        challenge_config: Base challenge rules (drawdown limits).
        scaling_config: Scaling rules (review period, increments).
        cost_map: Optional mapping of account_size -> fee for buy-backs.

    Returns:
        ScalingReport containing multiple lives.
    """
    if not executions:
        return ScalingReport(lives=[], total_duration_days=0, active_life_index=-1)

    # Sort trades
    sorted_execs = sorted(executions, key=lambda x: x.close_timestamp)

    lives: list[LifeResult] = []

    # Financial Tracking
    wallet_balance = -challenge_config.cost
    total_costs = challenge_config.cost
    total_payouts = 0.0

    # State
    current_tier_idx = 0
    start_tier_balance = scaling_config.increments[0]

    base_account_size = challenge_config.account_size

    current_balance = start_tier_balance
    current_life_trades: list[TradeExecution] = []
    current_life_start = sorted_execs[0].open_timestamp
    min_review_date = current_life_start + relativedelta(
        months=scaling_config.review_period_months
    )

    # Daily Balance Tracking for Loss Limit
    daily_start_balances = {}
    current_day = current_life_start.date()
    daily_start_balances[current_day] = current_balance

    peak_balance = current_balance
    monthly_pnls = {}  # Year-Month -> float
    life_id_counter = 1

    # Loop state
    i = 0
    while i < len(sorted_execs):
        trade = sorted_execs[i]
        trade_date = trade.close_timestamp.date()
        trade_month = (trade.close_timestamp.year, trade.close_timestamp.month)

        if trade_date > current_day:
            daily_start_balances[trade_date] = current_balance
            current_day = trade_date

        scale_factor = start_tier_balance / base_account_size
        base_pnl = trade.pnl_r * trade.risk_amount
        if trade.risk_amount == 0 and trade.pnl_r != 0:
            base_pnl = trade.pnl_r * (base_account_size * (trade.risk_percent or 0.01))

        scaled_pnl = base_pnl * scale_factor
        current_balance += scaled_pnl
        current_life_trades.append(trade)
        monthly_pnls[trade_month] = monthly_pnls.get(trade_month, 0.0) + scaled_pnl

        if current_balance > peak_balance:
            peak_balance = current_balance

        status = "IN_PROGRESS"
        max_dd_amount = start_tier_balance * challenge_config.max_total_drawdown_pct
        max_daily_loss_pct = challenge_config.max_daily_loss_pct

        failed = False
        if challenge_config.drawdown_type == "STATIC":
            floor = start_tier_balance - max_dd_amount
        else:
            floor = peak_balance - max_dd_amount

        if current_balance < floor:
            status = "FAILED_DRAWDOWN"
            failed = True

        if not failed and max_daily_loss_pct:
            day_start = daily_start_balances.get(trade_date, current_balance)
            limit = day_start - (start_tier_balance * max_daily_loss_pct)
            if current_balance < limit:
                status = "FAILED_DAILY"
                failed = True

        promoted = False
        if not failed:
            if trade.close_timestamp >= min_review_date:
                profit = current_balance - start_tier_balance
                target = start_tier_balance * scaling_config.profit_target_pct

                if profit >= target:
                    window_start = trade.close_timestamp - relativedelta(
                        months=scaling_config.review_period_months
                    )
                    prof_months_count = 0
                    current_month_key = (trade.close_timestamp.year, trade.close_timestamp.month)

                    for (y, m), pnl_val in monthly_pnls.items():
                        m_date = datetime(y, m, 1, tzinfo=window_start.tzinfo)
                        if (y, m) == current_month_key: continue
                        if m_date >= window_start and pnl_val > 0:
                            prof_months_count += 1

                    if prof_months_count >= 2:
                        status = "PROMOTED"
                        promoted = True

        if failed or promoted:
            # Payout Logic (Upon promotion or failure, collect profit)
            profit_at_end = current_balance - start_tier_balance
            if profit_at_end > 0:
                payout = profit_at_end * challenge_config.payout_share
                total_payouts += payout
                wallet_balance += payout

            # Close Life
            life_result = LifeResult(
                life_id=life_id_counter,
                start_tier_balance=start_tier_balance,
                end_balance=current_balance,
                status=status,
                start_date=current_life_start,
                end_date=trade.close_timestamp,
                trade_count=len(current_life_trades),
                pnl=profit_at_end,
                metrics=calculate_metrics(current_life_trades),
            )
            lives.append(life_result)
            life_id_counter += 1

            # Setup Next Life
            if failed:
                # Buy-back Logic: pick highest affordable tier
                next_tier_balance = scaling_config.increments[0] # Default to smallest
                
                if cost_map:
                    # Sort tiers descending to find largest affordable
                    affordable_tiers = sorted([t for t, cost in cost_map.items() if cost <= wallet_balance], reverse=True)
                    if affordable_tiers:
                        next_tier_balance = affordable_tiers[0]
                    
                    # Subtract cost
                    buyback_cost = cost_map.get(next_tier_balance, 0.0)
                    if buyback_cost == 0 and next_tier_balance == scaling_config.increments[0]:
                        # Default cost if not in map for some reason
                        buyback_cost = challenge_config.cost
                    
                    wallet_balance -= buyback_cost
                    total_costs += buyback_cost
                else:
                    # Legacy behavior: restart at bottom, wallet ignores cost
                    wallet_balance -= challenge_config.cost
                    total_costs += challenge_config.cost

                # Find index in scaling increments
                try:
                    current_tier_idx = scaling_config.increments.index(next_tier_balance)
                except ValueError:
                    current_tier_idx = 0
                start_tier_balance = next_tier_balance
            else:
                current_tier_idx = min(current_tier_idx + 1, len(scaling_config.increments) - 1)
                start_tier_balance = scaling_config.increments[current_tier_idx]

            # Reset Life State
            current_balance = start_tier_balance
            current_life_trades = []
            current_life_start = trade.close_timestamp
            peak_balance = current_balance
            monthly_pnls = {}
            daily_start_balances = {trade_date: current_balance}
            min_review_date = current_life_start + relativedelta(months=scaling_config.review_period_months)

        i += 1

    # Final Life result
    life_result = LifeResult(
        life_id=life_id_counter,
        start_tier_balance=start_tier_balance,
        end_balance=current_balance,
        status="IN_PROGRESS",
        start_date=current_life_start,
        end_date=(sorted_execs[-1].close_timestamp if sorted_execs else current_life_start),
        trade_count=len(current_life_trades),
        pnl=current_balance - start_tier_balance,
        metrics=calculate_metrics(current_life_trades),
    )
    lives.append(life_result)

    return ScalingReport(
        lives=lives,
        total_duration_days=(sorted_execs[-1].close_timestamp - sorted_execs[0].open_timestamp).days,
        active_life_index=len(lives) - 1,
        wallet_balance=wallet_balance,
        net_payouts=total_payouts,
        total_costs=total_costs,
    )

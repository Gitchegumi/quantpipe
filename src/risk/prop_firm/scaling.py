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
    """
    if not executions:
        return ScalingReport(lives=[], total_duration_days=0, active_life_index=-1)

    sorted_execs = sorted(executions, key=lambda x: x.close_timestamp)
    lives: list[LifeResult] = []

    # Financial Tracking
    wallet_balance = -challenge_config.cost
    total_costs = challenge_config.cost
    total_payouts = 0.0

    # Initial State
    is_in_evaluation = challenge_config.program_id in ["1STEP", "2STEP"]
    current_step = 1 if is_in_evaluation else 0
    
    current_tier_idx = 0
    start_tier_balance = scaling_config.increments[0]
    base_account_size = challenge_config.account_size

    current_balance = start_tier_balance
    current_life_trades: list[TradeExecution] = []
    current_life_start = sorted_execs[0].open_timestamp
    
    # Review period check starts after min period
    min_review_date = current_life_start + relativedelta(months=scaling_config.review_period_months)

    # Daily Balance Tracking
    daily_start_balances = {}
    current_day = current_life_start.date()
    daily_start_balances[current_day] = current_balance

    peak_balance = current_balance
    monthly_pnls = {}
    tier_profit_accrued = 0.0
    life_id_counter = 1
    life_withdrawals = 0.0
    pending_buyback_cost = 0.0
    beginning_wallet = wallet_balance

    i = 0
    while i < len(sorted_execs):
        trade = sorted_execs[i]
        trade_date = trade.close_timestamp.date()
        trade_month = (trade.close_timestamp.year, trade.close_timestamp.month)

        if trade_date > current_day:
            # End of Month Payout Logic (Only for Funded Accounts)
            if not is_in_evaluation and trade_date.month != current_day.month:
                profit_this_month = current_balance - start_tier_balance
                if profit_this_month > 0:
                    payout = profit_this_month * challenge_config.payout_share
                    total_payouts += payout
                    life_withdrawals += payout
                    wallet_balance += payout
                    # Reset balance to tier start after payout
                    current_balance = start_tier_balance
                    peak_balance = current_balance
            
            daily_start_balances[trade_date] = current_balance
            current_day = trade_date

        scale_factor = start_tier_balance / base_account_size
        base_pnl = trade.pnl_r * trade.risk_amount
        if trade.risk_amount == 0 and trade.pnl_r != 0:
            base_pnl = trade.pnl_r * (base_account_size * (trade.risk_percent or 0.01))

        scaled_pnl = base_pnl * scale_factor
        current_balance += scaled_pnl
        tier_profit_accrued += scaled_pnl
        current_life_trades.append(trade)
        monthly_pnls[trade_month] = monthly_pnls.get(trade_month, 0.0) + scaled_pnl

        if current_balance > peak_balance:
            peak_balance = current_balance

        max_dd_amount = start_tier_balance * challenge_config.max_total_drawdown_pct
        failed = False
        floor = start_tier_balance - max_dd_amount if challenge_config.drawdown_type == "STATIC" else peak_balance - max_dd_amount
        
        if current_balance < floor:
            status = "FAILED_DRAWDOWN"
            failed = True

        if not failed and challenge_config.max_daily_loss_pct:
            day_start = daily_start_balances.get(trade_date, current_balance)
            limit = day_start - (start_tier_balance * challenge_config.max_daily_loss_pct)
            if current_balance < limit:
                status = "FAILED_DAILY"
                failed = True

        promoted = False
        if not failed:
            if is_in_evaluation:
                # Evaluation Stage Logic
                step_target_pct = 0.10 if current_step == 1 else 0.05
                target = start_tier_balance * step_target_pct
                if tier_profit_accrued >= target:
                    if challenge_config.program_id == "2STEP" and current_step == 1:
                        status = "STEP_1_PASSED"
                        current_step = 2
                        promoted = True
                    else:
                        status = "PROMOTED_TO_FUNDED"
                        is_in_evaluation = False
                        current_step = 0
                        promoted = True
            else:
                # Funded Scaling Logic (Sliding Window)
                if trade.close_timestamp >= min_review_date:
                    target = start_tier_balance * scaling_config.profit_target_pct
                    if tier_profit_accrued >= target:
                        # Check profitable months requirement in the sliding window
                        window_start = trade.close_timestamp - relativedelta(months=scaling_config.review_period_months)
                        prof_months = sum(1 for (y, m), p in monthly_pnls.items() if datetime(y, m, 1, tzinfo=window_start.tzinfo) >= window_start and p > 0)
                        if prof_months >= 2:
                            status = "SCALED_UP"
                            promoted = True

        if failed or promoted:
            # Calculate final profit at end of this life attempt
            # For evaluations, we don't have monthly payouts, so current_balance works.
            # For funded, we reset monthly, so tier_profit_accrued is the source of truth.
            profit_at_end = tier_profit_accrued
            
            if not is_in_evaluation and profit_at_end > 0:
                # Calculate any remaining payout not yet captured by the monthly trigger
                # (e.g. if promoted mid-month)
                remaining_profit = current_balance - start_tier_balance
                if remaining_profit > 0:
                    payout = remaining_profit * challenge_config.payout_share
                    total_payouts += payout
                    life_withdrawals += payout
                    wallet_balance += payout

            lives.append(LifeResult(
                life_id=life_id_counter,
                start_tier_balance=start_tier_balance,
                end_balance=current_balance,
                status=status if not failed else status,
                start_date=current_life_start,
                end_date=trade.close_timestamp,
                trade_count=len(current_life_trades),
                pnl=profit_at_end,
                beginning_wallet_balance=beginning_wallet,
                new_wallet_balance=wallet_balance,
                life_withdrawals=life_withdrawals,
                buyback_cost=pending_buyback_cost,
                metrics=calculate_metrics(current_life_trades),
            ))
            life_id_counter += 1
            life_withdrawals = 0.0
            
            if failed:
                is_in_evaluation = False 
                current_step = 0
                next_tier_balance = scaling_config.increments[0]
                if cost_map:
                    affordable = sorted([t for t, c in cost_map.items() if c <= wallet_balance], reverse=True)
                    if affordable:
                        next_tier_balance = affordable[0]
                    pending_buyback_cost = cost_map.get(next_tier_balance, challenge_config.cost)
                    wallet_balance -= pending_buyback_cost
                    total_costs += pending_buyback_cost
                else:
                    pending_buyback_cost = challenge_config.cost
                    total_costs += pending_buyback_cost
                    wallet_balance -= pending_buyback_cost
                
                start_tier_balance = next_tier_balance
                try:
                    current_tier_idx = scaling_config.increments.index(start_tier_balance)
                except ValueError:
                    current_tier_idx = 0
            elif status == "STEP_1_PASSED":
                # Step 2 stays at same balance but target changes
                start_tier_balance = start_tier_balance 
                pending_buyback_cost = 0.0
            else:
                # Scaled up or Promoted to Funded
                current_tier_idx = min(current_tier_idx + (1 if status == "SCALED_UP" else 0), len(scaling_config.increments) - 1)
                start_tier_balance = scaling_config.increments[current_tier_idx]
                pending_buyback_cost = 0.0

            # Reset State for Next Life/Step
            current_balance = start_tier_balance
            current_life_trades = []
            current_life_start = trade.close_timestamp
            peak_balance = current_balance
            monthly_pnls = {}
            tier_profit_accrued = 0.0
            min_review_date = current_life_start + relativedelta(months=scaling_config.review_period_months)
            beginning_wallet = wallet_balance

        i += 1

    # Final active state
    lives.append(LifeResult(
        life_id=life_id_counter,
        start_tier_balance=start_tier_balance,
        end_balance=current_balance,
        status="Active",
        start_date=current_life_start,
        end_date=sorted_execs[-1].close_timestamp,
        trade_count=len(current_life_trades),
        pnl=tier_profit_accrued,
        beginning_wallet_balance=beginning_wallet,
        new_wallet_balance=wallet_balance,
        life_withdrawals=life_withdrawals,
        buyback_cost=pending_buyback_cost,
        metrics=calculate_metrics(current_life_trades),
    ))

    return ScalingReport(
        lives=lives,
        total_duration_days=(sorted_execs[-1].close_timestamp - sorted_execs[0].open_timestamp).days,
        active_life_index=len(lives) - 1,
        wallet_balance=wallet_balance,
        net_payouts=total_payouts,
        total_costs=total_costs,
    )

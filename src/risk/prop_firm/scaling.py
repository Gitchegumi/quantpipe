"""
Scaling logic for CTI Prop Firm progression.
"""

from datetime import datetime
from dateutil.relativedelta import relativedelta
from src.backtest.metrics import calculate_metrics
from src.models.core import TradeExecution
from .models import AttemptResult, ChallengeConfig, LevelResult, ScalingConfig, ScalingReport


def evaluate_scaling(
    executions: list[TradeExecution],
    challenge_config: ChallengeConfig,
    scaling_config: ScalingConfig,
    cost_map: dict[float, float] | None = None,
    instant_cost_map: dict[float, float] | None = None,
    buyback_mode: str | None = None,
) -> ScalingReport:
    """
    Simulate scaling progression with resets and periodic reviews.
    """
    if not executions:
        return ScalingReport(attempts=[], total_duration_days=0, active_attempt_index=-1)

    sorted_execs = sorted(executions, key=lambda x: x.close_timestamp)
    attempts: list[AttemptResult] = []
    current_attempt_levels: list[LevelResult] = []

    # Financial Tracking
    wallet_balance = -challenge_config.cost
    total_costs = challenge_config.cost
    total_payouts = 0.0

    # Initial State
    current_tier_type = "CHALLENGE" if challenge_config.program_id.startswith("CTI_2STEP") else "INSTANT"
    is_in_evaluation = (current_tier_type == "CHALLENGE")
    current_step = 1 if is_in_evaluation else 0 
    
    # Starting Equity vs Tier Size
    start_tier_equity = challenge_config.account_size
    
    # Find the nominal tier size
    nominal_current_size = start_tier_equity
    if current_tier_type == "INSTANT":
        if "_PRO_" not in challenge_config.program_id:
            nominal_current_size = start_tier_equity * 2.0
            
    nominal_start_size = nominal_current_size

    try:
        current_tier_idx = scaling_config.increments.index(nominal_current_size)
    except ValueError:
        current_tier_idx = 0

    current_balance = start_tier_equity
    current_level_trades: list[TradeExecution] = []
    current_level_start = sorted_execs[0].open_timestamp
    
    min_review_date = current_level_start + relativedelta(months=scaling_config.review_period_months)

    daily_start_balances = {}
    current_day = current_level_start.date()
    daily_start_balances[current_day] = current_balance

    peak_balance = current_balance
    monthly_pnls = {}
    level_profit_accrued = 0.0
    attempt_id_counter = 1
    level_id_counter = 1
    life_withdrawals = 0.0
    pending_buyback_cost = 0.0
    beginning_wallet = wallet_balance

    i = 0
    while i < len(sorted_execs):
        trade = sorted_execs[i]
        trade_date = trade.close_timestamp.date()
        trade_month = (trade.close_timestamp.year, trade.close_timestamp.month)

        if trade_date > current_day:
            if not is_in_evaluation and trade_date.month != current_day.month:
                profit_this_month = current_balance - start_tier_equity
                if profit_this_month > 0:
                    payout = profit_this_month * challenge_config.payout_share
                    total_payouts += payout
                    life_withdrawals += payout
                    wallet_balance += payout
                    current_balance = start_tier_equity
                    peak_balance = current_balance
            
            daily_start_balances[trade_date] = current_balance
            current_day = trade_date

        scale_factor = nominal_current_size / nominal_start_size
        
        base_pnl = trade.pnl_r * trade.risk_amount
        if trade.risk_amount == 0 and trade.pnl_r != 0:
            estimated_risk = nominal_current_size * (trade.risk_percent or 0.01)
            base_pnl = trade.pnl_r * estimated_risk
        else:
            base_pnl = trade.pnl_r * trade.risk_amount * scale_factor

        current_balance += base_pnl
        level_profit_accrued += base_pnl
        current_level_trades.append(trade)
        monthly_pnls[trade_month] = monthly_pnls.get(trade_month, 0.0) + base_pnl

        if current_balance > peak_balance:
            peak_balance = current_balance

        max_dd_amount = nominal_current_size * challenge_config.max_total_drawdown_pct
        failed = False
        floor = start_tier_equity - max_dd_amount if challenge_config.drawdown_type == "STATIC" else peak_balance - max_dd_amount
        
        if current_balance < floor:
            status = "FAILED_DRAWDOWN"
            failed = True

        if not failed and challenge_config.max_daily_loss_pct:
            day_start = daily_start_balances.get(trade_date, current_balance)
            limit = day_start - (nominal_current_size * challenge_config.max_daily_loss_pct)
            if current_balance < limit:
                status = "FAILED_DAILY"
                failed = True

        promoted = False
        if not failed:
            if is_in_evaluation:
                target_pct = 0.10 if current_step == 1 else 0.05
                target_amount = start_tier_equity * target_pct
                
                if level_profit_accrued >= target_amount:
                    if current_step == 1:
                        status = "STEP_1_PASSED"
                        current_step = 2
                        promoted = True
                    else:
                        status = "PROMOTED_TO_FUNDED"
                        is_in_evaluation = False
                        current_step = 0
                        promoted = True
            else:
                if trade.close_timestamp >= min_review_date:
                    target_amount = start_tier_equity * scaling_config.profit_target_pct
                    window_start = trade.close_timestamp - relativedelta(months=scaling_config.review_period_months)
                    window_pnl = 0.0
                    prof_months = 0
                    
                    for (y, m), p in monthly_pnls.items():
                        month_dt = datetime(y, m, 1, tzinfo=window_start.tzinfo)
                        if month_dt >= window_start:
                            window_pnl += p
                            if p > 0:
                                prof_months += 1
                    
                    if window_pnl >= target_amount and prof_months >= 2:
                        status = "SCALED_UP"
                        promoted = True

        if failed or promoted:
            profit_at_end = level_profit_accrued
            
            payout_at_end = 0.0
            if not is_in_evaluation and profit_at_end > 0:
                remaining_profit = current_balance - start_tier_equity
                if remaining_profit > 0:
                    payout_at_end = remaining_profit * challenge_config.payout_share
                    total_payouts += payout_at_end
                    life_withdrawals += payout_at_end
            
            wallet_balance_before_next = wallet_balance + payout_at_end

            current_attempt_levels.append(LevelResult(
                level_id=level_id_counter,
                start_tier_balance=nominal_current_size,
                end_balance=current_balance,
                status=status,
                start_date=current_level_start,
                end_date=trade.close_timestamp,
                trade_count=len(current_level_trades),
                pnl=profit_at_end,
                beginning_wallet_balance=beginning_wallet,
                new_wallet_balance=wallet_balance_before_next,
                life_withdrawals=life_withdrawals,
                buyback_cost=pending_buyback_cost,
                metrics=calculate_metrics(current_level_trades),
                failure_reason=current_tier_type
            ))
            
            wallet_balance = wallet_balance_before_next
            level_id_counter += 1
            life_withdrawals = 0.0
            
            if failed:
                attempts.append(AttemptResult(
                    attempt_id=attempt_id_counter,
                    levels=current_attempt_levels,
                    status="FAILED",
                    total_pnl=sum(l.pnl for l in current_attempt_levels)
                ))
                
                attempt_id_counter += 1
                level_id_counter = 1
                current_attempt_levels = []
                
                # Buyback Strategy: 30% Wallet Budget
                buyback_budget = max(0.0, wallet_balance * 0.30)
                active_buyback_mode = buyback_mode if buyback_mode else program_type
                
                # Default back to initial selection
                buyback_type = active_buyback_mode
                nominal_current_size = scaling_config.increments[0]
                
                # Priority: Instant > Challenge (if affordable within budget)
                if instant_cost_map:
                    affordable_instants = sorted([t for t, c in instant_cost_map.items() if c <= buyback_budget], reverse=True)
                    if affordable_instants:
                        nominal_current_size = affordable_instants[0]
                        pending_buyback_cost = instant_cost_map[nominal_current_size]
                        buyback_type = "INSTANT"
                    elif cost_map:
                        affordable_challenges = sorted([t for t, c in cost_map.items() if c <= buyback_budget], reverse=True)
                        if affordable_challenges:
                            nominal_current_size = affordable_challenges[0]
                            pending_buyback_cost = cost_map[nominal_current_size]
                            buyback_type = "CHALLENGE"
                        else:
                            # Totally broke? Smallest Challenge, uses up wallet
                            nominal_current_size = scaling_config.increments[0]
                            pending_buyback_cost = cost_map.get(nominal_current_size, challenge_config.cost)
                            buyback_type = "CHALLENGE"
                    else:
                        pending_buyback_cost = challenge_config.cost
                        buyback_type = "CHALLENGE"
                
                current_tier_type = buyback_type
                is_in_evaluation = (current_tier_type == "CHALLENGE")
                current_step = 1 if is_in_evaluation else 0
                
                wallet_balance -= pending_buyback_cost
                total_costs += pending_buyback_cost
                
                try:
                    current_tier_idx = scaling_config.increments.index(nominal_current_size)
                except ValueError:
                    current_tier_idx = 0
                    
                if current_tier_type == "INSTANT":
                    start_tier_equity = nominal_current_size / 2.0
                else:
                    start_tier_equity = nominal_current_size
                
                nominal_start_size = nominal_current_size
            elif status == "STEP_1_PASSED":
                pass
            else:
                current_tier_idx = min(current_tier_idx + 1, len(scaling_config.increments) - 1)
                nominal_current_size = scaling_config.increments[current_tier_idx]
                start_tier_equity = nominal_current_size
                pending_buyback_cost = 0.0

            current_balance = start_tier_equity
            current_level_trades = []
            current_level_start = trade.close_timestamp
            peak_balance = current_balance
            monthly_pnls = {}
            level_profit_accrued = 0.0
            min_review_date = current_level_start + relativedelta(months=scaling_config.review_period_months)
            beginning_wallet = wallet_balance

        i += 1

    current_attempt_levels.append(LevelResult(
        level_id=level_id_counter,
        start_tier_balance=scaling_config.increments[current_tier_idx],
        end_balance=current_balance,
        status="Active",
        start_date=current_level_start,
        end_date=sorted_execs[-1].close_timestamp,
        trade_count=len(current_level_trades),
        pnl=level_profit_accrued,
        beginning_wallet_balance=beginning_wallet,
        new_wallet_balance=wallet_balance,
        life_withdrawals=life_withdrawals,
        buyback_cost=pending_buyback_cost,
        metrics=calculate_metrics(current_level_trades),
        failure_reason=current_tier_type
    ))
    
    attempts.append(AttemptResult(
        attempt_id=attempt_id_counter,
        levels=current_attempt_levels,
        status="ACTIVE",
        total_pnl=sum(l.pnl for l in current_attempt_levels)
    ))

    return ScalingReport(
        attempts=attempts,
        total_duration_days=(sorted_execs[-1].close_timestamp - sorted_execs[0].open_timestamp).days,
        active_attempt_index=len(attempts) - 1,
        wallet_balance=wallet_balance,
        net_payouts=total_payouts,
        total_costs=total_costs,
    )

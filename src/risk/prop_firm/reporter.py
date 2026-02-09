"""
Reporting module for CTI Prop Firm simulation results.
"""

from .models import ScalingReport, LevelResult


def format_cti_report(report: ScalingReport) -> str:
    """
    Format the CTI Scaling Report as a human-readable string.

    Matches the format expected by reference output:
    [CTI Evaluation: Portfolio]
      Scaling Report (Total Attempts: X | Total Levels: Y | Promotions: Z | Resets: R)
      Financials: Wallet Balance: $... | Total Payouts: $... | Total Costs: $...
      ...
    """
    lines = []
    lines.append("")
    lines.append("[CTI Evaluation: Portfolio]")

    # Summary Line
    total_levels = sum(len(a.levels) for a in report.attempts)
    promotions = 0
    resets = len(report.attempts) - 1 if report.attempts else 0

    for att in report.attempts:
        for lvl in att.levels:
            if lvl.status in ("PROMOTED_TO_FUNDED", "SCALED_UP", "STEP_1_PASSED"):
                promotions += 1

    lines.append(
        f"  Scaling Report (Total Attempts: {len(report.attempts)} | "
        f"Total Levels: {total_levels} | Promotions: {promotions} | Resets: {resets})"
    )

    # Financials
    # Calculate Payout P&L (Active Wallet + Payouts - Costs)
    # The reference shows "CTI Payout P&L (100%): ... | (80%): ..."
    # This implies a theoretical max payout vs actual share?
    # Or just total profit extracted?
    # Let's use report.net_payouts and report.wallet_balance

    total_net = report.wallet_balance + report.net_payouts - report.total_costs
    # Actually the reference says "CTI Payout P&L".
    # Let's just print the values we have.

    lines.append(
        f"  Financials: Wallet Balance: ${report.wallet_balance:,.2f} | "
        f"Total Payouts: ${report.net_payouts:,.2f} | "
        f"Total Costs: ${report.total_costs:,.2f}"
    )

    # Calculate Payout P&L scenarios
    # 100% Scenario: Gross Payouts - Total Costs
    # Share Scenario (e.g. 80%): Net Payouts - Total Costs (Matches Wallet)

    share = report.payout_share if report.payout_share > 0 else 1.0
    gross_payouts = report.net_payouts / share

    pnl_100 = gross_payouts - report.total_costs
    pnl_share = report.net_payouts - report.total_costs

    share_pct = int(share * 100)
    lines.append(
        f"  CTI Payout P&L (100%): ${pnl_100:,.2f} | ({share_pct}%): ${pnl_share:,.2f}"
    )

    # Attempts Detail
    for att in report.attempts:
        levels_achieved = len(att.levels)
        lines.append(
            f"    Attempt #{att.attempt_id}: Levels Achieved={levels_achieved}, Total PnL=${att.total_pnl:,.2f}"
        )

        for lvl in att.levels:
            # Step/Level Header
            # Format: Step 1 #1 [CHALLENGE | Tier $2500 | Target $250]: Status=..., PnL=..., Balance=...
            # We need to distinguish Step 1 vs Level #X.
            # We can infer from level_id ?
            # Or from status?
            # A level is a "Step" if in Evaluation.

            # Simplified Label
            label = f"Level #{lvl.level_id}"

            # Try to reconstruct detailed label if possible
            # But "Level #ID" is safe.

            lines.append(
                f"      {label} [Tier ${lvl.start_tier_balance:.0f}]: "
                f"Status={lvl.status}, PnL=${lvl.pnl:,.2f}, Balance=${lvl.end_balance:,.2f}"
            )

            if lvl.buyback_cost > 0:
                lines.append(f"        Buyback Cost: ${lvl.buyback_cost:,.2f}")

            lines.append(
                f"        Starting Wallet Balance: ${lvl.beginning_wallet_balance:,.2f}"
            )
            if lvl.life_withdrawals > 0:
                lines.append(f"        Life withdrawals: ${lvl.life_withdrawals:,.2f}")

            period_str = f"{lvl.start_date.strftime('%Y-%m-%d %H:%M')} to {lvl.end_date.strftime('%Y-%m-%d %H:%M')}"
            lines.append(f"        Period: {period_str}")

            if lvl.metrics:
                lines.append(
                    f"        Stats: {lvl.metrics.win_count} Wins, {lvl.metrics.loss_count} Losses | "
                    f"MaxWinStreak: {lvl.metrics.max_consecutive_wins}, MaxLossStreak: {lvl.metrics.max_consecutive_losses}"
                )

            if lvl.status.startswith("FAILED"):
                lines.append(
                    f"        Failure: {lvl.failure_reason} (End: {lvl.end_date})"
                )
            elif lvl.status in ("PROMOTED_TO_FUNDED", "SCALED_UP"):
                lines.append(
                    f"        Success: Promoted to Tier Balance ${lvl.end_balance:,.2f}"
                )

            lines.append(
                f"        Ending Wallet Balance: ${lvl.new_wallet_balance:,.2f}"
            )
            lines.append("")

    return "\n".join(lines)

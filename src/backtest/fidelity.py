"""Fidelity validation utilities for performance optimization.

This module provides utilities to compare backtest results between baseline
and optimized implementations, ensuring performance improvements maintain
result accuracy within defined tolerances.

Tolerances (from FR-006):
- Price differences: ≤ 1e-6 absolute
- PnL percentage: ≤ 0.01% absolute
- Win rate: ≤ 0.1 percentage points
- Holding duration: ≤ 1 bar difference
- Exit indices: exact match
"""

from typing import Any, Dict, List
from dataclasses import dataclass


@dataclass
class FidelityReport:
    """Results of fidelity comparison between baseline and optimized runs.

    Attributes:
        passed: Overall pass/fail status.
        total_comparisons: Number of items compared.
        price_violations: Count of price tolerance violations.
        pnl_violations: Count of PnL tolerance violations.
        index_violations: Count of exact index mismatches.
        duration_violations: Count of duration tolerance violations.
        details: List of specific violation details.
    """

    passed: bool
    total_comparisons: int
    price_violations: int
    pnl_violations: int
    index_violations: int
    duration_violations: int
    details: List[str]


def compare_fidelity(
    baseline: List[Dict[str, Any]],
    optimized: List[Dict[str, Any]],
    price_tolerance: float = 1e-6,
    pnl_tolerance: float = 0.0001,  # 0.01%
    duration_tolerance: int = 1,
) -> FidelityReport:
    """Compare baseline and optimized backtest results for fidelity.

    Validates that performance optimizations preserve result accuracy within
    defined tolerances. Compares trade-by-trade results including prices,
    PnL, exit timing, and indices.

    Args:
        baseline: List of baseline execution results.
        optimized: List of optimized execution results.
        price_tolerance: Maximum absolute price difference allowed (default 1e-6).
        pnl_tolerance: Maximum PnL percentage difference allowed (default 0.01%).
        duration_tolerance: Maximum bar count difference allowed (default 1).

    Returns:
        FidelityReport with comparison results and violation details.

    Examples:
        >>> baseline = [{"exit_price": 1.1000, "pnl": 0.02, "exit_index": 100}]
        >>> optimized = [{"exit_price": 1.1000, "pnl": 0.02, "exit_index": 100}]
        >>> report = compare_fidelity(baseline, optimized)
        >>> report.passed
        True
    """
    details = []
    price_violations = 0
    pnl_violations = 0
    index_violations = 0
    duration_violations = 0

    # Check count mismatch
    if len(baseline) != len(optimized):
        details.append(
            f"Trade count mismatch: baseline={len(baseline)}, "
            f"optimized={len(optimized)}"
        )
        return FidelityReport(
            passed=False,
            total_comparisons=0,
            price_violations=0,
            pnl_violations=0,
            index_violations=0,
            duration_violations=0,
            details=details,
        )

    total = len(baseline)

    # Compare each trade
    for i, (base, opt) in enumerate(zip(baseline, optimized)):
        trade_id = f"trade_{i}"

        # Check exit price
        base_price = base.get("exit_price")
        opt_price = opt.get("exit_price")
        if base_price is not None and opt_price is not None:
            price_diff = abs(base_price - opt_price)
            if price_diff > price_tolerance:
                price_violations += 1
                details.append(
                    f"{trade_id}: price diff {price_diff:.2e} > {price_tolerance:.2e} "
                    f"(base={base_price:.6f}, opt={opt_price:.6f})"
                )

        # Check PnL
        base_pnl = base.get("pnl")
        opt_pnl = opt.get("pnl")
        if base_pnl is not None and opt_pnl is not None:
            pnl_diff = abs(base_pnl - opt_pnl)
            if pnl_diff > pnl_tolerance:
                pnl_violations += 1
                details.append(
                    f"{trade_id}: PnL diff {pnl_diff:.4f} > {pnl_tolerance:.4f} "
                    f"(base={base_pnl:.4f}, opt={opt_pnl:.4f})"
                )

        # Check exit index (exact match required)
        base_idx = base.get("exit_index")
        opt_idx = opt.get("exit_index")
        if base_idx is not None and opt_idx is not None:
            if base_idx != opt_idx:
                index_violations += 1
                details.append(
                    f"{trade_id}: exit index mismatch "
                    f"(base={base_idx}, opt={opt_idx})"
                )

        # Check holding duration
        base_dur = base.get("holding_duration")
        opt_dur = opt.get("holding_duration")
        if base_dur is not None and opt_dur is not None:
            dur_diff = abs(base_dur - opt_dur)
            if dur_diff > duration_tolerance:
                duration_violations += 1
                details.append(
                    f"{trade_id}: duration diff {dur_diff} > {duration_tolerance} bars "
                    f"(base={base_dur}, opt={opt_dur})"
                )

    total_violations = (
        price_violations + pnl_violations + index_violations + duration_violations
    )
    passed = total_violations == 0

    return FidelityReport(
        passed=passed,
        total_comparisons=total,
        price_violations=price_violations,
        pnl_violations=pnl_violations,
        index_violations=index_violations,
        duration_violations=duration_violations,
        details=details,
    )

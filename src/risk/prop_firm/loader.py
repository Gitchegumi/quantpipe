"""
Configuration loader for Prop Firm presets.
"""

import json
from pathlib import Path

from .models import ChallengeConfig, ScalingConfig

PRESETS_DIR = Path("src/config/presets/cti")


def load_cti_config(mode: str, account_size: int) -> ChallengeConfig:
    """
    Load CTI challenge configuration for a specific mode and account size.

    Args:
        mode: "1STEP", "2STEP", or "INSTANT"
        account_size: Starting account balance (e.g. 10000)

    Returns:
        ChallengeConfig object

    Raises:
        ValueError: If mode or account_size is invalid.
    """
    filename_map = {
        "1STEP": "cti_1_step_challenge.json",
        "2STEP": "cti_2_step_challenge.json",
        "INSTANT": "cti_instant_funding.json",
    }

    if mode not in filename_map:
        raise ValueError(
            f"Unknown CTI mode: {mode}. Must be one of {list(filename_map.keys())}"
        )

    file_path = PRESETS_DIR / filename_map[mode]

    if not file_path.exists():
        # Fallback for checking from project root if running as module
        file_path = Path.cwd() / file_path

    if not file_path.exists():
        raise FileNotFoundError(f"Config config file not found: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Find matching account size
    matching_config = None
    for size_config in data.get("starting_account_sizes", []):
        if size_config["account_size"] == account_size:
            matching_config = size_config
            break

    if not matching_config:
        available = [s["account_size"] for s in data.get("starting_account_sizes", [])]
        raise ValueError(
            f"Account size {account_size} not found for mode {mode}. Available: {available}"
        )

    eval_rules = matching_config.get("evaluation")
    if not eval_rules:
        # Fallback for multi-phase (use Phase 1 rules)
        eval_rules = matching_config.get("phase1")

    if not eval_rules:
        available = list(matching_config.keys())
        raise KeyError(
            f"Could not find 'evaluation' or 'phase1' rules in config. Keys: {available}"
        )

    # Map JSON fields to ChallengeConfig
    # Note: JSON percentages are often integers (e.g. 8 for 8%). Model expects float (0.08) or checking logic?
    # Spec says "max_daily_loss_pct: float". Usually logic uses 0.04. CTI json has "4".
    # We should convert 4 -> 0.04.

    def to_decimal(val):
        return float(val) / 100.0 if val is not None else None

    # Determine drawdown type
    if eval_rules.get("max_static_drawdown_percentage"):
        dd_type = "STATIC"
        max_dd = to_decimal(eval_rules.get("max_static_drawdown_percentage"))
    else:
        dd_type = "TRAILING"
        max_dd = to_decimal(eval_rules.get("max_trailing_drawdown_percentage"))

    return ChallengeConfig(
        program_id=f"CTI_{mode}_{account_size}",
        account_size=float(account_size),
        max_daily_loss_pct=to_decimal(eval_rules.get("max_daily_drawdown_percentage")),
        max_total_drawdown_pct=max_dd,
        profit_target_pct=to_decimal(eval_rules.get("profit_target_percentage")),
        min_trading_days=eval_rules.get("minimum_profitable_days", 0) or 0,
        max_time_days=eval_rules.get("time_limit_days"),
        drawdown_type=dd_type,
        drawdown_mode="CLOSED_BALANCE",
    )


def load_scaling_plan(mode: str) -> ScalingConfig:
    """
    Load scaling plan for a given mode.

    Args:
        mode: "1STEP", "2STEP", or "INSTANT"
    """
    filename = (
        "cti_instant_scaling_plan.json"
        if mode == "INSTANT"
        else "cti_challenge_scaling_plan.json"
    )
    file_path = PRESETS_DIR / filename

    if not file_path.exists():
        file_path = Path.cwd() / file_path

    if not file_path.exists():
        raise FileNotFoundError(f"Scaling plan file not found: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    criteria = data["criteria"]
    increments = [float(inc["account_size"]) for inc in data["increments"]]

    return ScalingConfig(
        review_period_months=criteria["review_period_months"],
        profit_target_pct=float(criteria["profit_target_percentage"]) / 100.0,
        increments=increments,
    )

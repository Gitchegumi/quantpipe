"""
Configuration loader for Prop Firm presets.
"""

import json
from pathlib import Path
from .models import ChallengeConfig, ScalingConfig

PRESETS_DIR = Path("src/config/presets/cti")

def load_cti_config(mode: str, account_size: int, tier: str = "STANDARD") -> ChallengeConfig:
    """
    Load CTI challenge configuration for a specific mode and account size.
    """
    filename_map = {
        "1STEP": "cti_1_step_challenge.json",
        "2STEP": "cti_2_step_challenge.json",
        "INSTANT": "cti_instant_funding.json",
    }

    if mode not in filename_map:
        raise ValueError(f"Unknown CTI mode: {mode}")

    file_path = PRESETS_DIR / filename_map[mode]
    if not file_path.exists():
        file_path = Path.cwd() / file_path

    with open(file_path, encoding="utf-8") as f:
        data = json.load(f)

    matching_config = None
    
    # Handle nested "programs" structure for Instant
    if "programs" in data:
        program_list = data["programs"].get(tier.upper(), [])
        for item in program_list:
            # For Instant, tier_name is the key (e.g. 10000)
            if item.get("tier_name") == account_size:
                matching_config = item
                break
    else:
        # Standard flat structure for Challenges
        for item in data.get("starting_account_sizes", []):
            if item.get("account_size") == account_size:
                matching_config = item
                break

    if not matching_config:
        raise ValueError(f"Account size {account_size} not found for {mode} {tier}")

    # Map to ChallengeConfig
    # For Instant: use starting_balance as account_size
    # For Challenge: use account_size
    base_size = matching_config.get("starting_balance", matching_config.get("account_size"))
    
    # Drawdown logic
    dd_cfg = matching_config.get("drawdown", {})
    max_dd = dd_cfg.get("total_pct", matching_config.get("max_drawdown_pct", 0.10))
    dd_type = dd_cfg.get("type", "TRAILING")
    daily_loss = dd_cfg.get("daily_pct", 0.05 if mode == "2STEP" else None)

    # Target logic
    target_pct = matching_config.get("profit_target_pct", 0.10)
    
    return ChallengeConfig(
        program_id=f"CTI_{mode}_{tier}_{account_size}",
        account_size=float(base_size),
        max_daily_loss_pct=daily_loss,
        max_total_drawdown_pct=max_dd,
        profit_target_pct=target_pct,
        min_trading_days=3,
        drawdown_type=dd_type,
        cost=float(matching_config.get("cost", 0.0)),
        payout_share=0.8
    )

def load_scaling_plan(mode: str) -> ScalingConfig:
    """
    Load scaling plan for a given mode.
    """
    filename = "cti_instant_scaling_plan.json" if mode == "INSTANT" else "cti_challenge_scaling_plan.json"
    file_path = PRESETS_DIR / filename
    if not file_path.exists(): file_path = Path.cwd() / file_path

    with open(file_path, encoding="utf-8") as f:
        data = json.load(f)

    criteria = data["criteria"]
    increments = [float(inc["account_size"]) for inc in data["increments"]]

    return ScalingConfig(
        review_period_months=criteria["review_period_months"],
        profit_target_pct=float(criteria["profit_target_percentage"]) / 100.0,
        increments=increments,
    )

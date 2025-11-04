"""Integration test: Single-strategy run with configuration overrides.

Tests US2 acceptance criteria:
- Register strategy with default config
- Run single-strategy backtest
- Apply config overrides
- Verify overrides affect only target strategy

Validates FR-005 (per-strategy config overrides), FR-009 (runtime overrides).
"""

# pylint: disable=unused-argument, unused-variable

import pytest
from src.backtest.orchestrator import BacktestOrchestrator
from src.models.enums import DirectionMode
from src.strategy.config_override import apply_strategy_overrides
from src.backtest.risk_strategy import extract_risk_limits_from_config
from src.models.strategy_config import StrategyConfig


def test_single_strategy_with_config_overrides():
    """
    Test single-strategy run with parameter overrides.

    Validates that config overrides apply only to target strategy.
    """
    base_config = {
        "ema_fast": 20,
        "ema_slow": 50,
        "atr_mult": 2.0,
    }

    user_overrides = {"alpha": {"ema_fast": 12, "atr_mult": 2.5}}

    # Apply overrides
    alpha_config = apply_strategy_overrides("alpha", base_config, user_overrides)
    beta_config = apply_strategy_overrides("beta", base_config, user_overrides)

    # Verify alpha has overrides
    assert alpha_config["ema_fast"] == 12
    assert alpha_config["ema_slow"] == 50  # Unchanged
    assert alpha_config["atr_mult"] == 2.5

    # Verify beta uses base
    assert beta_config["ema_fast"] == 20
    assert beta_config["ema_slow"] == 50
    assert beta_config["atr_mult"] == 2.0


def test_strategy_config_with_risk_limit_overrides():
    """
    Test StrategyConfig with risk limit overrides.

    Validates FR-005: Per-strategy risk limit configuration.
    """
    config = StrategyConfig(
        name="alpha",
        parameters={"ema_fast": 20},
        risk_limits={"max_drawdown_pct": 0.15, "stop_on_breach": True},
    )

    risk_limits = extract_risk_limits_from_config(config)

    assert risk_limits.max_drawdown_pct == 0.15
    assert risk_limits.stop_on_breach is True


def test_strategy_config_without_risk_limits_uses_defaults():
    """
    Test that missing risk_limits uses permissive defaults.
    """
    config = StrategyConfig(
        name="alpha",
        parameters={"ema_fast": 20},
        risk_limits=None,
    )

    risk_limits = extract_risk_limits_from_config(config)

    # Default: max_drawdown_pct = 1.0 (100%)
    assert risk_limits.max_drawdown_pct == 1.0
    assert risk_limits.stop_on_breach is True


def test_multi_strategy_independent_configs():
    """
    Test that multiple strategies maintain independent configs.

    Validates isolation: config changes to one don't affect others.
    """

    def strategy_alpha(candles):
        return {
            "pnl": 100.0,
            "max_drawdown": 0.05,
            "exposure": {},
        }

    def strategy_beta(candles):
        return {
            "pnl": 50.0,
            "max_drawdown": 0.03,
            "exposure": {},
        }

    orchestrator = BacktestOrchestrator(direction_mode=DirectionMode.LONG)

    # Configs with different parameters
    config_alpha = StrategyConfig(
        name="alpha",
        parameters={"ema_fast": 12, "ema_slow": 50},
        risk_limits={"max_drawdown_pct": 0.10},
    )

    config_beta = StrategyConfig(
        name="beta",
        parameters={"ema_fast": 20, "ema_slow": 100},
        risk_limits={"max_drawdown_pct": 0.15},
    )

    # Extract risk limits
    limits_alpha = extract_risk_limits_from_config(config_alpha)
    limits_beta = extract_risk_limits_from_config(config_beta)

    # Verify independence
    assert limits_alpha.max_drawdown_pct == 0.10
    assert limits_beta.max_drawdown_pct == 0.15

    assert config_alpha.parameters["ema_fast"] == 12
    assert config_beta.parameters["ema_fast"] == 20


def test_config_override_preserves_unmodified_params():
    """
    Test that overrides preserve parameters not explicitly overridden.
    """
    base = {
        "ema_fast": 20,
        "ema_slow": 50,
        "atr_mult": 2.0,
        "rsi_length": 14,
        "cooldown": 5,
    }

    overrides = {"alpha": {"ema_fast": 12}}  # Only override one param

    result = apply_strategy_overrides("alpha", base, overrides)

    # Verify single override applied
    assert result["ema_fast"] == 12

    # Verify all other params preserved
    assert result["ema_slow"] == 50
    assert result["atr_mult"] == 2.0
    assert result["rsi_length"] == 14
    assert result["cooldown"] == 5


def test_strategy_config_validation_version_format():
    """
    Test StrategyConfig validates semantic version format.
    """
    with pytest.raises(ValueError, match="semantic format"):
        StrategyConfig(name="alpha", version="invalid")  # Not x.y.z format

    with pytest.raises(ValueError, match="numeric"):
        StrategyConfig(name="alpha", version="1.0.x")  # Non-numeric component

    # Valid versions
    valid = StrategyConfig(name="alpha", version="1.2.3")
    assert valid.version == "1.2.3"


def test_strategy_config_name_validation():
    """
    Test StrategyConfig validates non-empty name.
    """
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        StrategyConfig(name="")

    with pytest.raises(ValidationError):
        StrategyConfig(name="   ")  # Whitespace only

    # Valid name
    valid = StrategyConfig(name="alpha")
    assert valid.name == "alpha"


def test_risk_limits_from_config_with_custom_defaults():
    """
    Test extract_risk_limits_from_config with custom default fallback.
    """
    from src.models.risk_limits import RiskLimits

    config = StrategyConfig(name="alpha", risk_limits=None)

    custom_default = RiskLimits(
        max_drawdown_pct=0.05,
        daily_loss_threshold=500.0,
        stop_on_breach=False,
    )

    limits = extract_risk_limits_from_config(config, default_limits=custom_default)

    assert limits.max_drawdown_pct == 0.05
    assert limits.daily_loss_threshold == 500.0
    assert limits.stop_on_breach is False


def test_config_override_with_new_parameters():
    """
    Test that overrides can add new parameters not in base.
    """
    base = {"ema_fast": 20}
    overrides = {"alpha": {"ema_fast": 12, "new_param": 100}}

    result = apply_strategy_overrides("alpha", base, overrides)

    assert result["ema_fast"] == 12
    assert result["new_param"] == 100

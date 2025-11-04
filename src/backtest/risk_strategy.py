"""Per-strategy risk breach handling for multi-strategy execution.

This module evaluates individual strategy risk limits and determines
when a strategy should be halted due to local breaches (FR-003, FR-015).

Per FR-021, single strategy breaches do NOT trigger global abort—they only
halt that specific strategy while others continue.

Integration with StrategyConfig (T040):
- Supports extracting RiskLimits from StrategyConfig.risk_limits dict
- Provides backward compatibility with direct RiskLimits instances
"""

import logging
from src.models.risk_limits import RiskLimits
from src.models.strategy_config import StrategyConfig
from src.backtest.state_isolation import StrategyState

logger = logging.getLogger(__name__)


def check_strategy_risk_breach(
    state: StrategyState,
    risk_limits: RiskLimits,
) -> tuple[bool, str]:
    """
    Check if strategy has breached any configured risk limits.

    Evaluates:
    - Maximum drawdown percentage
    - Daily loss threshold (if configured)
    - Maximum open trades (future enhancement)

    Args:
        state: Current strategy state with metrics.
        risk_limits: Configured risk thresholds for this strategy.

    Returns:
        Tuple of (is_breach, reason).
        - is_breach: True if any limit breached
        - reason: Human-readable breach description

    Examples:
        >>> from src.models.risk_limits import RiskLimits
        >>> from src.backtest.state_isolation import StrategyState
        >>> state = StrategyState("alpha")
        >>> state.current_drawdown = 0.12
        >>> limits = RiskLimits(max_drawdown_pct=0.10)
        >>> check_strategy_risk_breach(state, limits)
        (True, 'drawdown_breach')
    """
    # Check drawdown limit
    if state.current_drawdown > risk_limits.max_drawdown_pct:
        reason = "drawdown_breach"
        logger.warning(
            "Strategy risk breach: name=%s drawdown=%.4f > limit=%.4f",
            state.strategy_name,
            state.current_drawdown,
            risk_limits.max_drawdown_pct,
        )
        return (True, reason)

    # Check daily loss threshold (if configured)
    if risk_limits.daily_loss_threshold is not None:
        # Note: This requires daily PnL tracking, which is not yet implemented
        # For now, we check running PnL as proxy
        if state.running_pnl < -risk_limits.daily_loss_threshold:
            reason = "daily_loss_breach"
            logger.warning(
                "Strategy risk breach: name=%s loss=%.4f > threshold=%.4f",
                state.strategy_name,
                abs(state.running_pnl),
                risk_limits.daily_loss_threshold,
            )
            return (True, reason)

    # No breach detected
    return (False, "")


def should_halt_on_breach(
    state: StrategyState,
    risk_limits: RiskLimits,
    breach_detected: bool,
) -> bool:
    """
    Determine if strategy should be halted given breach status.

    Respects RiskLimits.stop_on_breach configuration.

    Args:
        state: Strategy state (for logging context).
        risk_limits: Risk configuration including stop_on_breach flag.
        breach_detected: Whether a risk breach was detected.

    Returns:
        True if strategy should halt.

    Examples:
        >>> from src.models.risk_limits import RiskLimits
        >>> from src.backtest.state_isolation import StrategyState
        >>> state = StrategyState("alpha")
        >>> limits = RiskLimits(max_drawdown_pct=0.10, stop_on_breach=True)
        >>> should_halt_on_breach(state, limits, breach_detected=True)
        True
        >>> limits_no_stop = RiskLimits(max_drawdown_pct=0.10, stop_on_breach=False)
        >>> should_halt_on_breach(state, limits_no_stop, breach_detected=True)
        False
    """
    if not breach_detected:
        return False

    if risk_limits.stop_on_breach:
        logger.info(
            "Halting strategy on breach: name=%s", state.strategy_name
        )
        return True

    logger.info(
        "Risk breach detected but stop_on_breach=False: name=%s (continuing)",
        state.strategy_name,
    )
    return False


def extract_risk_limits_from_config(
    config: StrategyConfig,
    default_limits: RiskLimits | None = None,
) -> RiskLimits:
    """
    Extract RiskLimits from StrategyConfig.risk_limits dict.

    Args:
        config: StrategyConfig instance with optional risk_limits dict.
        default_limits: Fallback RiskLimits if config.risk_limits is None.

    Returns:
        RiskLimits instance constructed from config or default.

    Examples:
        >>> from src.models.strategy_config import StrategyConfig
        >>> from src.models.risk_limits import RiskLimits
        >>> config = StrategyConfig(
        ...     name="alpha",
        ...     risk_limits={"max_drawdown_pct": 0.12, "stop_on_breach": True}
        ... )
        >>> limits = extract_risk_limits_from_config(config)
        >>> limits.max_drawdown_pct
        0.12
    """
    if config.risk_limits is None:
        if default_limits is None:
            # Use permissive defaults
            return RiskLimits(max_drawdown_pct=1.0, stop_on_breach=True)
        return default_limits

    # Construct RiskLimits from dict
    return RiskLimits(**config.risk_limits)


__all__ = [
    "check_strategy_risk_breach",
    "should_halt_on_breach",
    "extract_risk_limits_from_config",
]

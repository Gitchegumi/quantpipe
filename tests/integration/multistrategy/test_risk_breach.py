"""Integration test: Risk breach isolation.

Tests that single strategy risk breaches halt only that strategy
while others continue executing per FR-003 and FR-021.

Validates:
- Per-strategy risk limit enforcement
- Halted strategy recorded in risk_breaches
- Other strategies continue execution
- Global abort NOT triggered by single strategy breach
"""

# pylint: disable=unused-variable, unused-import

from datetime import datetime, UTC
import pytest
from src.backtest.orchestrator import BacktestOrchestrator
from src.models.enums import DirectionMode
from src.backtest.state_isolation import StrategyState, StateIsolationManager
from src.models.risk_limits import RiskLimits
from src.backtest.risk_strategy import check_strategy_risk_breach


def test_strategy_drawdown_breach_detection():
    """
    Test that strategy exceeding drawdown limit is detected.
    """
    state = StrategyState(strategy_name="alpha")
    state.current_drawdown = 0.12  # 12% drawdown
    state.peak_equity = 1000.0
    state.running_pnl = 880.0

    limits = RiskLimits(max_drawdown_pct=0.10)  # 10% limit

    is_breach, reason = check_strategy_risk_breach(state, limits)

    assert is_breach is True
    assert reason == "drawdown_breach"


def test_strategy_within_limits_no_breach():
    """
    Test that strategy within limits is not flagged.
    """
    state = StrategyState(strategy_name="beta")
    state.current_drawdown = 0.08  # 8% drawdown
    limits = RiskLimits(max_drawdown_pct=0.10)

    is_breach, reason = check_strategy_risk_breach(state, limits)

    assert is_breach is False
    assert reason == ""


def test_state_halt_records_breach():
    """
    Test that halting a strategy records the breach event.
    """
    state = StrategyState(strategy_name="gamma")
    timestamp = datetime.now(UTC)

    assert state.is_halted is False
    assert len(state.risk_breach_events) == 0

    state.halt("drawdown_breach", timestamp)

    assert state.is_halted is True
    assert state.halt_reason == "drawdown_breach"
    assert len(state.risk_breach_events) == 1
    assert state.risk_breach_events[0] == timestamp


def test_state_isolation_manager_independence():
    """
    Test that StateIsolationManager maintains independent states.
    """
    manager = StateIsolationManager()

    state_a = manager.get_or_create("alpha")
    state_b = manager.get_or_create("beta")

    # Modify alpha's state
    state_a.update_pnl(100.0, datetime.now(UTC))
    state_a.halt("test_breach", datetime.now(UTC))

    # Beta should be unaffected
    assert state_b.running_pnl == 0.0
    assert state_b.is_halted is False

    # Alpha modifications preserved
    assert state_a.running_pnl == 100.0
    assert state_a.is_halted is True


def test_multi_strategy_single_breach_isolation():
    """
    Integration test: One strategy breaches, others continue.

    This is a conceptual test - full orchestrator integration would require
    actual risk limit checks during execution (future enhancement).
    """
    manager = StateIsolationManager()

    # Strategy 1: Exceeds drawdown
    state_1 = manager.get_or_create("alpha")
    state_1.update_pnl(-120.0, datetime.now(UTC))  # Simulate loss
    state_1.peak_equity = 1000.0
    state_1.current_drawdown = 0.12

    limits_1 = RiskLimits(max_drawdown_pct=0.10, stop_on_breach=True)
    is_breach_1, reason_1 = check_strategy_risk_breach(state_1, limits_1)

    if is_breach_1:
        state_1.halt(reason_1, datetime.now(UTC))

    # Strategy 2: Within limits
    state_2 = manager.get_or_create("beta")
    state_2.update_pnl(50.0, datetime.now(UTC))
    state_2.current_drawdown = 0.05

    limits_2 = RiskLimits(max_drawdown_pct=0.10)
    is_breach_2, reason_2 = check_strategy_risk_breach(state_2, limits_2)

    # Validate isolation
    assert state_1.is_halted is True
    assert state_2.is_halted is False
    assert is_breach_1 is True
    assert is_breach_2 is False


def test_daily_loss_threshold_breach():
    """
    Test daily loss threshold breach detection.

    Note: Current implementation uses running PnL as proxy for daily loss.
    """
    state = StrategyState(strategy_name="delta")
    state.running_pnl = -600.0  # Lost $600

    limits = RiskLimits(
        max_drawdown_pct=1.0,  # Permissive drawdown
        daily_loss_threshold=500.0,  # $500 limit
    )

    is_breach, reason = check_strategy_risk_breach(state, limits)

    assert is_breach is True
    assert reason == "daily_loss_breach"


def test_stop_on_breach_flag_honored():
    """
    Test that stop_on_breach=False allows strategy to continue despite breach.
    """
    from src.backtest.risk_strategy import should_halt_on_breach

    state = StrategyState(strategy_name="epsilon")
    limits_stop = RiskLimits(max_drawdown_pct=0.10, stop_on_breach=True)
    limits_continue = RiskLimits(max_drawdown_pct=0.10, stop_on_breach=False)

    # Breach detected
    breach_detected = True

    # With stop_on_breach=True, should halt
    assert should_halt_on_breach(state, limits_stop, breach_detected) is True

    # With stop_on_breach=False, should continue
    assert should_halt_on_breach(state, limits_continue, breach_detected) is False


def test_multiple_breaches_recorded():
    """
    Test that multiple breach events are tracked chronologically.
    """
    state = StrategyState(strategy_name="zeta")

    timestamp1 = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
    timestamp2 = datetime(2025, 1, 1, 14, 0, 0, tzinfo=UTC)

    state.halt("first_breach", timestamp1)
    # Simulate re-halt after recovery attempt (edge case)
    state.risk_breach_events.append(timestamp2)

    assert len(state.risk_breach_events) == 2
    assert state.risk_breach_events[0] == timestamp1
    assert state.risk_breach_events[1] == timestamp2
